from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from ibkr_tax.models.database import Trade, Gain, CashTransaction, FXGain
from ibkr_tax.schemas.report import TaxReport

class TaxAggregatorService:
    def __init__(self, session: Session):
        self.session = session

    def generate_report(self, account_identifier: str, tax_year: int) -> TaxReport:
        """
        Aggregates gains and cash transactions for a given account and tax year.
        Note: account_identifier here corresponds to the `account_id` string in the Account model,
        not the primary key ID.
        """
        # First, find our internal database account ID
        from ibkr_tax.models.database import Account
        stmt_acc = select(Account.id).where(Account.account_id == account_identifier)
        account_db_id = self.session.execute(stmt_acc).scalar()

        if account_db_id is None:
            return TaxReport(account_id=account_identifier, tax_year=tax_year)

        # 1. Aggregate Gains
        # Line 8: Gewinne aus Aktien (positive PnL where tax_pool == 'Aktien')
        # Line 9: Verluste aus Aktien (negative PnL where tax_pool == 'Aktien')
        # Line 10: Termingeschäfte (netted PnL where tax_pool == 'Termingeschäfte')
        # Total PnL: Sum of all realized_pnl
        # Line 7 (portion): 'Sonstige' gains
        
        stmt_gains = (
            select(Gain)
            .join(Trade, Gain.sell_trade_id == Trade.id)
            .where(Trade.account_id == account_db_id)
            .where(Gain.tax_year == tax_year)
        )
        gains = self.session.execute(stmt_gains).scalars().all()

        kap_8 = Decimal("0.00")
        kap_9 = Decimal("0.00")
        kap_10 = Decimal("0.00")
        sonstige_gains = Decimal("0.00")
        total_pnl = Decimal("0.00")

        for g in gains:
            total_pnl += g.realized_pnl
            if g.tax_pool == "Aktien":
                if g.realized_pnl > 0:
                    kap_8 += g.realized_pnl
                else:
                    kap_9 += abs(g.realized_pnl)
            elif g.tax_pool == "Termingeschäfte":
                kap_10 += g.realized_pnl
            else:
                # Sonstige (ETFs, Bonds, etc.)
                sonstige_gains += g.realized_pnl

        # 2. Aggregate Cash Transactions
        # Line 7 (portion): Dividends, Interest (all positive amounts)
        # Line 15: Withholding Tax (usually negative amounts in IBKR, but line 15 expects absolute value if it's a paid tax?)
        # Actually Line 15 in Anlage KAP is "Anrechenbare ausländische Steuern".
        
        stmt_cash = (
            select(CashTransaction)
            .where(CashTransaction.account_id == account_db_id)
            .where(CashTransaction.settle_date.like(f"{tax_year}%"))
        )
        cash_txs = self.session.execute(stmt_cash).scalars().all()

        dividends_interest = Decimal("0.00")
        withholding_tax = Decimal("0.00")
        margin_interest_paid = Decimal("0.00")

        for ctx in cash_txs:
            # Type names vary by source:
            #   CSV:  'Dividends', 'Withholding Tax', 'Broker Interest Paid', 'Broker Interest Received', etc.
            #   XML (ibflex): 'Dividends', 'Withholding Tax', 'Broker Interest Paid/Received', etc.
            #
            # § 20 Abs. 9 EStG: Margin interest PAID is non-deductible Werbungskosten.
            # Broker interest RECEIVED is taxable Zinserträge → KAP Line 7.
            if ctx.type == "Broker Interest Paid":
                # CSV path: explicit paid type → always margin cost
                margin_interest_paid += abs(ctx.amount * ctx.fx_rate_to_base)
            elif ctx.type == "Broker Interest Paid/Received":
                # XML/ibflex path: combined type, use amount sign to distinguish
                if ctx.amount < 0:
                    margin_interest_paid += abs(ctx.amount * ctx.fx_rate_to_base)
                else:
                    dividends_interest += ctx.amount * ctx.fx_rate_to_base
            elif ctx.type in ["Dividends", "Payment In Lieu of Dividends", "Broker Interest Received"]:
                dividends_interest += ctx.amount * ctx.fx_rate_to_base
            elif ctx.type == "Withholding Tax":
                # Withholding tax is negative (money out). Line 15 is positive (tax credit).
                withholding_tax += abs(ctx.amount * ctx.fx_rate_to_base)

        # Line 7 = Dividends/Interest + Sonstige Gains
        kap_7 = dividends_interest + sonstige_gains

        # 2b. Aggregate FX Gains (Anlage SO - § 23 EStG)
        stmt_fx_gains = (
            select(FXGain)
            .where(FXGain.account_id == account_db_id)
            .where(FXGain.disposal_date.like(f"{tax_year}%"))
        )
        fx_gains = self.session.execute(stmt_fx_gains).scalars().all()

        so_fx_total = Decimal("0.00")
        so_fx_taxable = Decimal("0.00")
        so_fx_tax_free = Decimal("0.00")

        for fxg in fx_gains:
            so_fx_total += fxg.realized_pnl_eur
            if fxg.is_taxable_section_23:
                so_fx_taxable += fxg.realized_pnl_eur
            else:
                so_fx_tax_free += fxg.realized_pnl_eur

        # Freigrenze applies if total taxable gains < 1000 EUR
        so_freigrenze_applies = so_fx_taxable > 0 and so_fx_taxable < 1000

        # 3. Detect Missing Cost Basis (Unresolved Short Positions)
        from ibkr_tax.models.database import FIFOLot, FXFIFOLot
        from sqlalchemy.orm import selectinload
        
        # 3a. Symbol-basis missing cost basis
        # Redundant safety: Filter out anything starting with EUR. or marked as CASH
        from ibkr_tax.schemas.report import MissingCostBasisWarning
        stmt_missing = (
            select(FIFOLot)
            .options(selectinload(FIFOLot.trade))
            .join(Trade, FIFOLot.trade_id == Trade.id)
            .where(Trade.account_id == account_db_id)
            .where(FIFOLot.remaining_quantity < 0)
            .where(Trade.settle_date.like(f"{tax_year}%"))
            .where(Trade.asset_category != "CASH")
            .where(FIFOLot.symbol.not_like("EUR.%"))
        )
        missing_lots = self.session.execute(stmt_missing).scalars().all()
        warnings = []
        for lot in missing_lots:
            # Using normalize() to remove trailing zeros
            qty_clean = abs(lot.remaining_quantity).normalize()
            msg = (
                f"❌ **Sold {qty_clean:f} {lot.symbol}** on {lot.settle_date} (ID: {lot.trade.ib_trade_id}), "
                f"but no corresponding Buy found. Using 0€ cost basis."
            )
            warnings.append(
                MissingCostBasisWarning(
                    symbol=lot.symbol,
                    asset_category=lot.asset_category,
                    quantity=qty_clean,
                    date=lot.settle_date,
                    trade_id=lot.trade.ib_trade_id,
                    message=msg
                )

            )

        # 3b. FX-basis missing cost basis warnings are REMOVED per redesign.
        # We only track explicit FX conversions now.

        return TaxReport(
            account_id=account_identifier,
            tax_year=tax_year,
            kap_line_7_kapitalertraege=kap_7,
            kap_line_8_gewinne_aktien=kap_8,
            kap_line_9_verluste_aktien=kap_9,
            kap_line_10_termingeschaefte=kap_10,
            kap_line_15_quellensteuer=withholding_tax,
            so_fx_gains_total=so_fx_total,
            so_fx_gains_taxable_1y=so_fx_taxable,
            so_fx_gains_tax_free=so_fx_tax_free,
            so_fx_freigrenze_applies=so_freigrenze_applies,
            margin_interest_paid=margin_interest_paid,
            total_realized_pnl=total_pnl + so_fx_total,
            missing_cost_basis_warnings=warnings
        )
