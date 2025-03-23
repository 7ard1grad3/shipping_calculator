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
    Line_1_UW: float
    Line_1_UH: float
    Line_1_UD: float
    Line_1_KG: float
    Line_1_total_U: int
    Line_1_total_V: float
    Line_1_total_KG: float
    Line_2_UW: Optional[float] = None
    Line_2_UH: Optional[float] = None
    Line_2_UD: Optional[float] = None
    Line_2_KG: Optional[float] = None
    Line_2_total_U: Optional[int] = None
    Line_2_total_V: Optional[float] = None
    Line_2_total_KG: Optional[float] = None

    class Config:
        json_schema_extra = {
            "example": {
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
                "Shipping_Zip": "222222",
                "Line_1_UW": 0.2,
                "Line_1_UH": 0.2,
                "Line_1_UD": 0.2,
                "Line_1_KG": 10.23,
                "Line_1_total_U": 1,
                "Line_1_total_V": 0.030624999999999996,
                "Line_1_total_KG": 80.23,
                "Line_2_UW": 0.2,
                "Line_2_UH": 0.2,
                "Line_2_UD": 0.2,
                "Line_2_KG": 10.62,
                "Line_2_total_U": 1,
                "Line_2_total_V": 0.030624999999999996,
                "Line_2_total_KG": 50.62
            }
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