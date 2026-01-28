"""
Printer Discovery Models

Data models for discovered printers and their capabilities.
"""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class PrinterBrand(str, Enum):
    """Supported printer brands"""

    BAMBULAB = "bambulab"
    KLIPPER = "klipper"
    OCTOPRINT = "octoprint"
    PRUSA = "prusa"
    CREALITY = "creality"
    GENERIC = "generic"


class PrinterStatus(str, Enum):
    """Printer operational status"""

    OFFLINE = "offline"
    IDLE = "idle"
    PRINTING = "printing"
    PAUSED = "paused"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class ConnectionType(str, Enum):
    """How we connect to the printer"""

    LOCAL = "local"  # Direct IP/network connection
    CLOUD = "cloud"  # Via manufacturer's cloud API
    BOTH = "both"  # Supports both local and cloud


class PrinterCapabilities(BaseModel):
    """Printer hardware capabilities"""

    # Build volume (mm)
    bed_width: Optional[float] = None
    bed_depth: Optional[float] = None
    bed_height: Optional[float] = None

    # Features
    has_enclosure: bool = False
    has_heated_bed: bool = True
    has_heated_chamber: bool = False

    # Multi-material
    has_ams: bool = False  # BambuLab AMS
    has_mmu: bool = False  # Prusa MMU
    filament_count: int = 1  # Number of filaments (1, 4, etc.)

    # Camera
    has_camera: bool = False
    has_lidar: bool = False

    # Max temperatures
    max_nozzle_temp: Optional[int] = None
    max_bed_temp: Optional[int] = None

    # Nozzle
    nozzle_diameter: float = 0.4


class PrinterConnectionConfig(BaseModel):
    """Connection configuration for a printer"""

    # Network
    ip_address: Optional[str] = None
    port: Optional[int] = None

    # Authentication
    access_code: Optional[str] = None  # BambuLab access code
    api_key: Optional[str] = None  # OctoPrint/Klipper API key

    # Cloud credentials (stored separately, referenced by ID)
    cloud_account_id: Optional[int] = None

    # MQTT (for BambuLab)
    mqtt_topic: Optional[str] = None

    # Serial connection (for some printers)
    serial_port: Optional[str] = None
    baud_rate: Optional[int] = None


class DiscoveredPrinter(BaseModel):
    """
    A printer discovered on the network or via cloud API.

    This is the unified representation before being saved to the database.
    """

    # Identification
    brand: PrinterBrand
    model: str
    name: str
    serial_number: Optional[str] = None

    # Connection info
    connection_type: ConnectionType = ConnectionType.LOCAL
    ip_address: Optional[str] = None

    # Capabilities (auto-detected or from known models)
    capabilities: PrinterCapabilities = Field(default_factory=PrinterCapabilities)

    # Connection config
    connection_config: PrinterConnectionConfig = Field(default_factory=PrinterConnectionConfig)

    # Discovery metadata
    discovered_via: str = "manual"  # "ssdp", "mdns", "cloud", "manual"
    firmware_version: Optional[str] = None

    # Brand-specific raw data (for debugging/advanced features)
    raw_data: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


