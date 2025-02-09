import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Authentication settings
USERNAME = os.getenv('USERNAME', 'admin')
PASSWORD = os.getenv('PASSWORD', 'shipping2025')  # You should change this to a more secure password

# Application settings
DEFAULT_WEIGHT_TYPE = os.getenv('DEFAULT_WEIGHT_TYPE', 'volume') # 'actual', 'volume', or 'loading_meter'
NNR_PREMIUM_FEES = float(os.getenv('NNR_PREMIUM_FEES', '20'))
UNILOG_PREMIUM_FEES = float(os.getenv('UNILOG_PREMIUM_FEES', '35'))
FUEL_SURCHARGE = float(os.getenv('FUEL_SURCHARGE', '8'))
DEFAULT_SHIPPING_SERVICE = os.getenv('DEFAULT_SHIPPING_SERVICE', 'Economy')
EXCEL_FILE = os.getenv('EXCEL_FILE', 'CTS flat buy 2025.xlsx')