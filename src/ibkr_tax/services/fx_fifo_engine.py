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
        """Gathers only explicit FX conversion trades (asset_category == 'CASH')."""
        # We only care about CASH trades. 
        # Symbol is usually 'BASE.QUOTE' (e.g. 'EUR.USD')
        # Trade.currency is usually the quote currency.
        # proceeds is in Trade.currency.
        # quantity is in base currency.
        
        trades = self.session.execute(
            select(Trade)
            .where(Trade.account_id == account_id)
            .where(Trade.asset_category == 'CASH')
        ).scalars().all()

        events = []
        for t in trades:
            # Parse symbol EUR.USD -> EUR (base), USD (quote)
            try:
                base, quote = t.symbol.split('.')
            except ValueError:
                # Handle non-standard symbols if any
                base, quote = t.symbol, ""

            # 1. Handle Quote Currency side (usually the currency of proceeds)
            if quote and quote != 'EUR':
                # Proceeds is the amount of quote currency acquired (+) or disposed (-)
                events.append({
                    'date': t.settle_date,
                    'amount': t.proceeds, 
                    'currency': quote,
                    'fx_rate': t.fx_rate_to_base, # This is quote -> EUR rate in our DB
                    'ref_id': t.id,
                })

            # 2. Handle Base Currency side (usually the quantity)
            if base and base != 'EUR':
                # If we BUY EUR.USD, quantity is +EUR, proceeds is -USD.
                # If we SELL EUR.USD, quantity is -EUR, proceeds is +USD.
                # So for the base currency: amount is -quantity? No.
                # Quantity in our DB for trades is signed. BUY = +, SELL = -.
                # For EUR.USD: BUY 1000 means +1000 EUR, -USD. 
                # So base currency amount is exactly Trade.quantity.
                
                # We need the base -> EUR rate. 
                # We have quote -> EUR rate (t.fx_rate_to_base) and price = quote/base.
                # base_to_eur = (quote/base) * (eur/quote)? No.
                # base_to_eur = price * quote_to_eur = (quote/base) * (eur/quote) = eur/base. Correct.
                # Price is abs(proceeds / quantity)
                if abs(t.quantity) > 0:
                    price = abs(t.proceeds / t.quantity)
                    base_to_eur = price * t.fx_rate_to_base
                else:
                    base_to_eur = t.fx_rate_to_base # fallback
                
                events.append({
                    'date': t.settle_date,
                    'amount': t.quantity,
                    'currency': base,
                    'fx_rate': base_to_eur,
                    'ref_id': t.id,
                })

        # Sort by date, then ref_id
        events.sort(key=lambda x: (x['date'], x['ref_id']))
        return events

    def _process_currency_stream(self, account_id: int, currency: str, events: list):
        """Standard FIFO matching: acquisitions (amount > 0) matched against disposals (amount < 0)."""
        for event in events:
            amount = event['amount']
            if amount == 0:
                continue

            if amount > 0:
                # Acquisition -> Create new lot
                self._add_fx_lot(account_id, currency, event, amount)
            else:
                # Disposal -> consumes existing lots
                self._match_disposal(account_id, currency, event)

    def _add_fx_lot(self, account_id: int, currency: str, event: dict, quantity: Decimal):
        lot = FXFIFOLot(
            account_id=account_id,
            currency=currency,
            acquisition_date=event['date'],
            original_amount=quantity,
            remaining_amount=quantity,
            cost_basis_total_eur=abs(quantity) * event['fx_rate'],
            cost_basis_per_unit_eur=event['fx_rate'],
            trade_id=event['ref_id']
        )
        self.session.add(lot)
        self.session.flush()

    def _match_disposal(self, account_id: int, currency: str, event: dict):
        amount_to_match = abs(event['amount'])
        date = event['date']
        rate = event['fx_rate']

        # Find open LONG lots (remaining > 0)
        stmt = (
            select(FXFIFOLot)
            .where(FXFIFOLot.account_id == account_id)
            .where(FXFIFOLot.currency == currency)
            .where(FXFIFOLot.remaining_amount > 0)
            .order_by(asc(FXFIFOLot.acquisition_date), asc(FXFIFOLot.id))
        )
        open_lots = self.session.execute(stmt).scalars().all()

        for lot in open_lots:
            if amount_to_match <= 0:
                break

            matched_qty = min(lot.remaining_amount, amount_to_match)
            
            # Proceeds/Cost logic
            cost_basis_matched = matched_qty * lot.cost_basis_per_unit_eur
            proceeds_matched = matched_qty * rate
            
            # Holding period
            d1 = datetime.strptime(lot.acquisition_date, "%Y-%m-%d")
            d2 = datetime.strptime(date, "%Y-%m-%d")
            days_held = (d2 - d1).days
            is_taxable = days_held <= 365

            gain = FXGain(
                account_id=account_id,
                fx_lot_id=lot.id,
                disposal_date=date,
                amount_matched=matched_qty,
                disposal_proceeds_eur=proceeds_matched,
                cost_basis_matched_eur=cost_basis_matched,
                realized_pnl_eur=proceeds_matched - cost_basis_matched,
                days_held=days_held,
                is_taxable_section_23=is_taxable
            )
            self.session.add(gain)
            
            lot.remaining_amount -= matched_qty
            amount_to_match -= matched_qty

        # If amount_to_match > 0 here, it's a disposal with no acquisition (e.g. margin or missing data).
        # Per user request, we ignore these for § 23 if they are not from explicit acquisitions.
        # But we should maybe still create a matching "missing lot" warning in the aggregator?
        # Actually, the user says "only track explicit buy/sell... no other stuff plays a role".
        # So if I sell USD I never "bought", I have no § 23 pool to exhaust.
        self.session.flush()
