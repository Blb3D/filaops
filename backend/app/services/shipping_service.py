"""
Shipping Service - FilaOps Open Source

Manual shipping management. For automated carrier integration
(EasyPost, Shippo), see FilaOps Pro.
"""

from typing import Optional
from pydantic import BaseModel


class ShipmentInfo(BaseModel):
    """Basic shipment information for manual entry"""

    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    service: Optional[str] = None


class ShippingService:
    """
    Basic shipping service for manual tracking.

    FilaOps Pro adds:
    - EasyPost/Shippo integration
    - Rate shopping across carriers
    - Automatic label generation
    """

    async def create_shipment(
        self, tracking_number: str, carrier: str = "Manual", service: str = "Standard"
    ) -> ShipmentInfo:
        """Record a manual shipment"""
        return ShipmentInfo(tracking_number=tracking_number, carrier=carrier, service=service)

    async def get_rates(self, *args, **kwargs):
        """Rate shopping requires FilaOps Pro"""
        raise NotImplementedError(
            "Carrier rate shopping requires FilaOps Pro. " "Use manual tracking number entry instead."
        )

    async def buy_label(self, *args, **kwargs):
        """Label printing requires FilaOps Pro"""
        raise NotImplementedError(
            "Automatic label printing requires FilaOps Pro. " "Use manual tracking number entry instead."
        )


shipping_service = ShippingService()
