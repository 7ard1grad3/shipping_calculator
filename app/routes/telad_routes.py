import math
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
import logging

from app.mapping.telad.mapper import TeladMapper
from app.models import TeladRequest, ShipmentRequest, TeladResponse, TeladCalculationResult, TeladMappingDetails
from app.dependencies import get_calculator, get_db
from typing import Dict, Any

from configurations import DEFAULT_SHIPPING_SERVICE

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/telad",
    tags=["telad"]
)


async def map_request(request_data: TeladRequest, calculator=Depends(get_calculator)):
    """Map and validate external request format, then calculate price"""
    try:
        logger.info(f"Received mapping request: {request_data}")

        # Map external request to internal format using TeladMapper
        shipment_data = TeladMapper.map_request_to_shipment(request_data.model_dump())
        logger.info(f"Mapped to internal format: {shipment_data}")

        # Calculate price using mapped data
        shipment_request = ShipmentRequest(**shipment_data)
        result = calculator.calculate_price(
            num_collo=shipment_request.num_collo,
            length=shipment_request.length,
            width=shipment_request.width,
            height=shipment_request.height,
            actual_weight=shipment_request.actual_weight,
            country=shipment_request.country,
            zipcode=shipment_request.zipcode,
            service_level=shipment_request.service_level.value
        )

        # Format the response
        return {
            "status": "success",
            "calculation": {
                "base_rate": result["base_rate"],
                "extra_fees": result["extra_fees"],
                "total_price": result["total_price"],
                "zone": result["zone"],
                "chargeable_weight": result["chargeable_weight"],
                "weight_type": result["weight_type"],
                "fee_breakdown": result["fee_breakdown"]
            },
            "mapping": {
                "mapping_details": {
                    "combined_weight": shipment_data["actual_weight"],
                    "combined_volume": ((shipment_data["length"] * 100) * (shipment_data["width"] * 100) * (shipment_data["height"] * 100)) / 1000000000,
                    "dimensions": {
                        "length": shipment_data["length"],
                        "width": shipment_data["width"],
                        "height": shipment_data["height"]
                    },
                    "service_level": shipment_data["service_level"],
                    "country_code": shipment_data["country"]
                }
            }
        }

    except ValueError as e:
        logger.error(f"Validation error in mapping: {str(e)}")
        return {
            "status": "error",
            "validation": {
                "message": str(e)
            }
        }
    except Exception as e:
        logger.error(f"Unexpected error in mapping: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/calculate", response_model=TeladResponse)
async def calculate_telad(request_data: TeladRequest, calculator=Depends(get_calculator), db=Depends(get_db)):
    """Calculate price based on Telad request format"""
    try:
        logger.info(f"Received Telad calculation request: {request_data}")

        # Map and validate the request
        mapping_result = await map_request(request_data, calculator)

        if mapping_result["status"] == "error":
            return TeladResponse(
                status="error",
                error_message=mapping_result["validation"]["message"]
            )

        # Create response with proper models
        calculation = TeladCalculationResult(**mapping_result["calculation"])
        mapping_details = TeladMappingDetails(**mapping_result["mapping"]["mapping_details"])
        
        # Save calculation to history
        history_data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'country': mapping_details.country_code,
            'zipcode': request_data.Shipping_Zip,
            'service_level': mapping_details.service_level,
            'num_collo': int(mapping_details.dimensions['length'] / 100),  # Convert cm to m
            'length': mapping_details.dimensions['length'],
            'width': mapping_details.dimensions['width'],
            'height': mapping_details.dimensions['height'],
            'actual_weight': mapping_details.combined_weight,
            'volume_weight': calculation.chargeable_weight if calculation.weight_type == 'volume' else 0,
            'loading_meter_weight': calculation.chargeable_weight if calculation.weight_type == 'loading_meter' else 0,
            'chargeable_weight': calculation.chargeable_weight,
            'weight_type': calculation.weight_type,
            'zone': calculation.zone,
            'base_rate': calculation.base_rate,
            'extra_fees': calculation.extra_fees,
            'total_price': calculation.total_price
        }
        
        db.add_calculation_history(history_data)
        
        response = TeladResponse(
            status="success",
            calculation=calculation,
            mapping_details=mapping_details
        )

        return response

    except Exception as e:
        logger.error(f"Error in Telad calculation: {str(e)}")
        return TeladResponse(
            status="error",
            error_message=str(e)
        )


@router.post("/map")
async def map_telad_request(request_data: TeladRequest, calculator=Depends(get_calculator)):
    """Map and validate Telad request format"""
    return await map_request(request_data, calculator)


@router.post("/validate")
async def validate_telad_request(request_data: TeladRequest):
    """Validate Telad request format without processing"""
    try:
        return {
            "status": "success",
            "valid": True,
            "message": "Request format is valid",
            "data": request_data.model_dump()
        }
    except Exception as e:
        return {
            "status": "error",
            "valid": False,
            "message": str(e)
        }