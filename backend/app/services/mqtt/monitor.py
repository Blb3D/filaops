"""
Printer Monitor Service

Manages MQTT connections for the entire printer fleet.
Handles:
- Loading printers from database
- Managing connections (connect/disconnect/reconnect)
- Aggregating status for bulk queries (Otto needs this)
- Periodic database flush
- Event routing
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from sqlalchemy.orm.attributes import flag_modified

from app.db.session import SessionLocal
from app.models import Printer
from app.core.settings import get_settings
from .client import BambuMQTTClient
from .events import EventQueue, TelemetryEvent, EventType

logger = logging.getLogger(__name__)


class PrinterMonitorService:
    """
    Central service for monitoring all printers via MQTT.

    Lifecycle:
    1. start() - Load printers from DB, connect all with MQTT credentials
    2. Running - Receive events, maintain cache, flush to DB periodically
    3. stop() - Disconnect all, final flush
    """

    def __init__(self):
        self._clients: Dict[int, BambuMQTTClient] = {}
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None
        self._event_queue = EventQueue(max_events=1000)
        self._production_order_map: Dict[int, int] = {}  # printer_id -> current PO ID

    async def start(self):
        """Start the monitor service."""
        if self._running:
            logger.warning("PrinterMonitorService already running")
            return

        logger.info("Starting PrinterMonitorService...")
        self._running = True

        # Load and connect printers
        await self._load_printers()

        # Start periodic DB flush
        self._flush_task = asyncio.create_task(self._periodic_flush())

        logger.info(f"PrinterMonitorService started with {len(self._clients)} printers")

    async def stop(self):
        """Stop the monitor service."""
        if not self._running:
            return

        logger.info("Stopping PrinterMonitorService...")
        self._running = False

        # Cancel flush task
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Final flush before disconnect
        await self._flush_to_database()

        # Disconnect all printers
        for printer_id, client in self._clients.items():
            client.disconnect()

        self._clients.clear()
        logger.info("PrinterMonitorService stopped")

    async def _load_printers(self):
        """Load printers from database and connect those with MQTT credentials."""
        db = SessionLocal()
        try:
            printers = db.query(Printer).filter(
                Printer.active.is_(True),
                Printer.brand == "bambulab"  # Only Bambu printers have MQTT
            ).all()

            for printer in printers:
                await self._connect_printer(printer)
        finally:
            db.close()

    async def _connect_printer(self, printer: Printer) -> bool:
        """Connect to a single printer if it has MQTT credentials."""
        config = printer.connection_config or {}

        # Check for required MQTT credentials
        # Priority: connection_config JSON > printer model columns
        host = config.get("mqtt_host") or config.get("ip_address") or printer.ip_address
        serial = config.get("mqtt_serial") or config.get("serial") or printer.serial_number
        access_code = config.get("mqtt_access_code") or config.get("access_code")

        if not all([host, serial, access_code]):
            logger.debug(f"Printer {printer.id} ({printer.name}) missing MQTT credentials, skipping")
            return False

        # Create client
        client = BambuMQTTClient(
            printer_id=printer.id,
            host=host,
            serial=serial,
            access_code=access_code,
            on_event=self._handle_event
        )

        # Connect
        if client.connect():
            self._clients[printer.id] = client
            logger.info(f"Connected to printer {printer.id} ({printer.name})")
            return True
        else:
            logger.error(f"Failed to connect to printer {printer.id} ({printer.name})")
            return False

    def _handle_event(self, event_data: Dict[str, Any]):
        """Handle an event from a printer."""
        try:
            event_type = EventType(event_data.get("type", "unknown"))
        except ValueError:
            event_type = EventType.PRINTER_ERROR

        # Check if this printer has an active production order
        printer_id = event_data.get("printer_id")
        po_id = self._production_order_map.get(printer_id)

        event = TelemetryEvent(
            event_type=event_type,
            printer_id=printer_id,
            timestamp=datetime.now(timezone.utc),
            data=event_data,
            production_order_id=po_id
        )

        self._event_queue.push(event)
        logger.info(f"Event: {event_type.value} from printer {printer_id}")

    # ==========================================================================
    # Status Queries (for API endpoints)
    # ==========================================================================

    def get_printer_status(self, printer_id: int) -> Optional[Dict[str, Any]]:
        """Get cached status for a single printer."""
        client = self._clients.get(printer_id)
        if client:
            status = client.get_cached_status()
            status["production_order_id"] = self._production_order_map.get(printer_id)
            return status
        return None

    def get_all_printer_status(self) -> Dict[int, Dict[str, Any]]:
        """
        Get cached status for ALL printers.

        This is the bulk endpoint Otto needs - one call for entire fleet.
        """
        result = {}
        for printer_id, client in self._clients.items():
            status = client.get_cached_status()
            status["production_order_id"] = self._production_order_map.get(printer_id)
            result[printer_id] = status
        return result

    def get_connected_count(self) -> int:
        """Get count of connected printers."""
        return sum(1 for c in self._clients.values() if c.is_connected())

    def get_service_status(self) -> Dict[str, Any]:
        """Get overall service status."""
        return {
            "running": self._running,
            "total_printers": len(self._clients),
            "connected_printers": self.get_connected_count(),
            "event_queue_size": len(self._event_queue),
        }

    # ==========================================================================
    # Event Queries (for AI workers)
    # ==========================================================================

    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """Get recent events across all printers."""
        return self._event_queue.get_recent(limit)

    def get_events_since(self, since_id: int, limit: int = 100) -> List[Dict]:
        """Get events since a given ID (for polling)."""
        return self._event_queue.get_since(since_id, limit)

    def get_events_by_type(self, event_type: EventType, limit: int = 50) -> List[Dict]:
        """Get events of a specific type."""
        return self._event_queue.get_by_type(event_type, limit)

    # ==========================================================================
    # Production Order Linking
    # ==========================================================================

    def link_production_order(self, printer_id: int, production_order_id: int):
        """
        Link a production order to a printer.

        Call this when a PO is started on a printer.
        Events will then include the PO ID for correlation.
        """
        self._production_order_map[printer_id] = production_order_id
        logger.info(f"Linked printer {printer_id} to PO {production_order_id}")

    def unlink_production_order(self, printer_id: int):
        """Unlink production order when print completes or is cancelled."""
        if printer_id in self._production_order_map:
            del self._production_order_map[printer_id]

    def get_printer_production_order(self, printer_id: int) -> Optional[int]:
        """Get the production order currently running on a printer."""
        return self._production_order_map.get(printer_id)

    # ==========================================================================
    # Database Sync
    # ==========================================================================

    async def _periodic_flush(self):
        """Periodically flush status to database."""
        settings = get_settings()
        interval = getattr(settings, 'MQTT_DB_FLUSH_INTERVAL', 15)
        while self._running:
            await asyncio.sleep(interval)
            await self._flush_to_database()

    async def _flush_to_database(self):
        """Batch update all printer statuses to database."""
        if not self._clients:
            return

        db = SessionLocal()
        try:
            for printer_id, client in self._clients.items():
                status = client.get_cached_status()
                printer = db.query(Printer).get(printer_id)

                if printer and status:
                    # Update basic status
                    gcode_state = status.get("gcode_state", "unknown")
                    printer.status = self._map_gcode_state(gcode_state)
                    printer.last_seen = datetime.now(timezone.utc)

                    # Store full telemetry in connection_config
                    config = printer.connection_config or {}
                    config["last_telemetry"] = status
                    config["last_telemetry_time"] = datetime.now(timezone.utc).isoformat()
                    printer.connection_config = config
                    flag_modified(printer, "connection_config")

            db.commit()
            logger.debug(f"Flushed status for {len(self._clients)} printers to database")
        except Exception as e:
            logger.error(f"Error flushing to database: {e}")
            db.rollback()
        finally:
            db.close()

    def _map_gcode_state(self, gcode_state: str) -> str:
        """Map Bambu gcode_state to FilaOps printer status."""
        if not gcode_state:
            return "unknown"
        mapping = {
            "IDLE": "idle",
            "READY": "idle",
            "RUNNING": "printing",
            "PAUSE": "paused",
            "FINISH": "idle",
            "FAILED": "error",
            "OFFLINE": "offline",
            "UNKNOWN": "unknown",
        }
        return mapping.get(gcode_state.upper(), "unknown")

    # ==========================================================================
    # Manual Controls
    # ==========================================================================

    async def reconnect_printer(self, printer_id: int) -> bool:
        """Manually reconnect a printer."""
        # Disconnect if connected
        if printer_id in self._clients:
            self._clients[printer_id].disconnect()
            del self._clients[printer_id]

        # Reload from database and reconnect
        db = SessionLocal()
        try:
            printer = db.query(Printer).get(printer_id)
            if printer:
                return await self._connect_printer(printer)
        finally:
            db.close()
        return False

    async def add_printer(self, printer_id: int) -> bool:
        """Add and connect a new printer (called after printer created in admin)."""
        db = SessionLocal()
        try:
            printer = db.query(Printer).get(printer_id)
            if printer:
                return await self._connect_printer(printer)
        finally:
            db.close()
        return False
