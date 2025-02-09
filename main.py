from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
import logging
from app.models import ShipmentRequest
from app.dependencies import get_calculator
from app.utils.exception_handlers import validation_exception_handler
from app.routes import telad_routes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="CTS Shipping Calculator API",
    description="API for calculating shipping prices based on dimensions and weight",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Include Telad routes
app.include_router(telad_routes.router)


@app.post("/calculate-price")
async def calculate_price(request: ShipmentRequest, calculator=Depends(get_calculator)):
    """Calculate shipping price based on shipment details"""
    try:
        logger.info(f"Received calculation request: {request}")

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

        logger.info(f"Calculation complete: {result}")
        return {
            "status": "success",
            "calculation": result
        }

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health")
async def health_check(calculator=Depends(get_calculator)):
    """Health check endpoint"""
    try:
        # Try to connect to the database
        with calculator.pricing_data.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")

        return {
            "status": "healthy",
            "message": "Service is running",
            "database": "connected",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "message": "Service is experiencing issues",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )