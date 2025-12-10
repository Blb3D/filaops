"""
BLB3D ERP - Main FastAPI Application
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1 import router as api_v1_router
from app.core.config import settings
from app.exceptions import BLB3DException
from app.logging_config import setup_logging, get_logger

# Setup structured logging
setup_logging()
logger = get_logger(__name__)

# Rate limiter - shared across all endpoints
limiter = Limiter(key_func=get_remote_address)


def init_database():
    """Initialize database tables on startup.
    
    Creates all tables from SQLAlchemy models if they don't exist.
    Safe to run multiple times - only creates missing tables.
    """
    try:
        from app.db.session import engine
        from app.db.base import Base
        
        # Import all models so they're registered with Base.metadata
        # The models/__init__.py imports everything we need
        import app.models  # noqa: F401
        
        logger.info("Checking database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables ready")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        # Don't raise - let the app start and show errors on first request
        # This allows health checks to pass while DB issues are debugged


def seed_default_data():
    """Check if setup is needed (no users exist).
    
    NOTE: We no longer auto-create admin users for security.
    Users create their own admin account via /setup on first run.
    """
    try:
        from app.db.session import SessionLocal
        from app.models.user import User
        
        db = SessionLocal()
        try:
            user_count = db.query(User).count()
            if user_count == 0:
                logger.info("No users found - first-run setup required at /setup")
            else:
                logger.info(f"Found {user_count} existing users")
        finally:
            db.close()
            
    except Exception as e:
        logger.warning(f"Could not check user data: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info(
        "Starting FilaOps ERP API",
        extra={
            "version": settings.VERSION,
            "environment": getattr(settings, "ENVIRONMENT", "development"),
            "debug": getattr(settings, "DEBUG", False),
        }
    )
    
    # Initialize database tables
    init_database()
    
    # Seed default data (admin user)
    seed_default_data()
    
    yield
    
    # Shutdown
    logger.info("Shutting down FilaOps ERP API")


# Create FastAPI app
app = FastAPI(
    title="FilaOps ERP API",
    description="Open-source ERP for 3D print farms",
    version=settings.VERSION,
    lifespan=lifespan,
)

# Set up rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Rate limiting middleware (must be before CORS)
app.add_middleware(SlowAPIMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS if hasattr(settings, 'ALLOWED_ORIGINS') else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===================
# Exception Handlers
# ===================


@app.exception_handler(BLB3DException)
async def blb3d_exception_handler(request: Request, exc: BLB3DException):
    """Handle all custom BLB3D exceptions."""
    logger.warning(
        f"BLB3D Exception: {exc.error_code} - {exc.message}",
        extra={"error_code": exc.error_code, "details": exc.details, "path": request.url.path}
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with cleaner format."""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"],
        })

    logger.warning(
        f"Validation error on {request.url.path}",
        extra={"errors": errors}
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": {"errors": errors},
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle SQLAlchemy database errors."""
    # Log full error for debugging but don't expose to client
    logger.error(
        f"Database error on {request.url.path}: {str(exc)}",
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "DATABASE_ERROR",
            "message": "A database error occurred. Please try again.",
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unexpected errors."""
    # Log full stack trace for debugging
    logger.error(
        f"Unexpected error on {request.url.path}: {str(exc)}",
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred. Please try again later.",
        },
    )


# Set limiter reference in auth module BEFORE including routes
# This ensures decorators have access to the limiter instance
# Note: Import is here due to circular dependency - limiter must be set before routes are included
from app.api.v1.endpoints import auth  # noqa: E402
auth.limiter = limiter

# Include API routes (must be after limiter setup)
app.include_router(api_v1_router, prefix="/api/v1")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "BLB3D ERP API",
        "version": "1.0.0",
        "status": "online"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
