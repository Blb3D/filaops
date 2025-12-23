# backend/app/core/settings.py
"""
FilaOps ERP - Configuration Management with pydantic-settings

- Loads from environment and root .env
- Validates and normalizes values
- Cached singleton via get_settings()
"""
import json
from functools import lru_cache
from pathlib import Path
from typing import Optional, List, Dict, Any
from decimal import Decimal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Calculate path to .env in project root (4 levels up from this file)
# backend/app/core/settings.py -> <repo>/.env
_ENV_FILE = Path(__file__).resolve().parent.parent.parent.parent / ".env"


class Settings(BaseSettings):
    """
    Application settings with validation.

    Environment variables take precedence over .env file values.
    Prefix FILAOPS_ can be used for any setting (e.g., FILAOPS_DEBUG=true).
    """

    # -------------------------------------------------
    # Pydantic Settings (v2) — must be *inside* class
    # -------------------------------------------------
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===================
    # Application Settings
    # ===================
    PROJECT_NAME: str = "FilaOps"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    ENVIRONMENT: str = Field(default="development", description="Deployment environment")

    # ===================
    # Database Settings
    # ===================
    DB_HOST: str = Field(default="localhost", description="PostgreSQL host")
    DB_PORT: int = Field(default=5432, description="PostgreSQL port")
    DB_NAME: str = Field(default="filaops", description="Database name")
    DB_USER: str = Field(default="postgres", description="Database user")
    DB_PASSWORD: str = Field(default="postgres", description="Database password")
    DATABASE_URL: Optional[str] = Field(
        default=None, description="Full database URL (overrides DB_* settings)"
    )

    @property
    def database_url(self) -> str:
        """Build PostgreSQL database URL from components or use explicit URL."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # ===================
    # Security Settings
    # ===================
    SECRET_KEY: str = Field(
        default="change-this-to-a-random-secret-key-in-production",
        description="JWT signing key - MUST change in production",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, description="JWT token expiration in minutes"
    )
    API_KEY: Optional[str] = Field(default=None, description="API key for integrations")

    @field_validator("SECRET_KEY")
    @classmethod
    def warn_default_secret(cls, v: str) -> str:
        """Fail in prod if default secret; warn in dev."""
        if "change-this" in v.lower():
            import warnings
            import os

            if os.getenv("ENVIRONMENT", "development").lower() == "production":
                raise ValueError(
                    "Default SECRET_KEY detected in production. Set a secure SECRET_KEY."
                )
            warnings.warn(
                "WARNING: Using default SECRET_KEY. Do not use this in production.",
                UserWarning,
                stacklevel=2,
            )
        return v

    # ===================
    # CORS Settings
    # ===================
    ALLOWED_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8001",
            "http://127.0.0.1:8001",
        ],
        description="Allowed CORS origins",
    )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    FRONTEND_URL: str = Field(
        default="http://localhost:5173", description="Frontend URL for redirects"
    )

    @model_validator(mode="after")
    def add_frontend_url_to_cors(self):
        """Ensure FRONTEND_URL is allowed for CORS."""
        if self.FRONTEND_URL and self.FRONTEND_URL not in self.ALLOWED_ORIGINS:
            self.ALLOWED_ORIGINS = list(self.ALLOWED_ORIGINS) + [self.FRONTEND_URL]
        return self

    # ==============================
    # Optional Google Drive switch
    # ==============================
    ENABLE_GOOGLE_DRIVE: bool = Field(
        default=False, validation_alias="ENABLE_GOOGLE_DRIVE"
    )

    # ===================
    # Bambu Print Suite
    # ===================
    BAMBU_SUITE_API_URL: str = Field(
        default="http://localhost:8001", description="Bambu Print Suite API URL"
    )
    BAMBU_SUITE_API_KEY: Optional[str] = Field(default=None, description="API key")

    # ===================
    # File Storage
    # ===================
    UPLOAD_DIR: str = Field(default="./uploads/quotes", description="Upload dir")
    MAX_FILE_SIZE_MB: int = Field(default=100, description="Max upload size (MB)")
    ALLOWED_FILE_FORMATS: List[str] = Field(
        default=[".3mf", ".stl"], description="Allowed upload extensions"
    )

    @field_validator("ALLOWED_FILE_FORMATS", mode="before")
    @classmethod
    def parse_file_formats(cls, v):
        if isinstance(v, str):
            return [fmt.strip() for fmt in v.split(",") if fmt.strip()]
        return v

    # ===================
    # Google Cloud Storage
    # ===================
    GCS_ENABLED: bool = Field(default=False, description="Enable GCS backup")
    GCS_BUCKET_NAME: str = Field(default="filaops-quote-files", description="Bucket")
    GCS_PROJECT_ID: Optional[str] = Field(default=None)
    GCS_CREDENTIALS_PATH: Optional[str] = Field(default=None)

    # ===================
    # Google Drive (legacy fields; optional)
    # ===================
    GDRIVE_ENABLED: bool = Field(default=False, description="Enable Google Drive")
    GDRIVE_CREDENTIALS_PATH: Optional[str] = Field(default=None)
    GDRIVE_FOLDER_ID: Optional[str] = Field(default=None)

    # ===================
    # Stripe
    # ===================
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None

    # ===================
    # EasyPost
    # ===================
    EASYPOST_API_KEY: Optional[str] = None
    EASYPOST_TEST_MODE: bool = True

    # ===================
    # Email (SMTP)
    # ===================
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "noreply@example.com"
    SMTP_FROM_NAME: str = "Your Company Name"
    SMTP_TLS: bool = True

    # ===================
    # Admin & Business
    # ===================
    ADMIN_APPROVAL_EMAIL: str = "admin@example.com"
    BUSINESS_EMAIL: str = "info@yourcompany.com"
    BUSINESS_NAME: str = "Your Company Name"

    # ===================
    # Ship From Address
    # ===================
    SHIP_FROM_NAME: str = "Your Company Name"
    SHIP_FROM_STREET1: str = "123 Main Street"
    SHIP_FROM_STREET2: Optional[str] = None
    SHIP_FROM_CITY: str = "Your City"
    SHIP_FROM_STATE: str = "ST"
    SHIP_FROM_ZIP: str = "12345"
    SHIP_FROM_COUNTRY: str = "US"
    SHIP_FROM_PHONE: str = "555-555-5555"

    # ===================
    # Redis / Background Jobs
    # ===================
    REDIS_URL: Optional[str] = None

    # ===================
    # Logging
    # ===================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text
    LOG_FILE: Optional[str] = None
    AUDIT_LOG_FILE: Optional[str] = "./logs/audit.log"

    # ===================
    # WooCommerce (future)
    # ===================
    WOOCOMMERCE_URL: Optional[str] = None
    WOOCOMMERCE_KEY: Optional[str] = None
    WOOCOMMERCE_SECRET: Optional[str] = None
    WOOCOMMERCE_WEBHOOK_SECRET: Optional[str] = None

    # ===================
    # QuickBooks (future)
    # ===================
    QUICKBOOKS_CLIENT_ID: Optional[str] = None
    QUICKBOOKS_CLIENT_SECRET: Optional[str] = None
    QUICKBOOKS_REDIRECT_URI: Optional[str] = None
    QUICKBOOKS_ENVIRONMENT: str = "sandbox"

    # ===================
    # Product Tier
    # ===================
    TIER: str = Field(default="open", description="open, pro, enterprise")
    LICENSE_KEY: Optional[str] = None

    # ===================
    # MRP Settings (safe defaults)
    # ===================
    INCLUDE_SALES_ORDERS_IN_MRP: bool = False
    AUTO_MRP_ON_ORDER_CREATE: bool = False
    AUTO_MRP_ON_SHIPMENT: bool = False
    AUTO_MRP_ON_CONFIRMATION: bool = False
    MRP_ENABLE_SUB_ASSEMBLY_CASCADING: bool = False
    MRP_VALIDATION_STRICT_MODE: bool = True

    # ===================
    # Manufacturing
    # ===================
    MACHINE_HOURLY_RATE: float = 1.50
    MACHINE_TIME_SKU: str = "MFG-MACHINE-TIME"
    LEGACY_MACHINE_TIME_SKU: str = "SVC-MACHINE-TIME"

    # ===================
    # Pricing
    # ===================
    MATERIAL_COST_PLA: float = 0.017
    MATERIAL_COST_PETG: float = 0.017
    MATERIAL_COST_ABS: float = 0.020
    MATERIAL_COST_ASA: float = 0.020
    MATERIAL_COST_TPU: float = 0.033

    MARKUP_PLA: float = 3.5
    MARKUP_PETG: float = 3.5
    MARKUP_ABS: float = 4.0
    MARKUP_ASA: float = 4.0
    MARKUP_TPU: float = 4.5

    MINIMUM_ORDER_VALUE: float = 10.00
    AUTO_APPROVE_THRESHOLD: float = 50.00
    QUOTE_EXPIRATION_DAYS: int = 30

    ABS_ASA_MAX_X_MM: int = 200
    ABS_ASA_MAX_Y_MM: int = 200
    ABS_ASA_MAX_Z_MM: int = 100

    PRINTING_HOURS_PER_DAY: int = 8
    PROCESSING_BUFFER_DAYS: int = 2
    RUSH_48H_REDUCTION_DAYS: int = 3
    RUSH_24H_REDUCTION_DAYS: int = 4

    # JSON-like knobs from env; allow string or parsed object
    QUANTITY_DISCOUNTS: Optional[Any] = Field(
        default=None,
        description="JSON: [{'min_quantity': 100, 'discount': 0.30}, ...]",
    )
    FINISH_COSTS: Optional[Any] = Field(
        default=None,
        description="JSON: {'standard': 0, 'cleanup': 3, ...}",
    )
    RUSH_MULTIPLIERS: Optional[Any] = Field(
        default=None,
        description="JSON: {'standard': 1.0, 'fast': 1.25, ...}",
    )
    PRINTER_FLEET: Optional[Any] = Field(
        default=None,
        description="JSON: {'total_printers': 4, 'printers': [...]}",
    )

    @field_validator(
        "QUANTITY_DISCOUNTS", "FINISH_COSTS", "RUSH_MULTIPLIERS", "PRINTER_FLEET", mode="before"
    )
    @classmethod
    def parse_json_string(cls, v):
        """Accept JSON string or already-parsed object."""
        if v is None or v == "":
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return v

    @property
    def material_costs(self) -> Dict[str, Decimal]:
        return {
            "PLA": Decimal(str(self.MATERIAL_COST_PLA)),
            "PETG": Decimal(str(self.MATERIAL_COST_PETG)),
            "ABS": Decimal(str(self.MATERIAL_COST_ABS)),
            "ASA": Decimal(str(self.MATERIAL_COST_ASA)),
            "TPU": Decimal(str(self.MATERIAL_COST_TPU)),
        }

    @property
    def markup_multipliers(self) -> Dict[str, Decimal]:
        return {
            "PLA": Decimal(str(self.MARKUP_PLA)),
            "PETG": Decimal(str(self.MARKUP_PETG)),
            "ABS": Decimal(str(self.MARKUP_ABS)),
            "ASA": Decimal(str(self.MARKUP_ASA)),
            "TPU": Decimal(str(self.MARKUP_TPU)),
        }

    @property
    def quantity_discounts(self) -> List[Dict[str, Any]]:
        if self.QUANTITY_DISCOUNTS and isinstance(self.QUANTITY_DISCOUNTS, list):
            return [
                {
                    "min_quantity": d["min_quantity"],
                    "discount": Decimal(str(d["discount"])),
                }
                for d in self.QUANTITY_DISCOUNTS  # type: ignore[union-attr]
            ]
        return [
            {"min_quantity": 100, "discount": Decimal("0.30")},
            {"min_quantity": 50, "discount": Decimal("0.20")},
            {"min_quantity": 10, "discount": Decimal("0.10")},
        ]

    @property
    def finish_costs(self) -> Dict[str, Decimal]:
        if self.FINISH_COSTS and isinstance(self.FINISH_COSTS, dict):
            return {k: Decimal(str(v)) for k, v in self.FINISH_COSTS.items()}  # type: ignore[union-attr]
        return {
            "standard": Decimal("0.00"),
            "cleanup": Decimal("3.00"),
            "sanded": Decimal("8.00"),
            "painted": Decimal("20.00"),
            "custom": Decimal("0.00"),
        }

    @property
    def rush_multipliers(self) -> Dict[str, Decimal]:
        if self.RUSH_MULTIPLIERS and isinstance(self.RUSH_MULTIPLIERS, dict):
            return {k: Decimal(str(v)) for k, v in self.RUSH_MULTIPLIERS.items()}  # type: ignore[union-attr]
        return {
            "standard": Decimal("1.0"),
            "fast": Decimal("1.25"),
            "rush_48h": Decimal("1.5"),
            "rush_24h": Decimal("2.0"),
        }

    @property
    def printer_fleet_config(self) -> Dict[str, Any]:
        if self.PRINTER_FLEET and isinstance(self.PRINTER_FLEET, dict):
            return self.PRINTER_FLEET  # type: ignore[return-value]
        return {
            "total_printers": 4,
            "printers": [
                {"model": "Bambu P1S", "quantity": 1},
                {"model": "Bambu A1", "quantity": 3},
            ],
            "daily_capacity_hours": 80,
            "average_hours_per_printer_per_day": 20,
        }

    @property
    def abs_asa_size_limits(self) -> Dict[str, int]:
        return {
            "max_x_mm": self.ABS_ASA_MAX_X_MM,
            "max_y_mm": self.ABS_ASA_MAX_Y_MM,
            "max_z_mm": self.ABS_ASA_MAX_Z_MM,
        }

    @property
    def delivery_estimation(self) -> Dict[str, Any]:
        return {
            "printing_hours_per_day": self.PRINTING_HOURS_PER_DAY,
            "processing_buffer_days": self.PROCESSING_BUFFER_DAYS,
            "rush_reduction_days": {
                "rush_48h": self.RUSH_48H_REDUCTION_DAYS,
                "rush_24h": self.RUSH_24H_REDUCTION_DAYS,
            },
        }

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"

    @property
    def is_pro_tier(self) -> bool:
        return self.TIER.lower() in ("pro", "enterprise")

    @property
    def is_enterprise_tier(self) -> bool:
        return self.TIER.lower() == "enterprise"


@lru_cache
def get_settings() -> Settings:
    """Singleton settings loader (cached)."""
    return Settings()


# Convenience alias for backward compatibility with existing code
settings = get_settings()
