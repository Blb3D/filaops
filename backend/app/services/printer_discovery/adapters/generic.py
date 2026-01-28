"""
Generic Printer Adapter

For printers without specific API support.
Provides manual entry and basic connectivity testing.
"""

import logging
import socket
from typing import List, Optional, Dict, Any

from ..base import PrinterDiscoveryAdapter
from ..models import (
    DiscoveredPrinter,
    PrinterStatus,
    PrinterConnectionConfig,
)

logger = logging.getLogger(__name__)


class GenericAdapter(PrinterDiscoveryAdapter):
    """
    Generic adapter for printers without specific API support.

    This adapter:
    - Does not support network discovery
    - Provides manual entry only
    - Tests connectivity via ping/port check
    """

    @property
    def brand_name(self) -> str:
        return "Other / Generic"

    @property
    def brand_code(self) -> str:
        return "generic"

    async def discover_local(self, timeout_seconds: float = 5.0) -> List[DiscoveredPrinter]:
        """Generic adapter doesn't support auto-discovery"""
        return []

    async def test_connection(self, config: PrinterConnectionConfig) -> tuple[bool, Optional[str]]:
        """Test if printer is reachable via ping or port check"""
        if not config.ip_address:
            return True, None  # No IP = manual tracking only, always "ok"

        # Try to ping or check common ports
        common_ports = [80, 443, 8080, 7125, 8883]

        for port in common_ports:
            if await self._check_port(config.ip_address, port):
                return True, None

        # Try ICMP ping as fallback
        if await self._ping(config.ip_address):
            return True, None

        return False, "Printer not reachable (no open ports found)"

    async def _check_port(self, ip: str, port: int) -> bool:
        """Check if a port is open"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    async def _ping(self, ip: str) -> bool:
        """Simple ping check"""
        try:
            import subprocess
            import platform

            # Windows vs Unix ping command
            param = "-n" if platform.system().lower() == "windows" else "-c"
            command = ["ping", param, "1", "-w", "1000", ip]

            result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
            return result.returncode == 0
        except Exception:
            return False

    async def get_status(self, config: PrinterConnectionConfig) -> Optional[PrinterStatus]:
        """
        Generic status check.

        Since we can't query the printer, we just check if it's reachable.
        """
        if not config.ip_address:
            return PrinterStatus.OFFLINE

        success, _ = await self.test_connection(config)
        return PrinterStatus.IDLE if success else PrinterStatus.OFFLINE

    def get_connection_fields(self) -> List[Dict[str, Any]]:
        """Generic connection fields - minimal requirements"""
        return [
            {
                "name": "ip_address",
                "label": "IP Address (optional)",
                "type": "text",
                "required": False,
                "placeholder": "192.168.1.100",
                "help": "Optional - for network status checks",
            },
        ]

    def get_supported_models(self) -> List[Dict[str, str]]:
        """Common generic printer models"""
        return [
            {"value": "Ender 3", "label": "Creality Ender 3"},
            {"value": "Ender 3 Pro", "label": "Creality Ender 3 Pro"},
            {"value": "Ender 3 V2", "label": "Creality Ender 3 V2"},
            {"value": "CR-10", "label": "Creality CR-10"},
            {"value": "Anycubic Kobra", "label": "Anycubic Kobra"},
            {"value": "Artillery Sidewinder", "label": "Artillery Sidewinder"},
            {"value": "Elegoo Neptune", "label": "Elegoo Neptune"},
            {"value": "Custom", "label": "Custom / DIY"},
            {"value": "Other", "label": "Other"},
        ]
