import math
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from app.models import TeladRequest, TeladResponse, ShipmentRequest
from app.mapping.telad.mapper import TeladMapper
from app.dependencies import get_calculator, get_db
import logging

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
                "total_price": result["total_price"],
                "zone": result["zone"],
                "chargeable_weight": result["chargeable_weight"],
                "weight_type": result["weight_type"],
                "base_rate": result["base_rate"],
                "extra_fees": result["extra_fees"]
            },
            "mapping": {
                "mapping_details": {
                    "combined_weight": shipment_data["actual_weight"],
                    "combined_volume": ((shipment_data["length"] * 100) * (shipment_data["width"] * 100) * (shipment_data["height"] * 100)) / 1000000000,
                    "non_stackable_weight": result["non_stackable_weight"],
                    "dimensions": {
                        "length": shipment_data["length"],
                        "width": shipment_data["width"],
                        "height": shipment_data["height"],
                        "num_collo": shipment_data["num_collo"]
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
                error_message=mapping_result["validation"]["message"],
                zone="",
                chargeable_weight=0,
                weight_type="",
                combined_weight=0,
                non_stackable_weight=0,
                dimensions={"length": 0, "width": 0, "height": 0, "num_collo": 0},
                service_levels=[]
            )

        # Extract calculation and mapping details
        calc = mapping_result["calculation"]
        mapping = mapping_result["mapping"]["mapping_details"]
        
        

        # Save calculation to history (using Priority service as default)
        volume_weight = calculator.calculate_volume_weight(
            num_collo=mapping["dimensions"]["num_collo"],
            length=mapping["dimensions"]["length"],
            width=mapping["dimensions"]["width"],
            height=mapping["dimensions"]["height"]
        )
        loading_meter_weight = calculator.calculate_loading_meter_weight(
            num_collo=mapping["dimensions"]["num_collo"],
            length=mapping["dimensions"]["length"],
            width=mapping["dimensions"]["width"]
        )

        # Calculate prices for all service levels
        service_levels = []
        for service_level in ["Economy", "Road Express", "Priority"]:
            try:
                result = calculator.calculate_price(
                    num_collo=int(mapping["dimensions"]["num_collo"]),
                    length=mapping["dimensions"]["length"],
                    width=mapping["dimensions"]["width"],
                    height=mapping["dimensions"]["height"],
                    actual_weight=mapping["combined_weight"],
                    country=mapping["country_code"],
                    zipcode=request_data.Shipping_Zip,
                    service_level=service_level
                )
                print(result)
                service_levels.append({
                    "name": service_level,
                    "price": math.ceil(result["total_price"]),
                    "currency": "eur"
                })

                history_data = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'country': mapping["country_code"],
                'zipcode': request_data.Shipping_Zip,
                'service_level': service_level,
                'num_collo': mapping["dimensions"]["num_collo"],
                'length': mapping["dimensions"]["length"],
                'width': mapping["dimensions"]["width"],
                'height': mapping["dimensions"]["height"],
                'actual_weight': mapping["combined_weight"],
                'volume_weight': volume_weight,
                'loading_meter_weight': loading_meter_weight,
                'chargeable_weight': round(calc["chargeable_weight"], 2),
                'weight_type': calc["weight_type"],
                'zone': calc["zone"],
                'base_rate': math.ceil(result["base_rate"]),
                'extra_fees': math.ceil(result["extra_fees"]),
                'total_price': math.ceil(result["total_price"])
                }
                db.add_calculation_history(history_data)
            except Exception as e:
                logger.error(f"Error calculating price for {service_level}: {str(e)}")
                if not service_levels:  # If this is the first service level and it failed
                    return TeladResponse(
                        status="error",
                        error_message=str(e),
                        zone="",
                        chargeable_weight=0,
                        weight_type="",
                        combined_weight=0,
                        non_stackable_weight=0,
                        dimensions={"length": 0, "width": 0, "height": 0, "num_collo": 0},
                        service_levels=[]
                    )
                continue  # Skip this service level if others are available
        
        # Create response with all service levels
        response = TeladResponse(
            status="success",
            zone=calc["zone"],
            chargeable_weight=round(calc["chargeable_weight"], 2),
            weight_type=calc["weight_type"],
            combined_weight=round(mapping["combined_weight"], 2),
            non_stackable_weight=round(mapping["non_stackable_weight"], 2),
            dimensions={
                "length": round(mapping["dimensions"]["length"], 2),
                "width": round(mapping["dimensions"]["width"], 2),
                "height": round(mapping["dimensions"]["height"], 2),
                "num_collo": mapping["dimensions"]["num_collo"]
            },
            service_levels=service_levels,
            error_message=None
        )

        return response

    except Exception as e:
        logger.error(f"Error in Telad calculation: {str(e)}")
        return TeladResponse(
            status="error",
            error_message=str(e),
            zone="",
            chargeable_weight=0,
            weight_type="",
            combined_weight=0,
            non_stackable_weight=0,
            dimensions={"length": 0, "width": 0, "height": 0, "num_collo": 0},
            service_levels=[]
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