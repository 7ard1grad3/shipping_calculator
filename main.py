from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
import logging
from app.models import ShipmentRequest
from app.dependencies import get_calculator
from app.utils.exception_handlers import validation_exception_handler
from app.routes import teldor_routes
from fastapi.openapi.utils import get_openapi

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
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "Teldor",
            "description": "Teldor shipping calculation endpoints"
        },
        {
            "name": "Health",
            "description": "Health check endpoint"
        }
    ],
    openapi_url="/openapi.json"
)

# Hide all routes except /teldor/calculate and /health in the OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes
    )
    
    paths_to_keep = {
        "/teldor/calculate": openapi_schema["paths"].get("/teldor/calculate", {}),
        "/health": openapi_schema["paths"].get("/health", {})
    }
    openapi_schema["paths"] = paths_to_keep
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

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

# Include Teldor routes
app.include_router(teldor_routes.router)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to CTS Shipping Calculator API",
        "docs": "/docs",
        "redoc": "/redoc"
    }

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