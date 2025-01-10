from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class ServiceLevel(str, Enum):
    PRIO = "Prio (1BD)"
    ROAD = "Road (2-3 BD)"
    ECO = "Eco (4-5 BD)"

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