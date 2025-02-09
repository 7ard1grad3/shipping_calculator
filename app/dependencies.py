from pathlib import Path
from fastapi import Depends
from app.calculator import ShippingCalculator
from app.database import Database
from app.data_loader import PricingData
from configurations import EXCEL_FILE

_calculator = None
_database = None


def init_calculator():
    """Initialize the calculator instance"""
    global _calculator
    if _calculator is None:
        data_file = Path(f"data/{EXCEL_FILE}")
        db_file = Path("data/shipping.db")

        pricing_data = PricingData(
            excel_path=str(data_file),
            db_path=str(db_file)
        )
        _calculator = ShippingCalculator(pricing_data)
    return _calculator


def init_database():
    global _database
    if _database is None:
        _database = Database()
    return _database


def get_calculator():
    """Dependency to get calculator instance"""
    return init_calculator()


def get_db():
    """Dependency to get database instance"""
    return init_database()