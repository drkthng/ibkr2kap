from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from ibkr_tax.models.database import Trade, Gain, CashTransaction
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

        for ctx in cash_txs:
            # Type names are from Flex Query: 'Dividends', 'Withholding Tax', 'Payment In Lieu of Dividends', 'Broker Interest Paid/Received'
            if ctx.type in ["Dividends", "Payment In Lieu of Dividends", "Broker Interest Paid/Received"]:
                # Note: IBKR reports paid interest as negative. For Line 7 we want the net interest/dividends.
                dividends_interest += ctx.amount * ctx.fx_rate_to_base
            elif ctx.type == "Withholding Tax":
                # Withholding tax is negative (money out). Line 15 is positive (tax credit).
                withholding_tax += abs(ctx.amount * ctx.fx_rate_to_base)

        # Line 7 = Dividends/Interest + Sonstige Gains
        kap_7 = dividends_interest + sonstige_gains

        # 3. Detect Missing Cost Basis (Unresolved Short Positions)
        from ibkr_tax.models.database import FIFOLot
        stmt_missing = (
            select(FIFOLot)
            .join(Trade, FIFOLot.trade_id == Trade.id)
            .where(Trade.account_id == account_db_id)
            .where(FIFOLot.remaining_quantity < 0)
            .where(Trade.settle_date.like(f"{tax_year}%"))
        )
        missing_lots = self.session.execute(stmt_missing).scalars().all()
        warnings = []
        for lot in missing_lots:
            # Using normalize() to remove trailing zeros for cleaner display
            qty_clean = abs(lot.remaining_quantity).normalize()
            warnings.append(
                f"Missing cost basis for {qty_clean:f} shares of {lot.symbol} (first sold on {lot.settle_date})"
            )

        return TaxReport(
            account_id=account_identifier,
            tax_year=tax_year,
            kap_line_7_kapitalertraege=kap_7,
            kap_line_8_gewinne_aktien=kap_8,
            kap_line_9_verluste_aktien=kap_9,
            kap_line_10_termingeschaefte=kap_10,
            kap_line_15_quellensteuer=withholding_tax,
            total_realized_pnl=total_pnl,
            missing_cost_basis_warnings=warnings
        )
