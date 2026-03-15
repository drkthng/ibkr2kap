import re
from decimal import Decimal
from typing import List, Any
from datetime import datetime, date

from ibflex import parser
from ibflex.Types import FlexStatement, Trade, CashTransaction

from ibkr_tax.schemas.ibkr import AccountSchema, TradeSchema, CashTransactionSchema, OptionEAECreate


class FlexXMLParser:
    """Service for parsing IBKR Flex Query XML files into validated Pydantic models."""

    def __init__(self, xml_content: str | None = None, xml_path: str | None = None):
        if xml_content:
            data = xml_content
        elif xml_path:
            with open(xml_path, "r", encoding="utf-8") as f:
                data = f.read()
        else:
            raise ValueError("Either xml_content or xml_path must be provided.")

        # Preprocessing to handle ibflex 0.15 incompatibilities with new IBKR attributes
        self.action_ids = {} # (account_id, dateTime_str, amount_str, type_str) -> actionID
        
        self.clean_data = self._preprocess(data)
        self.response = parser.parse(self.clean_data.encode("utf-8"))

    def _preprocess(self, data: str) -> str:
        # Match CashTransaction tags (case-insensitive for safety, but IBKR uses CamelCase)
        ct_pattern = re.compile(r'<CashTransaction\s+([^>]+)>', re.IGNORECASE)
        
        def process_ct(match):
            attrs_str = match.group(1)
            aid_match = re.search(r'actionID="([^"]+)"', attrs_str)
            if aid_match:
                aid = aid_match.group(1)
                account_id = re.search(r'accountId="([^"]+)"', attrs_str)
                date_time = re.search(r'dateTime="([^"]+)"', attrs_str)
                amount = re.search(r'amount="([^"]+)"', attrs_str)
                tx_type = re.search(r'type="([^"]+)"', attrs_str)
                
                if account_id and date_time and amount and tx_type:
                    # Use the raw strings from XML as keys
                    # Normalize type string (ibflex might use values like 'Withholding Tax')
                    key = (account_id.group(1), date_time.group(1), amount.group(1), tx_type.group(1))
                    self.action_ids[key] = aid
            
            # Strip identified problematic attributes for ibflex 0.15
            clean_attrs = re.sub(r'\bactionID="[^"]*"', '', attrs_str)
            clean_attrs = re.sub(r'\bisin="[^"]*"', '', clean_attrs)
            return f'<CashTransaction {clean_attrs}>'

        clean_data = ct_pattern.sub(process_ct, data)
        return clean_data

    def _get_val(self, obj: Any) -> Any:
        """Helper to get value from Enum or raw value."""
        if hasattr(obj, "value"):
            return obj.value
        return obj

    def _dt_to_xml_str(self, dt: Any) -> str:
        """Convert datetime/date back to IBKR XML format YYYYMMDD;HHMMSS or YYYYMMDD."""
        if isinstance(dt, datetime):
            return dt.strftime("%Y%m%d;%H%M%S")
        if isinstance(dt, date):
            return dt.strftime("%Y%m%d")
        return str(dt)

    def get_accounts(self) -> List[AccountSchema]:
        accounts = []
        for statement in self.response.FlexStatements:
            account_id = getattr(statement, "accountId", "UNKNOWN")
            currency = getattr(statement, "baseCurrency", "EUR")
            accounts.append(
                AccountSchema(
                    account_id=account_id,
                    currency=currency
                )
            )
        return accounts

    def get_trades(self) -> List[TradeSchema]:
        trades = []
        for statement in self.response.FlexStatements:
            account_id = getattr(statement, "accountId", "UNKNOWN")
            for trade in statement.Trades:
                trades.append(
                    TradeSchema(
                        ib_trade_id=str(trade.tradeID),
                        account_id=account_id,
                        asset_category=self._get_val(trade.assetCategory),
                        symbol=trade.symbol,
                        description=trade.description,
                        trade_date=trade.tradeDate,
                        settle_date=trade.settleDateTarget,
                        currency=trade.currency,
                        fx_rate_to_base=Decimal(str(trade.fxRateToBase)),
                        quantity=Decimal(str(trade.quantity)),
                        trade_price=Decimal(str(trade.tradePrice)),
                        proceeds=Decimal(str(trade.proceeds)),
                        taxes=Decimal(str(trade.taxes)) if trade.taxes is not None else Decimal("0"),
                        ib_commission=Decimal(str(trade.ibCommission)) if trade.ibCommission is not None else Decimal("0"),
                        buy_sell=self._get_val(trade.buySell),
                        open_close_indicator=trade.openCloseIndicator
                    )
                )
        return trades

    def get_cash_transactions(self) -> List[CashTransactionSchema]:
        transactions = []
        for statement in self.response.FlexStatements:
            account_id = getattr(statement, "accountId", "UNKNOWN")
            for ct in statement.CashTransactions:
                # Map back the action_id using extracted data
                # Reconstruct the XML key using the formatted dateTime
                dt_str = self._dt_to_xml_str(ct.dateTime)
                type_str = str(self._get_val(ct.type))
                amount_str = str(ct.amount)
                
                key = (account_id, dt_str, amount_str, type_str)
                action_id = self.action_ids.get(key)
                
                transactions.append(
                    CashTransactionSchema(
                        account_id=account_id,
                        symbol=ct.symbol,
                        description=ct.description,
                        date_time=str(ct.dateTime), # Keep the Pydantic field as a string but validated by it later if needed
                        settle_date=ct.settleDate,
                        amount=Decimal(str(ct.amount)),
                        type=self._get_val(ct.type),
                        currency=ct.currency,
                        fx_rate_to_base=Decimal(str(ct.fxRateToBase)),
                        action_id=action_id,
                        report_date=ct.reportDate
                    )
                )
        return transactions

    def get_option_eae(self) -> List[OptionEAECreate]:
        eae_records = []
        for statement in self.response.FlexStatements:
            account_id = getattr(statement, "accountId", "UNKNOWN")
            if hasattr(statement, "OptionEAE"):
                for eae in statement.OptionEAE:
                    eae_records.append(
                        OptionEAECreate(
                            account_id=account_id,
                            currency=eae.currency,
                            fx_rate_to_base=Decimal(str(eae.fxRateToBase)),
                            symbol=eae.symbol,
                            underlying_symbol=eae.underlyingSymbol,
                            strike=Decimal(str(eae.strike)),
                            expiry=eae.expiry,
                            put_call=self._get_val(eae.putCall),
                            date=eae.date,
                            transaction_type=self._get_val(eae.transactionType).capitalize(),
                            quantity=Decimal(str(eae.quantity)),
                            trade_price=Decimal(str(eae.tradePrice)),
                            multiplier=Decimal(str(eae.multiplier)),
                            trade_id=str(eae.tradeID) if hasattr(eae, "tradeID") and eae.tradeID else None
                        )
                    )
        return eae_records

    def get_corporate_actions(self) -> List[CorporateActionSchema]:
        # Placeholder for real XML parsing of corporate actions if needed
        return []

    def parse_all(self):
        return {
            "accounts": self.get_accounts(),
            "trades": self.get_trades(),
            "cash_transactions": self.get_cash_transactions(),
            "option_eae": self.get_option_eae(),
            "corporate_actions": self.get_corporate_actions(),
        }
