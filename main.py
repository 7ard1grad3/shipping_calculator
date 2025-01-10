from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
from pathlib import Path
from app.models import ShipmentRequest, PriceResponse
from app.calculator import ShippingCalculator
from app.data_loader import PricingData
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="CTS Shipping Price Calculator",
    description="API for calculating shipping prices based on dimensions, weight, and destination",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize pricing data and calculator
data_file = Path("data/CTS flat buy 2024 1.xlsx")
db_file = Path("data/shipping.db")

pricing_data = PricingData(
    excel_path=str(data_file),
    db_path=str(db_file)
)
calculator = ShippingCalculator(pricing_data)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Service is running"}


@app.post("/calculate-price", response_model=PriceResponse)
async def calculate_price(request: ShipmentRequest):
    """
    Calculate shipping price based on dimensions, weight, and destination
    """
    try:
        logger.info(f"Calculating price for shipment: {request.dict()}")
        result = calculator.calculate_price(
            num_collo=request.num_collo,
            length=request.length,
            width=request.width,
            height=request.height,
            actual_weight=request.actual_weight,
            country=request.country,
            zipcode=request.zipcode,
            service_level=request.service_level.value
        )
        logger.info(f"Calculation result: {result}")
        return PriceResponse(**result)
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/zones/{country}/{zipcode}")
async def get_zone(country: str, zipcode: str):
    """Get shipping zone for a country and zipcode"""
    try:
        zone = calculator.get_zone(country, zipcode)
        return {
            "country": country,
            "zipcode": zipcode,
            "zone": zone
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/countries", response_model=Dict[str, List[str]])
async def get_countries():
    """Get list of available countries"""
    try:
        with calculator.pricing_data.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT country 
                FROM zones 
                ORDER BY country
            """)
            countries = [row[0] for row in cursor.fetchall()]
            return {"countries": countries}
    except Exception as e:
        logger.error(f"Error fetching countries: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/service-levels", response_model=Dict[str, List[str]])
async def get_service_levels():
    """Get list of available service levels"""
    try:
        with calculator.pricing_data.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT service_level 
                FROM price_list 
                ORDER BY service_level
            """)
            service_levels = [row[0] for row in cursor.fetchall()]
            return {"service_levels": service_levels}
    except Exception as e:
        logger.error(f"Error fetching service levels: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/price-list/{country}")
async def get_price_list(country: str):
    """Get complete price list for a country"""
    try:
        with calculator.pricing_data.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    weight_range,
                    zone,
                    rate,
                    service_level
                FROM price_list
                WHERE country = ?
                ORDER BY min_weight, service_level
            """, (country,))

            prices = [
                {
                    "weight_range": row[0],
                    "zone": row[1],
                    "rate": row[2],
                    "service_level": row[3]
                }
                for row in cursor.fetchall()
            ]
            return {"prices": prices}
    except Exception as e:
        logger.error(f"Error fetching price list: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/weight-calculation-example")
async def weight_calculation_example():
    """Get example of weight calculations"""
    example = {
        "stackable": {
            "formula": "length × width × height × 330 × number_of_collo (dimensions in meters)",
            "example": {
                "dimensions": "120cm × 80cm × 100cm",
                "collo": 1,
                "calculation": "1.2 × 0.8 × 1.0 × 330 × 1 = 316.8 kg"
            }
        },
        "non_stackable": {
            "formula": "((width × length)/2.4) × number_of_collo × 1750 (dimensions in meters)",
            "example": {
                "dimensions": "120cm × 80cm",
                "collo": 1,
                "calculation": "((1.2 × 0.8)/2.4) × 1 × 1750 = 700 kg"
            }
        },
        "rules": [
            "Height > 120cm forces non-stackable calculation",
            "The highest weight (actual, volume, or loading meter) is used",
            "Maximum dimensions: Length 240cm, Width 120cm, Height 220cm"
        ]
    }
    return example


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)