# Known printer models with their capabilities
KNOWN_PRINTER_MODELS: Dict[str, Dict[str, Any]] = {
    # BambuLab
    "bambulab:X1C": {
        "brand": PrinterBrand.BAMBULAB,
        "model": "X1 Carbon",
        "capabilities": PrinterCapabilities(
            bed_width=256,
            bed_depth=256,
            bed_height=256,
            has_enclosure=True,
            has_heated_chamber=True,
            has_ams=True,
            filament_count=4,
            has_camera=True,
            has_lidar=True,
            max_nozzle_temp=300,
            max_bed_temp=110,
        ),
    },
    "bambulab:X1": {
        "brand": PrinterBrand.BAMBULAB,
        "model": "X1",
        "capabilities": PrinterCapabilities(
            bed_width=256,
            bed_depth=256,
            bed_height=256,
            has_enclosure=True,
            has_heated_chamber=True,
            has_ams=True,
            filament_count=4,
            has_camera=True,
            has_lidar=True,
            max_nozzle_temp=300,
            max_bed_temp=110,
        ),
    },
    "bambulab:P1S": {
        "brand": PrinterBrand.BAMBULAB,
        "model": "P1S",
        "capabilities": PrinterCapabilities(
            bed_width=256,
            bed_depth=256,
            bed_height=256,
            has_enclosure=True,
            has_heated_chamber=False,
            has_ams=True,
            filament_count=4,
            has_camera=True,
            has_lidar=False,
            max_nozzle_temp=300,
            max_bed_temp=110,
        ),
    },
    "bambulab:P1P": {
        "brand": PrinterBrand.BAMBULAB,
        "model": "P1P",
        "capabilities": PrinterCapabilities(
            bed_width=256,
            bed_depth=256,
            bed_height=256,
            has_enclosure=False,
            has_heated_chamber=False,
            has_ams=True,
            filament_count=4,
            has_camera=True,
            has_lidar=False,
            max_nozzle_temp=300,
            max_bed_temp=110,
        ),
    },
    "bambulab:A1": {
        "brand": PrinterBrand.BAMBULAB,
        "model": "A1",
        "capabilities": PrinterCapabilities(
            bed_width=256,
            bed_depth=256,
            bed_height=256,
            has_enclosure=False,
            has_heated_chamber=False,
            has_ams=True,
            filament_count=4,
            has_camera=True,
            has_lidar=False,
            max_nozzle_temp=300,
            max_bed_temp=100,
        ),
    },
    "bambulab:A1 Mini": {
        "brand": PrinterBrand.BAMBULAB,
        "model": "A1 Mini",
        "capabilities": PrinterCapabilities(
            bed_width=180,
            bed_depth=180,
            bed_height=180,
            has_enclosure=False,
            has_heated_chamber=False,
            has_ams=True,
            filament_count=4,
            has_camera=True,
            has_lidar=False,
            max_nozzle_temp=300,
            max_bed_temp=80,
        ),
    },
    # Prusa
    "prusa:MK4": {
        "brand": PrinterBrand.PRUSA,
        "model": "MK4",
        "capabilities": PrinterCapabilities(
            bed_width=250,
            bed_depth=210,
            bed_height=220,
            has_enclosure=False,
            has_mmu=True,
            filament_count=5,
            has_camera=False,
            max_nozzle_temp=290,
            max_bed_temp=120,
        ),
    },
    "prusa:MK3S+": {
        "brand": PrinterBrand.PRUSA,
        "model": "MK3S+",
        "capabilities": PrinterCapabilities(
            bed_width=250,
            bed_depth=210,
            bed_height=210,
            has_enclosure=False,
            has_mmu=True,
            filament_count=5,
            has_camera=False,
            max_nozzle_temp=280,
            max_bed_temp=100,
        ),
    },
    "prusa:XL": {
        "brand": PrinterBrand.PRUSA,
        "model": "XL",
        "capabilities": PrinterCapabilities(
            bed_width=360,
            bed_depth=360,
            bed_height=360,
            has_enclosure=True,
            filament_count=5,  # Tool changer
            has_camera=False,
            max_nozzle_temp=290,
            max_bed_temp=120,
        ),
    },
    # Creality
    "creality:Ender 3 V3": {
        "brand": PrinterBrand.CREALITY,
        "model": "Ender 3 V3",
        "capabilities": PrinterCapabilities(
            bed_width=220,
            bed_depth=220,
            bed_height=250,
            has_enclosure=False,
            max_nozzle_temp=260,
            max_bed_temp=100,
        ),
    },
    "creality:K1": {
        "brand": PrinterBrand.CREALITY,
        "model": "K1",
        "capabilities": PrinterCapabilities(
            bed_width=220,
            bed_depth=220,
            bed_height=250,
            has_enclosure=True,
            has_camera=True,
            max_nozzle_temp=300,
            max_bed_temp=100,
        ),
    },
    "creality:K1 Max": {
        "brand": PrinterBrand.CREALITY,
        "model": "K1 Max",
        "capabilities": PrinterCapabilities(
            bed_width=300,
            bed_depth=300,
            bed_height=300,
            has_enclosure=True,
            has_camera=True,
            has_lidar=True,
            max_nozzle_temp=300,
            max_bed_temp=100,
        ),
    },
}


def get_model_capabilities(brand: str, model: str) -> Optional[PrinterCapabilities]:
    """Look up known capabilities for a printer model"""
    key = f"{brand}:{model}"
    if key in KNOWN_PRINTER_MODELS:
        return KNOWN_PRINTER_MODELS[key]["capabilities"]
    return None
