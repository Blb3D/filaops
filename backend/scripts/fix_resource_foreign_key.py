"""
Fix ProductionOrderOperation resource_id foreign key constraint

The foreign key was incorrectly pointing to 'machines.id' but should point to 'resources.id'.
This script drops the old constraint and creates the correct one.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.session import SessionLocal, engine
from app.logging_config import get_logger

logger = get_logger(__name__)


def fix_foreign_key():
    """Fix the resource_id foreign key constraint"""
    db = SessionLocal()
    try:
        logger.info("Fixing production_order_operations.resource_id foreign key constraint...")
        
        # Use autocommit mode for DDL statements
        with engine.begin() as conn:
            # Drop the old constraint if it exists
            logger.info("Dropping old foreign key constraint (if exists)...")
            conn.execute(text("""
                ALTER TABLE production_order_operations 
                DROP CONSTRAINT IF EXISTS production_order_operations_resource_id_fkey;
            """))
            logger.info("  ✓ Old constraint dropped")
            
            # Create the correct foreign key constraint
            logger.info("Creating new foreign key constraint pointing to resources.id...")
            conn.execute(text("""
                ALTER TABLE production_order_operations 
                ADD CONSTRAINT production_order_operations_resource_id_fkey 
                FOREIGN KEY (resource_id) 
                REFERENCES resources(id) 
                ON DELETE SET NULL;
            """))
            logger.info("  ✓ New constraint created")
        
        logger.info("\n✅ Foreign key constraint fixed successfully!")
        logger.info("   production_order_operations.resource_id now correctly references resources.id")
        
    except Exception as e:
        logger.error(f"❌ Failed to fix foreign key constraint: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("FIXING RESOURCE FOREIGN KEY CONSTRAINT")
    print("="*60)
    print("\nThis will:")
    print("  1. Drop the old constraint (machines.id)")
    print("  2. Create the correct constraint (resources.id)")
    print("\n⚠️  Make sure you have a database backup!")
    print()
    
    confirm = input("Continue? (yes/no): ")
    if confirm.lower() != "yes":
        print("Cancelled.")
        sys.exit(0)
    
    fix_foreign_key()

