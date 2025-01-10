from fastapi.testclient import TestClient
from main import app
import pytest

client = TestClient(app)


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_calculate_price():
    """Test price calculation endpoint"""
    request_data = {
        "country": "DE",
        "zipcode": "40123",
        "num_collo": 1,
        "length": 120,
        "width": 80,
        "height": 100,
        "actual_weight": 75,
        "service_level": "Prio (1BD)"
    }
    response = client.post("/calculate-price", json=request_data)
    assert response.status_code == 200

    data = response.json()
    assert all(key in data for key in [
        'base_rate', 'extra_fees', 'total_price',
        'zone', 'stackable_weight', 'non_stackable_weight',
        'chargeable_weight', 'weight_type'
    ])


def test_get_zone():
    """Test zone lookup endpoint"""
    response = client.get("/zones/DE/40123")
    assert response.status_code == 200
    data = response.json()
    assert "zone" in data
    assert data["country"] == "DE"
    assert data["zipcode"] == "40123"


def test_get_service_levels():
    """Test service levels endpoint"""
    response = client.get("/service-levels")
    assert response.status_code == 200
    data = response.json()
    assert "service_levels" in data
    assert isinstance(data["service_levels"], list)
    assert "Prio (1BD)" in data["service_levels"]


def test_invalid_country():
    """Test handling of invalid country"""
    response = client.get("/zones/XX/12345")
    assert response.status_code == 400


def test_invalid_dimensions():
    """Test handling of invalid dimensions"""
    request_data = {
        "country": "DE",
        "zipcode": "40123",
        "num_collo": 1,
        "length": 250,  # > 240cm max
        "width": 80,
        "height": 100,
        "actual_weight": 75,
        "service_level": "Prio (1BD)"
    }
    response = client.post("/calculate-price", json=request_data)
    assert response.status_code == 400


def test_invalid_service_level():
    """Test handling of invalid service level"""
    request_data = {
        "country": "DE",
        "zipcode": "40123",
        "num_collo": 1,
        "length": 120,
        "width": 80,
        "height": 100,
        "actual_weight": 75,
        "service_level": "INVALID"
    }
    response = client.post("/calculate-price", json=request_data)
    assert response.status_code == 400