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
    kap_termingeschaefte_gains: Decimal = Field(default=Decimal("0.00"))
    kap_termingeschaefte_losses: Decimal = Field(default=Decimal("0.00"))
    
    # Line 15: Ausländische Steuern (Withholding Tax)
    kap_line_15_quellensteuer: Decimal = Field(default=Decimal("0.00"))
    
    # Anlage SO: Fremdwährungsgeschäfte (§ 23 EStG)
    so_fx_gains_total: Decimal = Field(default=Decimal("0.00"))
    so_fx_gains_taxable_1y: Decimal = Field(default=Decimal("0.00"))
    so_fx_gains_tax_free: Decimal = Field(default=Decimal("0.00"))
    so_fx_freigrenze_applies: bool = Field(default=False)

    # Informational: Margin interest paid (not deductible per § 20 Abs. 9 EStG)
    margin_interest_paid: Decimal = Field(default=Decimal("0.00"))

    # === Tax-Pool Summary Fields ===
    # Aktientopf: Net result (Line 8 - Line 9) — stands alone, cannot offset other pools
    aktien_net_result: Decimal = Field(default=Decimal("0.00"))

    # Allgemeiner Topf: Line 7 + Line 10 — dividends, interest, sonstige, termingeschäfte can cross-offset
    allgemeiner_topf_result: Decimal = Field(default=Decimal("0.00"))

    # Sub-components for transparency
    dividends_interest_total: Decimal = Field(default=Decimal("0.00"))
    sonstige_gains_total: Decimal = Field(default=Decimal("0.00"))

    # Warnings
    missing_cost_basis_warnings: list[MissingCostBasisWarning] = Field(default_factory=list)

class CombinedTaxReport(BaseModel):
    """
    Combined report for multiple accounts.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    account_ids: list[str]
    tax_year: int

    # Combined totals (same fields as TaxReport)
    kap_line_7_kapitalertraege: Decimal = Field(default=Decimal("0.00"))
    kap_line_8_gewinne_aktien: Decimal = Field(default=Decimal("0.00"))
    kap_line_9_verluste_aktien: Decimal = Field(default=Decimal("0.00"))
    kap_line_10_termingeschaefte: Decimal = Field(default=Decimal("0.00"))
    kap_termingeschaefte_gains: Decimal = Field(default=Decimal("0.00"))
    kap_termingeschaefte_losses: Decimal = Field(default=Decimal("0.00"))
    kap_line_15_quellensteuer: Decimal = Field(default=Decimal("0.00"))
    
    so_fx_gains_total: Decimal = Field(default=Decimal("0.00"))
    so_fx_gains_taxable_1y: Decimal = Field(default=Decimal("0.00"))
    so_fx_gains_tax_free: Decimal = Field(default=Decimal("0.00"))
    so_fx_freigrenze_applies: bool = Field(default=False)

    margin_interest_paid: Decimal = Field(default=Decimal("0.00"))

    aktien_net_result: Decimal = Field(default=Decimal("0.00"))
    allgemeiner_topf_result: Decimal = Field(default=Decimal("0.00"))
    dividends_interest_total: Decimal = Field(default=Decimal("0.00"))
    sonstige_gains_total: Decimal = Field(default=Decimal("0.00"))

    # Breakdowns
    per_account_reports: list[TaxReport] = Field(default_factory=list)
    missing_cost_basis_warnings: list[MissingCostBasisWarning] = Field(default_factory=list)
