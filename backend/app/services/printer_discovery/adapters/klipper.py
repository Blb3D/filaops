"""
Klipper/Moonraker Printer Discovery Adapter

Supports:
- mDNS/Zeroconf discovery
- Direct HTTP API connection
- WebSocket status monitoring
"""

import asyncio
import logging
import socket
from typing import List, Optional, Dict, Any

from ..base import PrinterDiscoveryAdapter
from ..models import (
    DiscoveredPrinter,
    PrinterBrand,
    PrinterStatus,
    PrinterCapabilities,
    PrinterConnectionConfig,
    ConnectionType,
)

logger = logging.getLogger(__name__)


class KlipperAdapter(PrinterDiscoveryAdapter):
    """Discovery adapter for Klipper/Moonraker printers"""

    @property
    def brand_name(self) -> str:
        return "Klipper (Moonraker)"

    @property
    def brand_code(self) -> str:
        return "klipper"

    async def discover_local(self, timeout_seconds: float = 5.0) -> List[DiscoveredPrinter]:
        """
        Discover Klipper printers via mDNS.

        Moonraker advertises via mDNS as _moonraker._tcp
        """
        discovered = []

        try:
            # Try zeroconf if available
            from zeroconf import Zeroconf, ServiceBrowser  # noqa: F401

            class MoonrakerListener:
                def __init__(self):
                    self.found = []

                def add_service(self, zc, type_, name):
                    info = zc.get_service_info(type_, name)
                    if info:
                        self.found.append(
                            {
                                "name": name,
                                "addresses": [socket.inet_ntoa(addr) for addr in info.addresses],
                                "port": info.port,
                                "properties": {
                                    k.decode(): v.decode() if isinstance(v, bytes) else v
                                    for k, v in info.properties.items()
                                },
                            }
                        )

                def remove_service(self, zc, type_, name):
                    pass

                def update_service(self, zc, type_, name):
                    pass

            zc = Zeroconf()
            listener = MoonrakerListener()

            browser = ServiceBrowser(zc, "_moonraker._tcp.local.", listener)
            await asyncio.sleep(timeout_seconds)
            browser.cancel()
            zc.close()

            # Convert found services to DiscoveredPrinter
            for service in listener.found:
                ip = service["addresses"][0] if service["addresses"] else None
                if ip:
                    printer = DiscoveredPrinter(
                        brand=PrinterBrand.KLIPPER,
                        model="Klipper",
                        name=service["name"].replace("._moonraker._tcp.local.", ""),
                        connection_type=ConnectionType.LOCAL,
                        ip_address=ip,
                        connection_config=PrinterConnectionConfig(
                            ip_address=ip,
                            port=service["port"],
                        ),
                        discovered_via="mdns",
                        raw_data=service,
                    )
                    discovered.append(printer)
                    logger.info(f"Discovered Klipper printer: {printer.name} at {ip}")

        except ImportError:
            logger.info("zeroconf not installed - Klipper mDNS discovery disabled")
        except Exception as e:
            logger.error(f"Klipper mDNS discovery error: {e}")

        return discovered

    async def test_connection(self, config: PrinterConnectionConfig) -> tuple[bool, Optional[str]]:
        """Test connection to Moonraker API"""
        if not config.ip_address:
            return False, "IP address is required"

        port = config.port or 7125

        try:
            import aiohttp

            url = f"http://{config.ip_address}:{port}/server/info"
            headers = {}
            if config.api_key:
                headers["X-Api-Key"] = config.api_key

            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return True, None
                    elif response.status == 401:
                        return False, "API key required or invalid"
                    else:
                        return False, f"HTTP {response.status}"

        except ImportError:
            # Try basic socket test
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((config.ip_address, port))
                sock.close()
                return result == 0, None if result == 0 else "Connection refused"
            except Exception as e:
                return False, str(e)
        except Exception as e:
            return False, str(e)

    async def get_status(self, config: PrinterConnectionConfig) -> Optional[PrinterStatus]:
        """Get printer status from Moonraker API"""
        if not config.ip_address:
            return PrinterStatus.OFFLINE

        port = config.port or 7125

        try:
            import aiohttp

            url = f"http://{config.ip_address}:{port}/printer/objects/query?print_stats"
            headers = {}
            if config.api_key:
                headers["X-Api-Key"] = config.api_key

            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        state = data.get("result", {}).get("status", {}).get("print_stats", {}).get("state", "")

                        status_map = {
                            "standby": PrinterStatus.IDLE,
                            "printing": PrinterStatus.PRINTING,
                            "paused": PrinterStatus.PAUSED,
                            "complete": PrinterStatus.IDLE,
                            "cancelled": PrinterStatus.IDLE,
                            "error": PrinterStatus.ERROR,
                        }
                        return status_map.get(state, PrinterStatus.IDLE)
                    else:
                        return PrinterStatus.OFFLINE

        except Exception as e:
            logger.debug(f"Error getting Klipper status: {e}")
            return PrinterStatus.OFFLINE

    async def get_capabilities(self, config: PrinterConnectionConfig) -> Optional[PrinterCapabilities]:
        """Query Moonraker for printer capabilities"""
        if not config.ip_address:
            return None

        port = config.port or 7125

        try:
            import aiohttp

            url = f"http://{config.ip_address}:{port}/printer/objects/query?configfile"
            headers = {}
            if config.api_key:
                headers["X-Api-Key"] = config.api_key

            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        config_data = data.get("result", {}).get("status", {}).get("configfile", {}).get("settings", {})

                        # Extract stepper positions for bed size
                        stepper_x = config_data.get("stepper_x", {})
                        stepper_y = config_data.get("stepper_y", {})
                        stepper_z = config_data.get("stepper_z", {})

                        bed_width = stepper_x.get("position_max", 0) - stepper_x.get("position_min", 0)
                        bed_depth = stepper_y.get("position_max", 0) - stepper_y.get("position_min", 0)
                        bed_height = stepper_z.get("position_max", 0) - stepper_z.get("position_min", 0)

                        # Check for heated bed
                        has_heated_bed = "heater_bed" in config_data

                        # Check for extruder temp
                        extruder = config_data.get("extruder", {})
                        max_nozzle_temp = extruder.get("max_temp", 260)

                        return PrinterCapabilities(
                            bed_width=bed_width if bed_width > 0 else None,
                            bed_depth=bed_depth if bed_depth > 0 else None,
                            bed_height=bed_height if bed_height > 0 else None,
                            has_heated_bed=has_heated_bed,
                            max_nozzle_temp=int(max_nozzle_temp) if max_nozzle_temp else None,
                        )

        except Exception as e:
            logger.debug(f"Error getting Klipper capabilities: {e}")

        return None

    def get_connection_fields(self) -> List[Dict[str, Any]]:
        """Klipper/Moonraker-specific connection fields"""
        return [
            {
                "name": "ip_address",
                "label": "IP Address / Hostname",
                "type": "text",
                "required": True,
                "placeholder": "192.168.1.100 or mainsail.local",
            },
            {
                "name": "port",
                "label": "Moonraker Port",
                "type": "number",
                "required": False,
                "default": 7125,
                "help": "Usually 7125 (Moonraker default)",
            },
            {
                "name": "api_key",
                "label": "API Key",
                "type": "password",
                "required": False,
                "help": "Only if Moonraker is configured with authentication",
            },
        ]

    def get_supported_models(self) -> List[Dict[str, str]]:
        """Klipper supports many printer models"""
        return [
            {"value": "Voron 2.4", "label": "Voron 2.4"},
            {"value": "Voron Trident", "label": "Voron Trident"},
            {"value": "Voron 0", "label": "Voron 0"},
            {"value": "RatRig V-Core", "label": "RatRig V-Core"},
            {"value": "Ender 3 (Klipper)", "label": "Ender 3 (Klipper mod)"},
            {"value": "CR-10 (Klipper)", "label": "CR-10 (Klipper mod)"},
            {"value": "Custom CoreXY", "label": "Custom CoreXY"},
            {"value": "Custom Cartesian", "label": "Custom Cartesian"},
            {"value": "Other", "label": "Other"},
        ]
