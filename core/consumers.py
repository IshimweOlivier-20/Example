"""
WebSocket consumers for real-time tracking.
"""
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class TrackingConsumer(AsyncJsonWebsocketConsumer):
    """
    Live shipment tracking over WebSocket.

    Access: Customer, assigned driver, admin, or government official.
    """

    async def connect(self):
        self.tracking_code = self.scope['url_route']['kwargs'].get('tracking_code')
        user = self.scope.get('user')

        if not user or user.is_anonymous:
            await self.close()
            return

        shipment = await self._get_shipment(self.tracking_code)
        if not shipment or not self._is_authorized(user, shipment):
            await self.close()
            return

        self.shipment_id = shipment.id
        self.shipment_type = shipment.__class__.__name__
        await self.accept()
        await self.send_json(self._build_payload(shipment))

    async def receive_json(self, content, **kwargs):
        """Handle client ping to fetch latest tracking payload."""
        if content.get('type') != 'ping':
            return

        shipment = await self._get_shipment_by_id()
        if shipment:
            await self.send_json(self._build_payload(shipment))

    async def disconnect(self, close_code):
        return

    @database_sync_to_async
    def _get_shipment(self, tracking_code):
        from domestic.models import DomesticShipment
        from international.models import InternationalShipment

        try:
            return DomesticShipment.objects.select_related('driver', 'customer').get(
                tracking_number=tracking_code
            )
        except DomesticShipment.DoesNotExist:
            try:
                return InternationalShipment.objects.select_related('driver', 'customer').get(
                    tracking_number=tracking_code
                )
            except InternationalShipment.DoesNotExist:
                return None

    @database_sync_to_async
    def _get_shipment_by_id(self):
        from domestic.models import DomesticShipment
        from international.models import InternationalShipment

        if self.shipment_type == 'DomesticShipment':
            return DomesticShipment.objects.select_related('driver', 'customer').get(id=self.shipment_id)
        return InternationalShipment.objects.select_related('driver', 'customer').get(id=self.shipment_id)

    def _is_authorized(self, user, shipment) -> bool:
        if user == shipment.customer or user == shipment.driver:
            return True
        return user.user_type in ['ADMIN', 'GOV_OFFICIAL']

    def _build_payload(self, shipment) -> dict:
        return {
            'tracking_number': shipment.tracking_number,
            'status': shipment.status,
            'origin': shipment.origin,
            'destination': shipment.destination,
            'current_location': {
                'latitude': -1.9536,
                'longitude': 30.0606,
                'address': 'Kigali, Rwanda',
                'last_updated': timezone.now().isoformat()
            },
            'driver': {
                'name': shipment.driver.full_name if shipment.driver else None,
                'phone': shipment.driver.phone if shipment.driver else None
            } if shipment.driver else None,
        }
