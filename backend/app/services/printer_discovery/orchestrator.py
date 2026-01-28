"""
Printer Discovery Orchestrator

Coordinates discovery across all registered adapters.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional

from .base import PrinterDiscoveryAdapter
from .models import DiscoveredPrinter, PrinterConnectionConfig, PrinterStatus

logger = logging.getLogger(__name__)


class PrinterDiscoveryOrchestrator:
    """
    Orchestrates printer discovery across multiple brand adapters.

    Usage:
        orchestrator = PrinterDiscoveryOrchestrator()
        orchestrator.register_adapter(BambuLabAdapter())
        orchestrator.register_adapter(KlipperAdapter())

        # Discover all printers on network
        printers = await orchestrator.discover_all()

        # Discover specific brand only
        bambu_printers = await orchestrator.discover_brand("bambulab")
    """

    def __init__(self):
        self._adapters: Dict[str, PrinterDiscoveryAdapter] = {}

    @property
    def adapters(self) -> Dict[str, PrinterDiscoveryAdapter]:
        """Public accessor for registered adapters"""
        return self._adapters

    def register_adapter(self, adapter: PrinterDiscoveryAdapter) -> None:
        """Register a discovery adapter for a brand"""
        self._adapters[adapter.brand_code] = adapter
        logger.info(f"Registered printer adapter: {adapter.brand_name}")

    def get_adapter(self, brand_code: str) -> Optional[PrinterDiscoveryAdapter]:
        """Get adapter for a specific brand"""
        return self._adapters.get(brand_code)

    def get_registered_brands(self) -> List[Dict[str, str]]:
        """Get list of registered brands with their display names"""
        return [{"code": adapter.brand_code, "name": adapter.brand_name} for adapter in self._adapters.values()]

    async def discover_all(
        self,
        timeout_seconds: float = 5.0,
        include_cloud: bool = False,
        cloud_credentials: Optional[Dict[str, Dict[str, Any]]] = None,
        brand_filter: Optional[List[str]] = None,
    ) -> List[DiscoveredPrinter]:
        """
        Discover printers from all registered adapters.

        Args:
            timeout_seconds: Timeout for each adapter's discovery
            include_cloud: Whether to also check cloud APIs
            cloud_credentials: Dict of brand_code -> credentials
            brand_filter: Optional list of brand codes to scan (None = all)

        Returns:
            Combined list of all discovered printers
        """
        cloud_credentials = cloud_credentials or {}
        tasks = []

        for brand_code, adapter in self._adapters.items():
            # Skip if brand filter specified and this brand not in it
            if brand_filter and brand_code not in brand_filter:
                continue

            # Local discovery
            tasks.append(self._safe_discover_local(adapter, timeout_seconds))

            # Cloud discovery (if requested and credentials provided)
            if include_cloud and brand_code in cloud_credentials:
                tasks.append(self._safe_discover_cloud(adapter, cloud_credentials[brand_code]))

        results = await asyncio.gather(*tasks)

        # Flatten results and deduplicate by serial number
        all_printers = []
        seen_serials = set()

        for printer_list in results:
            for printer in printer_list:
                # Dedupe by serial if available
                if printer.serial_number:
                    if printer.serial_number in seen_serials:
                        continue
                    seen_serials.add(printer.serial_number)
                all_printers.append(printer)

        logger.info(f"Discovery complete: found {len(all_printers)} printers")
        return all_printers

    async def discover_brand(self, brand_code: str, timeout_seconds: float = 5.0) -> List[DiscoveredPrinter]:
        """Discover printers for a specific brand only"""
        adapter = self._adapters.get(brand_code)
        if not adapter:
            logger.warning(f"No adapter registered for brand: {brand_code}")
            return []

        return await self._safe_discover_local(adapter, timeout_seconds)

    async def test_connection(self, brand_code: str, config: PrinterConnectionConfig) -> tuple[bool, Optional[str]]:
        """
        Test connection to a printer.

        Args:
            brand_code: The printer's brand
            config: Connection configuration to test

        Returns:
            Tuple of (success, error_message)
        """
        adapter = self._adapters.get(brand_code)
        if not adapter:
            return False, f"No adapter for brand: {brand_code}"

        try:
            return await adapter.test_connection(config)
        except Exception as e:
            logger.exception(f"Error testing connection for {brand_code}")
            return False, str(e)

    async def get_status(self, brand_code: str, config: PrinterConnectionConfig) -> Optional[PrinterStatus]:
        """Get current status of a printer"""
        adapter = self._adapters.get(brand_code)
        if not adapter:
            return None

        try:
            return await adapter.get_status(config)
        except Exception:
            logger.exception(f"Error getting status for {brand_code}")
            return None

    def get_connection_fields(self, brand_code: str) -> List[Dict[str, Any]]:
        """Get form fields for a brand's connection config"""
        adapter = self._adapters.get(brand_code)
        if not adapter:
            return []
        return adapter.get_connection_fields()

    def get_supported_models(self, brand_code: str) -> List[Dict[str, str]]:
        """Get supported models for a brand"""
        adapter = self._adapters.get(brand_code)
        if not adapter:
            return []
        return adapter.get_supported_models()

    async def _safe_discover_local(
        self, adapter: PrinterDiscoveryAdapter, timeout_seconds: float
    ) -> List[DiscoveredPrinter]:
        """Safely run local discovery with error handling"""
        try:
            return await adapter.discover_local(timeout_seconds)
        except Exception:
            logger.exception(f"Error during {adapter.brand_name} local discovery")
            return []

    async def _safe_discover_cloud(
        self, adapter: PrinterDiscoveryAdapter, credentials: Dict[str, Any]
    ) -> List[DiscoveredPrinter]:
        """Safely run cloud discovery with error handling"""
        try:
            return await adapter.discover_cloud(credentials)
        except Exception:
            logger.exception(f"Error during {adapter.brand_name} cloud discovery")
            return []


# Global orchestrator instance
_orchestrator: Optional[PrinterDiscoveryOrchestrator] = None


def get_orchestrator() -> PrinterDiscoveryOrchestrator:
    """Get or create the global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = PrinterDiscoveryOrchestrator()
        # Register default adapters
        _register_default_adapters(_orchestrator)
    return _orchestrator


def _register_default_adapters(orchestrator: PrinterDiscoveryOrchestrator) -> None:
    """Register all available adapters"""
    # Import adapters here to avoid circular imports
    from .adapters.bambulab import BambuLabAdapter
    from .adapters.klipper import KlipperAdapter
    from .adapters.generic import GenericAdapter

    orchestrator.register_adapter(BambuLabAdapter())
    orchestrator.register_adapter(KlipperAdapter())
    orchestrator.register_adapter(GenericAdapter())
