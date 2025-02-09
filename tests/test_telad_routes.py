import os
import sys
import pytest
from fastapi.testclient import TestClient

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

client = TestClient(app)

def test_telad_calculate():
    request_data = {
        "ICL_POST_ID": 1732535225,
        "login": "mzimmer@fibersystems.com",
        "Currency": "USD",
        "ICL_POST_TIME": 1732535225,
        "Dispatch_City": "Kibbutz Ein Dor",
        "Dispatch_Country": "ISR",
        "Sea_Air_Land": "Land",
        "Incoterm": "DAP",
        "Shipping_City": "Ashdod",
        "Shipping_Country": "DEU",
        "Shipping_Zip": "22222",
        "Line_1_UW": 0.25,
        "Line_1_UH": 0.35,
        "Line_1_UD": 0.35,
        "Line_1_KG": 8.23,
        "Line_1_total_U": 1,
        "Line_1_total_V": 0.030624999999999996,
        "Line_1_total_KG": 8.23,
        "Line_2_UW": 0.25,
        "Line_2_UH": 0.35,
        "Line_2_UD": 0.35,
        "Line_2_KG": 17.62,
        "Line_2_total_U": 1,
        "Line_2_total_V": 0.030624999999999996,
        "Line_2_total_KG": 17.62
    }

    response = client.post("/telad/calculate", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "success"
    assert "calculation" in data
    assert "mapping_details" in data
    
    # Validate calculation details
    calculation = data["calculation"]
    assert "base_rate" in calculation
    assert "extra_fees" in calculation
    assert "total_price" in calculation
    assert "zone" in calculation
    assert "chargeable_weight" in calculation
    assert "weight_type" in calculation
    
    # Validate mapping details
    mapping = data["mapping_details"]
    assert "combined_weight" in mapping
    assert "combined_volume" in mapping
    assert "dimensions" in mapping
