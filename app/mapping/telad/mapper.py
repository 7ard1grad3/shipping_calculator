import logging
from typing import Dict, Any
from iso3166 import countries

logger = logging.getLogger(__name__)

class TeladMapper:
    @staticmethod
    def convert_iso3_to_iso2(country_code: str) -> str:
        """Convert ISO 3166-1 alpha-3 to alpha-2 country code"""
        try:
            country = countries.get(country_code)
            if country:
                return country.alpha2
            raise ValueError(f"Invalid country code: {country_code}")
        except KeyError:
            raise ValueError(f"Invalid country code: {country_code}")
        except Exception as e:
            logger.error(f"Error converting country code {country_code}: {str(e)}")
            raise ValueError(f"Invalid country code: {country_code}")

    @staticmethod
    def calculate_combined_dimensions(request_data: Dict[Any, Any]) -> dict:
        """Calculate combined dimensions and total weight from line items"""
        logger.info("Validating dimensions")
        
        # Extract line items
        line_items = request_data.get('line_items', {})
        if not line_items:
            raise ValueError("No line items found in request")

        total_weight = 0
        total_volume = 0
        max_width = 0
        max_length = 0
        total_height = 0
        num_collo = 0

        # Process each line item
        for line_num, item in line_items.items():
            try:
                # Get dimensions and weight
                width = float(item.get('UW', 0))
                height = float(item.get('UH', 0))
                depth = float(item.get('UD', 0))
                weight = float(item.get('KG', 0))
                quantity = int(item.get('total_U', 1))

                # Validate dimensions
                if not all([width, height, depth, weight]):
                    raise ValueError(f"Invalid dimensions in line item {line_num}")

                # Convert dimensions to centimeters (if they're in meters)
                width = width * 100
                height = height * 100
                depth = depth * 100
                print(weight)
                # Update maximums
                max_width = max(max_width, width)
                max_length = max(max_length, depth)
                total_height += height
                total_weight += weight
                total_volume += (width * height * depth) / 1000000  # Convert to m³
                num_collo += quantity

            except (ValueError, TypeError) as e:
                raise ValueError(f"Error processing line item {line_num}: {str(e)}")

        if not all([max_width, max_length, total_height, total_weight]):
            raise ValueError("Invalid combined dimensions")

        return {
            "num_collo": num_collo,
            "length": max_length,
            "width": max_width,
            "height": total_height,
            "actual_weight": total_weight,
            "volume": total_volume
        }

    @classmethod
    def map_request_to_shipment(cls, request_data: Dict[Any, Any]) -> dict:
        """Map external request format to internal ShipmentRequest format"""
        try:
            # Get shipping country code (convert from ISO3 to ISO2)
            country_iso2 = cls.convert_iso3_to_iso2(request_data['Shipping_Country'])

            # Extract line items from the request
            line_items = {}
            for key, value in request_data.items():
                if key.startswith('Line_'):
                    parts = key.split('_')
                    if len(parts) >= 3:
                        line_num = parts[1]
                        field = '_'.join(parts[2:])
                        if line_num not in line_items:
                            line_items[line_num] = {}
                        line_items[line_num][field] = value

            # Add line items to request data
            request_data['line_items'] = line_items

            # Calculate combined dimensions
            combined_dims = cls.calculate_combined_dimensions(request_data)

            return {
                "country": country_iso2,
                "zipcode": request_data['Shipping_Zip'],
                "num_collo": combined_dims['num_collo'],
                "length": combined_dims['length'],
                "width": combined_dims['width'],
                "height": combined_dims['height'],
                "actual_weight": combined_dims['actual_weight'],
                "service_level": "Economy"  # Default service
            }
        except Exception as e:
            logger.error(f"Error mapping request: {str(e)}")
            raise ValueError(f"Error mapping request: {str(e)}")