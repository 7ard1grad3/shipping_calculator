from enum import Enum
from pydantic import BaseModel, Field, model_validator, field_validator
from typing import Optional, Dict, Any, List
import re

class ServiceLevel(str, Enum):
    PRIO = "Priority"
    ROAD = "Road Express"
    ECO = "Economy"

class WeightType(str, Enum):
    ACTUAL = "actual"
    VOLUME = "volume"
    LOADING_METER = "loading_meter"

class ShipmentRequest(BaseModel):
    country: str = Field(..., min_length=2, max_length=2, description="Destination country code")
    zipcode: str = Field(..., min_length=4, max_length=10, description="Destination zip/postal code")
    num_collo: int = Field(..., gt=0, description="Number of collo")
    length: float = Field(..., gt=0, le=240, description="Length in cm")
    width: float = Field(..., gt=0, le=120, description="Width in cm")
    height: float = Field(..., gt=0, le=220, description="Height in cm")
    actual_weight: float = Field(..., gt=0, le=1000, description="Actual weight in kg")
    service_level: ServiceLevel = Field(..., description="Service level")
    weight_type: Optional[WeightType] = Field(
        default=WeightType.VOLUME,
        description="Weight type to use for calculation (actual, volume, or loading_meter)"
    )

class PriceResponse(BaseModel):
    base_rate: float
    extra_fees: float
    total_price: float
    zone: str
    stackable_weight: float
    non_stackable_weight: float
    chargeable_weight: float
    weight_type: str


class TeldorRequest(BaseModel):
    ICL_POST_ID: int
    login: str
    Currency: str
    ICL_POST_TIME: int
    Dispatch_City: str
    Dispatch_Country: str
    Sea_Air_Land: str
    Incoterm: str
    Shipping_City: str
    Shipping_Country: str
    Shipping_Zip: str
    line_items: Optional[Dict[str, Dict[str, Any]]] = None
    extra_data: Optional[Dict[str, Any]] = None

    @model_validator(mode='before')
    def extract_line_items(cls, data: Any) -> Any:
        """Extract and validate line items from the request"""
        if not isinstance(data, dict):
            raise ValueError("Input must be a dictionary")

        line_items = {}
        line_pattern = re.compile(r'^Line_(\d+)_(.+)$')

        # Extract line items
        for key, value in dict(data).items():
            match = line_pattern.match(key)
            if match:
                line_num, field = match.groups()
                if line_num not in line_items:
                    line_items[line_num] = {}
                line_items[line_num][field] = value

                # Store the original key-value in extra_data
                if 'extra_data' not in data:
                    data['extra_data'] = {}
                data['extra_data'][key] = value

        # Validate each line item
        if not line_items:
            raise ValueError("No valid line items found in request")

        for line_num, item in line_items.items():
            required_fields = ['UW', 'UH', 'UD', 'KG', 'total_U']
            missing_fields = [f for f in required_fields if f not in item]
            if missing_fields:
                raise ValueError(f"Line {line_num} missing required fields: {', '.join(missing_fields)}")

            # Validate numeric values
            for field in ['UW', 'UH', 'UD', 'KG', 'total_U']:
                try:
                    item[field] = float(item[field])
                except (ValueError, TypeError):
                    raise ValueError(f"Line {line_num} field {field} must be numeric")

        data['line_items'] = line_items
        return data

    @field_validator('Shipping_Country')
    def validate_shipping_country(cls, v: str) -> str:
        if len(v) != 3:
            raise ValueError('Shipping country code must be ISO 3166-1 alpha-3 format')
        return v

    @field_validator('Dispatch_Country')
    def validate_dispatch_country(cls, v: str) -> str:
        if len(v) != 3:
            raise ValueError('Dispatch country code must be ISO 3166-1 alpha-3 format')
        return v

    @field_validator('Sea_Air_Land')
    def validate_transport_mode(cls, v: str) -> str:
        valid_modes = ['Sea', 'Air', 'Land']
        if v not in valid_modes:
            raise ValueError(f'Transport mode must be one of: {", ".join(valid_modes)}')
        return v

    @field_validator('Currency')
    def validate_currency(cls, v: str) -> str:
        valid_currencies = ['USD', 'EUR', 'ILS']
        if v not in valid_currencies:
            raise ValueError(f'Currency must be one of: {", ".join(valid_currencies)}')
        return v

    model_config = {
        "extra": "allow"  # Allow extra fields
    }

class TeldorMappingDetails(BaseModel):
    """Details about how the request was mapped to internal format"""
    combined_weight: float
    combined_volume: float
    dimensions: Dict[str, float]
    service_level: str
    country_code: str

class TeldorCalculationResult(BaseModel):
    """Result of the shipping price calculation"""
    base_rate: float
    extra_fees: float
    total_price: float
    zone: str
    chargeable_weight: float
    weight_type: str
    fee_breakdown: Dict[str, Any]

class ServiceLevelDetails(BaseModel):
    """Service level details"""
    name: str
    price: float
    currency: str = "eur"

class TeldorResponse(BaseModel):
    """Response model for Teldor calculation endpoint"""
    status: str
    zone: str
    chargeable_weight: float
    weight_type: str
    combined_weight: float
    non_stackable_weight: float
    dimensions: Dict[str, float]
    service_levels: List[ServiceLevelDetails]
    error_message: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "zone": "22",
                "chargeable_weight": 127.60416666666667,
                "weight_type": "loading_meter",
                "combined_weight": 125.85,
                "non_stackable_weight": 127.60416666666667,
                "dimensions": {
                    "length": 35.0,
                    "width": 25.0,
                    "height": 70.0,
                    "num_collo": 2.0
                },
                "service_levels": [
                    {
                        "name": "Economy",
                        "price": 290,
                        "currency": "eur"
                    },
                    {
                        "name": "Road Express",
                        "price": 290,
                        "currency": "eur"
                    },
                    {
                        "name": "Priority",
                        "price": 290,
                        "currency": "eur"
                    }
                ],
                "error_message": None
            }
        }