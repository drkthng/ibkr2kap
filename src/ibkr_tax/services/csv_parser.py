import csv
import io
from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import datetime

from ibkr_tax.schemas.ibkr import AccountSchema, TradeSchema, CashTransactionSchema, OptionEAECreate


class CSVActivityParser:
    """
    Parser for IBKR CSV Activity Statements.
    Handles the multi-section format where each section has its own headers.
    """

    def __init__(self, csv_content: Optional[str] = None, csv_path: Optional[str] = None):
        if csv_content:
            self.data = csv_content
        elif csv_path:
            with open(csv_path, "r", encoding="utf-8") as f:
                self.data = f.read()
        else:
            raise ValueError("Either csv_content or csv_path must be provided.")

        self.sections: Dict[str, List[Dict[str, str]]] = {}
        self._parse_raw()

    def _parse_raw(self):
        """Initial pass to break the CSV into sections and rows."""
        reader = csv.reader(io.StringIO(self.data))
        headers: Dict[str, List[str]] = {}

        for row in reader:
            if not row or len(row) < 2:
                continue

            section = row[0]
            row_type = row[1]

            if row_type == "Header":
                headers[section] = row
            elif row_type == "Data":
                if section in headers:
                    # Map headers to data
                    section_headers = headers[section]
                    data_dict = {}
                    for i, val in enumerate(row):
                        if i < len(section_headers):
                            header_name = section_headers[i]
                            if header_name:
                                data_dict[header_name] = val
                    
                    if section not in self.sections:
                        self.sections[section] = []
                    self.sections[section].append(data_dict)

    def get_accounts(self) -> List[AccountSchema]:
        accounts = []
        if "Account Information" in self.sections:
            for row in self.sections["Account Information"]:
                acc_id = row.get("Account ID")
                currency = row.get("Base Currency", "EUR")
                if acc_id:
                    accounts.append(
                        AccountSchema(
                            account_id=acc_id,
                            currency=currency
                        )
                    )
        return accounts

    def get_trades(self) -> List[TradeSchema]:
        trades = []
        if "Trades" in self.sections:
            for row in self.sections["Trades"]:
                # Filter for actual asset trades, ignore things like 'Total' rows if they crept in
                if row.get("Header") == "Data" and row.get("Symbol"):
                    trades.append(
                        TradeSchema(
                            ib_trade_id=row.get("Trade ID", ""),
                            account_id=row.get("Account ID", "UNKNOWN"),
                            asset_category=row.get("Asset Category", "STK"),
                            symbol=row.get("Symbol", ""),
                            description=row.get("Description", ""),
                            trade_date=row.get("Trade Date"),
                            settle_date=row.get("Settle Date Target") or row.get("Date/Time"),
                            currency=row.get("Currency", "USD"),
                            fx_rate_to_base=Decimal(row.get("FX Rate To Base", "1")),
                            quantity=Decimal(row.get("Quantity", "0").replace(",", "")),
                            trade_price=Decimal(row.get("Trade Price", "0").replace(",", "")),
                            proceeds=Decimal(row.get("Proceeds", "0").replace(",", "")),
                            taxes=Decimal(row.get("Taxes", "0").replace(",", "")),
                            ib_commission=Decimal(row.get("Comm/Fee", "0").replace(",", "")),
                            buy_sell=row.get("Buy/Sell", "BUY"),
                            open_close_indicator=row.get("Open/Close Indicator")
                        )
                    )
        return trades

    def get_cash_transactions(self) -> List[CashTransactionSchema]:
        transactions = []
        cash_sections = [
            "Dividends", 
            "Withholding Tax", 
            "Broker Interest Paid", 
            "Broker Interest Received",
            "Bond Interest Received",
            "Bond Interest Paid",
            "Other Fees",
            "Deposits & Withdrawals",
            "Payment In Lieu Of Dividends"
        ]
        
        for section_name in cash_sections:
            if section_name in self.sections:
                for row in self.sections[section_name]:
                    amount_str = row.get("Amount", "0").replace(",", "")
                    if not amount_str:
                        continue
                        
                    transactions.append(
                        CashTransactionSchema(
                            account_id=row.get("Account ID", "UNKNOWN"),
                            symbol=row.get("Symbol"),
                            description=row.get("Description", ""),
                            date_time=row.get("Date/Time", ""),
                            settle_date=row.get("Settle Date") or row.get("Date/Time"),
                            amount=Decimal(amount_str),
                            type=section_name,
                            currency=row.get("Currency", "USD"),
                            fx_rate_to_base=Decimal(row.get("FX Rate To Base", "1")),
                            action_id=row.get("Action ID"),
                            report_date=row.get("Report Date") or row.get("Date/Time")
                        )
                    )
        return transactions

    def get_option_eae(self) -> List[OptionEAECreate]:
        eae_records = []
        # Normalizing section name - IBKR CSV usually uses this long name
        section_name = "Options Exercise, Assignment and Expiration"
        if section_name in self.sections:
            for row in self.sections[section_name]:
                # In CSV, we often have 'Total' rows, skip them
                if row.get("Symbol"):
                    eae_records.append(
                        OptionEAECreate(
                            account_id=row.get("Account ID", "UNKNOWN"),
                            currency=row.get("Currency", "USD"),
                            fx_rate_to_base=Decimal(row.get("FX Rate To Base", "1")),
                            symbol=row.get("Symbol", ""),
                            underlying_symbol=row.get("Underlying Symbol", ""),
                            strike=Decimal(row.get("Strike", "0").replace(",", "")),
                            expiry=row.get("Expiry"),
                            put_call=row.get("Put/Call", "C")[0].upper(), # Ensure 'P' or 'C'
                            date=row.get("Date"),
                            transaction_type=row.get("Type", "").capitalize(),
                            quantity=Decimal(row.get("Quantity", "0").replace(",", "")),
                            trade_price=Decimal(row.get("Trade Price", "0").replace(",", "")),
                            multiplier=Decimal(row.get("Multiplier", "100").replace(",", "")),
                            trade_id=row.get("Trade ID")
                        )
                    )
        return eae_records

    def parse_all(self) -> Dict[str, Any]:
        return {
            "accounts": self.get_accounts(),
            "trades": self.get_trades(),
            "cash_transactions": self.get_cash_transactions(),
            "option_eae": self.get_option_eae(),
        }
