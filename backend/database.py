"""Database configuration and session management for PostgreSQL"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Create engine for SQL Server
# Using NullPool to avoid connection pooling issues with SQL Server Express
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=True if os.getenv("DEBUG") == "True" else False,
    future=True
)

# Create SessionLocal class for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()

def get_db():
    """
    Dependency function to get database session.
    Used with FastAPI's Depends() for dependency injection.

    Usage:
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initialize database - create all tables.
    Should be called on application startup.
    """

    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")

def check_connection():
    """
    Test database connection.
    Returns True if connection is successful, False otherwise.
    """
    try:
        with engine.connect() as connection:
            connection.execute("SELECT 1")
            return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
