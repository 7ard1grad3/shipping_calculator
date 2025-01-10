from pathlib import Path
from .database import Database


class PricingData:
    def __init__(self, excel_path: str, db_path: str = "data/shipping.db"):
        self.excel_path = Path(excel_path)
        self.db = Database(db_path)
        self._load_data()

    def _load_data(self):
        """Load Excel data into SQLite database"""
        self.db.load_excel_data(str(self.excel_path))

    def get_price_for_shipment(self, weight: float, country: str, zipcode: str, service_level: str) -> tuple:
        """Get price from database"""
        return self.db.get_price_for_shipment(weight, country, zipcode, service_level)

    def get_extra_fees(self, weight: float, country: str) -> list:
        """Get applicable extra fees"""
        return self.db.get_extra_fees(weight, country)