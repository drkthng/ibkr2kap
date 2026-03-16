from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, asc, or_
from ibkr_tax.models.database import Trade, CashTransaction, FXFIFOLot, FXGain

class FXFIFOEngine:
    def __init__(self, session: Session):
        self.session = session

    def process_all_fx(self, account_id: int):
        """Processes all FX acquisitions and disposals for an account."""
        # 1. Clear existing FX data for this account to ensure idempotency
        self.session.query(FXGain).filter_by(account_id=account_id).delete()
        self.session.query(FXFIFOLot).filter_by(account_id=account_id).delete()
        self.session.commit()

        # 2. Extract chronological stream of FX events
        events = self._get_fx_events(account_id)
        
        # 3. Process events per currency
        currencies = set(e['currency'] for e in events if e['currency'] != 'EUR')
        for currency in currencies:
            currency_events = [e for e in events if e['currency'] == currency]
            self._process_currency_stream(account_id, currency, currency_events)

    def _get_fx_events(self, account_id: int):
        """Gathers all trades and cash transactions that affect FX pools."""
        # Trades affecting FX:
        # - Buying a USD stock: Disposal of USD (amount = proceeds + commission + taxes?)
        # - Selling a USD stock: Acquisition of USD (amount = proceeds - commission - taxes?)
        # Note: Proceeds for BUY is negative, Proceeds for SELL is positive in our DB.
        # But we need to be careful about the sign.
        # Usually: Net USD = Trade.proceeds (which is already signed) - abs(commission) - abs(taxes)?
        # No, if BUY: proceeds is -100, commission is 1. Net USD = -101. (Disposal of 101 USD)
        # If SELL: proceeds is 110, commission is 1. Net USD = 109. (Acquisition of 109 USD)
        
        trades = self.session.execute(
            select(Trade).where(Trade.account_id == account_id).where(Trade.currency != 'EUR')
        ).scalars().all()

        cash_txs = self.session.execute(
            select(CashTransaction).where(CashTransaction.account_id == account_id).where(CashTransaction.currency != 'EUR')
        ).scalars().all()

        events = []
        for t in trades:
            # Net USD change
            net_usd = t.proceeds - abs(t.ib_commission) - abs(t.taxes)
            events.append({
                'date': t.settle_date,
                'amount': net_usd,
                'currency': t.currency,
                'fx_rate': t.fx_rate_to_base,
                'ref_id': t.id,
                'ref_type': 'trade'
            })

        for c in cash_txs:
            events.append({
                'date': c.settle_date,
                'amount': c.amount,
                'currency': c.currency,
                'fx_rate': c.fx_rate_to_base,
                'ref_id': c.id,
                'ref_type': 'cash_tx'
            })

        # Sort by date, then ref_id
        events.sort(key=lambda x: (x['date'], x['ref_id']))
        return events

    def _process_currency_stream(self, account_id: int, currency: str, events: list):
        """Bidirectional FIFO matching for a single currency stream."""
        for event in events:
            amount = event['amount']
            if amount == 0:
                continue

            # Try to match against opposite side first
            remaining_to_match = self._match_fx_against_inventory(account_id, currency, event)
            
            if remaining_to_match != 0:
                # Add remainder to inventory (positive or negative)
                self._add_fx_lot(account_id, currency, event, remaining_to_match)

    def _add_fx_lot(self, account_id: int, currency: str, event: dict, quantity: Decimal):
        lot = FXFIFOLot(
            account_id=account_id,
            currency=currency,
            acquisition_date=event['date'],
            original_amount=quantity,  # Signed
            remaining_amount=quantity, # Signed
            cost_basis_total_eur=abs(quantity) * event['fx_rate'],
            cost_basis_per_unit_eur=event['fx_rate'],
            trade_id=event['ref_id'] if event['ref_type'] == 'trade' else None,
            cash_transaction_id=event['ref_id'] if event['ref_type'] == 'cash_tx' else None
        )
        self.session.add(lot)
        self.session.flush()

    def _match_fx_against_inventory(self, account_id: int, currency: str, event: dict) -> Decimal:
        amount_to_match = event['amount']
        date = event['date']
        rate = event['fx_rate']

        # If amount > 0 (BUY Ccy), match against existing SHORT lots (remaining < 0)
        # If amount < 0 (SELL Ccy), match against existing LONG lots (remaining > 0)
        if amount_to_match > 0:
            lot_filter = FXFIFOLot.remaining_amount < 0
            target_sign = -1
        else:
            lot_filter = FXFIFOLot.remaining_amount > 0
            target_sign = 1

        stmt = (
            select(FXFIFOLot)
            .where(FXFIFOLot.account_id == account_id)
            .where(FXFIFOLot.currency == currency)
            .where(lot_filter)
            .order_by(asc(FXFIFOLot.acquisition_date), asc(FXFIFOLot.id))
        )
        open_lots = self.session.execute(stmt).scalars().all()

        current_to_match = abs(amount_to_match)
        for lot in open_lots:
            if current_to_match <= 0:
                break

            matched_qty = min(abs(lot.remaining_amount), current_to_match)
            
            # Cost basis of matched amount from the opening lot
            cost_basis_matched = matched_qty * lot.cost_basis_per_unit_eur
            
            # Proceeds/Cost from the matching event
            proceeds_matched = matched_qty * rate
            
            # Holding period
            d1 = datetime.strptime(lot.acquisition_date, "%Y-%m-%d")
            d2 = datetime.strptime(date, "%Y-%m-%d")
            days_held = (d2 - d1).days
            is_taxable = days_held <= 365

            # PnL logic similar to stock FIFO
            if target_sign == 1: # Closing LONG (SELL Currency)
                pnl = proceeds_matched - cost_basis_matched
            else: # Closing SHORT (BUY Currency)
                pnl = cost_basis_matched - proceeds_matched
            
            gain = FXGain(
                account_id=account_id,
                fx_lot_id=lot.id,
                disposal_date=date,
                amount_matched=matched_qty,
                disposal_proceeds_eur=proceeds_matched if target_sign == 1 else cost_basis_matched,
                cost_basis_matched_eur=cost_basis_matched if target_sign == 1 else proceeds_matched,
                realized_pnl_eur=pnl,
                days_held=days_held,
                is_taxable_section_23=is_taxable
            )
            self.session.add(gain)
            
            lot.remaining_amount += (matched_qty if target_sign == -1 else -matched_qty)
            current_to_match -= matched_qty

        self.session.flush()
        return current_to_match * (1 if amount_to_match > 0 else -1)
