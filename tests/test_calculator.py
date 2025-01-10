import pytest
from app.calculator import ShippingCalculator
from app.data_loader import PricingData
import os
from pathlib import Path


@pytest.fixture
def calculator():
    # Use a test database path
    test_db_path = "data/test_shipping.db"
    data_path = "data/CTS flat buy 2024 1.xlsx"

    if not Path(data_path).exists():
        pytest.skip("Test data file not found")

    pricing_data = PricingData(
        excel_path=data_path,
        db_path=test_db_path
    )

    calculator = ShippingCalculator(pricing_data)

    yield calculator

    # Cleanup test database
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


def test_calculate_volume_weight(calculator):
    """Test volume weight calculation"""
    weight = calculator.calculate_volume_weight(
        num_collo=1,
        length=120,
        width=80,
        height=100
    )
    expected = 1 * (1.2 * 0.8 * 1.0) * 330
    assert abs(weight - expected) < 0.01


def test_calculate_loading_meter_weight(calculator):
    """Test loading meter weight calculation"""
    weight = calculator.calculate_loading_meter_weight(
        num_collo=1,
        length=120,
        width=80
    )
    expected = ((1.2 * 0.8) / 2.4) * 1 * 1750
    assert abs(weight - expected) < 0.01


def test_price_calculation_stackable(calculator):
    """Test price calculation for stackable shipment"""
    result = calculator.calculate_price(
        num_collo=1,
        length=120,
        width=80,
        height=100,
        actual_weight=75,
        country="DE",
        zipcode="40123",
        service_level="Prio (1BD)"
    )

    assert isinstance(result, dict)
    assert all(key in result for key in [
        'base_rate', 'extra_fees', 'total_price',
        'zone', 'stackable_weight', 'non_stackable_weight',
        'chargeable_weight', 'weight_type'
    ])
    assert result['weight_type'] in ['actual', 'volume', 'loading_meter']


def test_price_calculation_non_stackable(calculator):
    """Test price calculation for non-stackable shipment (height > 120)"""
    result = calculator.calculate_price(
        num_collo=1,
        length=120,
        width=80,
        height=150,  # > 120cm, should force non-stackable
        actual_weight=75,
        country="DE",
        zipcode="40123",
        service_level="Prio (1BD)"
    )

    assert result['weight_type'] == 'loading_meter'


def test_invalid_dimensions(calculator):
    """Test handling of invalid dimensions"""
    with pytest.raises(ValueError):
        calculator.calculate_price(
            num_collo=1,
            length=250,  # > 240cm max
            width=80,
            height=100,
            actual_weight=75,
            country="DE",
            zipcode="40123",
            service_level="Prio (1BD)"
        )


def test_invalid_weight(calculator):
    """Test handling of invalid weight"""
    with pytest.raises(ValueError):
        calculator.calculate_price(
            num_collo=1,
            length=120,
            width=80,
            height=100,
            actual_weight=1200,  # > 1000kg max
            country="DE",
            zipcode="40123",
            service_level="Prio (1BD)"
        )


def test_invalid_zipcode(calculator):
    """Test handling of invalid zip code"""
    with pytest.raises(ValueError):
        calculator.calculate_price(
            num_collo=1,
            length=120,
            width=80,
            height=100,
            actual_weight=75,
            country="DE",
            zipcode="99999",  # Invalid zip code prefix
            service_level="Prio (1BD)"
        )


def test_invalid_service_level(calculator):
    """Test handling of invalid service level"""
    with pytest.raises(ValueError):
        calculator.calculate_price(
            num_collo=1,
            length=120,
            width=80,
            height=100,
            actual_weight=75,
            country="DE",
            zipcode="40123",
            service_level="INVALID"  # Invalid service level
        )


def test_weight_type_selection(calculator):
    """Test weight type selection"""
    # Test with volume weight type (default)
    result_volume = calculator.calculate_price(
        num_collo=1,
        length=120,
        width=80,
        height=100,
        actual_weight=75,
        country="DE",
        zipcode="40123",
        service_level="Prio (1BD)",
        weight_type='volume'
    )
    assert result_volume['weight_type'] == 'volume'

    # Test with actual weight type
    result_actual = calculator.calculate_price(
        num_collo=1,
        length=120,
        width=80,
        height=100,
        actual_weight=75,
        country="DE",
        zipcode="40123",
        service_level="Prio (1BD)",
        weight_type='actual'
    )
    assert result_actual['weight_type'] == 'actual'

    # Test with loading meter weight type
    result_ldm = calculator.calculate_price(
        num_collo=1,
        length=120,
        width=80,
        height=100,
        actual_weight=75,
        country="DE",
        zipcode="40123",
        service_level="Prio (1BD)",
        weight_type='loading_meter'
    )
    assert result_ldm['weight_type'] == 'loading_meter'

    