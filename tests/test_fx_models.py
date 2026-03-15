from decimal import Decimal
from ibkr_tax.models.database import Account, FXFIFOLot, FXGain

def test_fx_model_relationships(db_session):
    """Tests if FXFIFOLot and FXGain models can be saved and retrieved with correct relationships."""
    # 1. Create Account
    account = Account(account_id="U FX TEST", currency="EUR")
    db_session.add(account)
    db_session.flush()

    # 2. Create FX Lot (Acquisition of USD)
    fx_lot = FXFIFOLot(
        account_id=account.id,
        currency="USD",
        acquisition_date="2023-01-01",
        original_amount=Decimal("1000.00"),
        remaining_amount=Decimal("1000.00"),
        cost_basis_total_eur=Decimal("930.00"),
        cost_basis_per_unit_eur=Decimal("0.93")
    )
    db_session.add(fx_lot)
    db_session.flush()

    # 3. Create FX Gain (Disposal of USD)
    fx_gain = FXGain(
        account_id=account.id,
        fx_lot_id=fx_lot.id,
        disposal_date="2023-02-01",
        amount_matched=Decimal("500.00"),
        disposal_proceeds_eur=Decimal("470.00"),
        cost_basis_matched_eur=Decimal("465.00"),
        realized_pnl_eur=Decimal("5.00"),
        days_held=31,
        is_taxable_section_23=True
    )
    db_session.add(fx_gain)
    db_session.commit()

    # Verification
    retrieved_acc = db_session.query(Account).filter_by(account_id="U FX TEST").first()
    assert retrieved_acc is not None
    assert len(retrieved_acc.fx_fifo_lots) == 1
    assert len(retrieved_acc.fx_gains) == 1

    retrieved_lot = db_session.query(FXFIFOLot).first()
    assert retrieved_lot.currency == "USD"
    assert retrieved_lot.account.account_id == "U FX TEST"

    retrieved_gain = db_session.query(FXGain).first()
    assert retrieved_gain.realized_pnl_eur == Decimal("5.00")
    assert retrieved_gain.fx_lot.currency == "USD"
    assert retrieved_gain.is_taxable_section_23 is True
