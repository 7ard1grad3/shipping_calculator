from configurations import DEFAULT_WEIGHT_TYPE
from .data_loader import PricingData


class ShippingCalculator:
    def __init__(self, pricing_data: PricingData):
        self.pricing_data = pricing_data

    def calculate_volume_weight(self, num_collo: int, length: float, width: float, height: float) -> float:
        """Calculate stackable volume weight (cbm × 330)"""
        return num_collo * (length / 100) * (width / 100) * (height / 100) * 330

    def calculate_loading_meter_weight(self, num_collo: int, length: float, width: float) -> float:
        """Calculate non-stackable loading meter weight (LDM × 1750)"""
        return ((width / 100) * (length / 100) / 2.4) * num_collo * 1750

    def determine_chargeable_weight(self, actual_weight: float, volume_weight: float,
                                    loading_meter_weight: float, height: float, weight_type: str = 'volume') -> tuple[
        float, str]:
        """Determine which weight to use for charging, optionally by specified type."""
        # Define available weight types
        weight_map = {
            'actual': actual_weight,
            'volume': volume_weight,
            'loading_meter': loading_meter_weight
        }

        # Return the weight based on the provided type
        if weight_type in weight_map:
            return weight_map[weight_type], weight_type

        # Force non-stackable if height > 120cm
        if height > 120:
            return loading_meter_weight, 'loading_meter'

        # Otherwise, return the maximum weight
        weights = [
            (actual_weight, 'actual'),
            (volume_weight, 'volume'),
            (loading_meter_weight, 'loading_meter')
        ]
        return max(weights, key=lambda x: x[0])

    def calculate_price(self, num_collo: int, length: float, width: float, height: float,
                        actual_weight: float, country: str, zipcode: str, service_level: str,
                        weight_type: str = 'volume') -> dict:
        """Calculate price based on dimensions and weight"""
        # Validate dimensions
        if length > 240 or width > 120 or height > 220:
            raise ValueError("Dimensions exceed maximum allowed values")

        if actual_weight > 1000:
            raise ValueError("Weight exceeds maximum allowed value of 1000 kg")

        # Calculate weights
        volume_weight = self.calculate_volume_weight(num_collo, length, width, height)
        loading_meter_weight = self.calculate_loading_meter_weight(num_collo, length, width)

        # Determine chargeable weight
        chargeable_weight, used_weight_type = self.determine_chargeable_weight(
            actual_weight, volume_weight, loading_meter_weight, height, weight_type
        )

        # Get zone and base rate
        zone = self.pricing_data.db.get_zone_for_zipcode(country, zipcode)
        base_rate = self.pricing_data.db.get_rate_for_shipment(
            weight=chargeable_weight,
            zone=zone,
            service_level=service_level,
            country=country
        )

        # Calculate extra fees sequentially
        extra_fees, fee_breakdown = self.calculate_sequential_fees(base_rate)

        return {
            "base_rate": base_rate,
            "extra_fees": extra_fees,
            "total_price": fee_breakdown['final_price'],
            "zone": zone,
            "stackable_weight": volume_weight,
            "non_stackable_weight": loading_meter_weight,
            "chargeable_weight": chargeable_weight,
            "weight_type": used_weight_type,
            "fee_breakdown": fee_breakdown
        }

    def get_zone(self, country: str, zipcode: str) -> str:
        """Helper method to get zone for a country and zipcode"""
        return self.pricing_data.db.get_zone_for_zipcode(country, zipcode)

    def calculate_sequential_fees(self, base_rate: float) -> tuple[float, dict]:
        """
        Calculate extra fees sequentially:
        1. Base Rate + NNR Premium
        2. Result + Unilog Premium
        3. Result + Fuel Surcharge
        Returns total extra fees and breakdown
        """
        # Get fee percentages from database
        db = self.pricing_data.db
        nnr_premium_pct = float(db.get_config('NNR_PREMIUM_FEES', '20.0'))
        unilog_premium_pct = float(db.get_config('UNILOG_PREMIUM_FEES', '35.0'))
        fuel_surcharge_pct = float(db.get_config('FUEL_SURCHARGE', '8.0'))

        # Calculate fees sequentially
        nnr_fee = base_rate * (nnr_premium_pct / 100)
        after_nnr = base_rate + nnr_fee

        unilog_fee = after_nnr * (unilog_premium_pct / 100)
        after_unilog = after_nnr + unilog_fee

        fuel_fee = after_unilog * (fuel_surcharge_pct / 100)
        final_price = after_unilog + fuel_fee

        total_extra_fees = final_price - base_rate

        # Prepare breakdown
        fee_breakdown = {
            'base_rate': base_rate,
            'nnr_premium': {
                'percentage': nnr_premium_pct,
                'amount': nnr_fee
            },
            'unilog_premium': {
                'percentage': unilog_premium_pct,
                'amount': unilog_fee
            },
            'fuel_surcharge': {
                'percentage': fuel_surcharge_pct,
                'amount': fuel_fee
            },
            'total_extra_fees': total_extra_fees,
            'final_price': final_price
        }

        return total_extra_fees, fee_breakdown