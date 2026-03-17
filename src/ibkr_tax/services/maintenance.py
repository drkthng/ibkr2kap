from sqlalchemy import delete
from ibkr_tax.models.database import (
    Trade, CashTransaction, FIFOLot, FXFIFOLot,
    FXGain, Gain, CorporateAction
)

class MaintenanceService:
    """Service for database maintenance tasks like resetting data."""

    def __init__(self, session):
        self.session = session

    def reset_database(self):
        """
        Permanently deletes all transaction and result data.
        Keeps Account metadata.
        """
        models_to_clear = [
            Gain,
            FXGain,
            FIFOLot,
            FXFIFOLot,
            CorporateAction,
            Trade,
            CashTransaction
        ]
        
        for model in models_to_clear:
            self.session.execute(delete(model))
        
        self.session.commit()
