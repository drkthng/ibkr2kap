from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict

class MissingCostBasisWarning(BaseModel):
    """
    Structured warning for missing cost basis.
    """
    symbol: str
    asset_category: str
    quantity: Decimal
    date: str
    trade_id: str

    message: str

class TaxReport(BaseModel):
    """
    TaxReport schema representing aggregated values for German Anlage KAP.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    account_id: str
    tax_year: int
    
    # Line 7: Kapitalerträge (Dividends + Interest + Sonstige gains)
    kap_line_7_kapitalertraege: Decimal = Field(default=Decimal("0.00"))
    
    # Line 8: Gewinne aus Aktienveräußerungen
    kap_line_8_gewinne_aktien: Decimal = Field(default=Decimal("0.00"))
    
    # Line 9: Verluste aus Aktienveräußerungen (absolute value)
    kap_line_9_verluste_aktien: Decimal = Field(default=Decimal("0.00"))
    
    # Line 10: Gewinne/Verluste aus Termingeschäften (netted)
    kap_line_10_termingeschaefte: Decimal = Field(default=Decimal("0.00"))
    
    # Line 15: Ausländische Steuern (Withholding Tax)
    kap_line_15_quellensteuer: Decimal = Field(default=Decimal("0.00"))
    
    # Anlage SO: Fremdwährungsgeschäfte (§ 23 EStG)
    so_fx_gains_total: Decimal = Field(default=Decimal("0.00"))
    so_fx_gains_taxable_1y: Decimal = Field(default=Decimal("0.00"))
    so_fx_gains_tax_free: Decimal = Field(default=Decimal("0.00"))
    so_fx_freigrenze_applies: bool = Field(default=False)

    # Informational: Margin interest paid (not deductible per § 20 Abs. 9 EStG)
    margin_interest_paid: Decimal = Field(default=Decimal("0.00"))

    # Summary Field
    total_realized_pnl: Decimal = Field(default=Decimal("0.00"))

    # Warnings
    missing_cost_basis_warnings: list[MissingCostBasisWarning] = Field(default_factory=list)
