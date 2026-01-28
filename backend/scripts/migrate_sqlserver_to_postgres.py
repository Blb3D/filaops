"""
SQL Server to PostgreSQL Migration Tool

Read-only extraction from SQL Server, transformation, and load into Postgres.
Includes reconciliation reporting.

Usage:
    python migrate_sqlserver_to_postgres.py --source-conn "mssql+pyodbc://..." --target-conn "postgresql://..." --dry-run
"""

import argparse
import sys
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from psycopg2.extras import execute_values

from app.logging_config import get_logger

logger = get_logger(__name__)


class SQLServerToPostgresMigrator:
    """Migrate data from SQL Server to PostgreSQL."""

    def __init__(self, source_conn_str: str, target_conn_str: str, dry_run: bool = False):
        self.source_conn_str = source_conn_str
        self.target_conn_str = target_conn_str
        self.dry_run = dry_run

        # Create engines
        self.source_engine = create_engine(source_conn_str, poolclass=NullPool, echo=False)
        self.target_engine = create_engine(target_conn_str, poolclass=NullPool, echo=False)

        self.source_session = sessionmaker(bind=self.source_engine)()
        self.target_session = sessionmaker(bind=self.target_engine)()

        # Track migration stats
        self.stats = {"tables_migrated": 0, "rows_migrated": 0, "errors": [], "warnings": []}

    def get_table_list(self) -> List[str]:
        """Get list of tables to migrate (exclude system tables)."""
        inspector = inspect(self.source_engine)
        all_tables = inspector.get_table_names()

        # Filter out system tables
        exclude_prefixes = ["sys", "information_schema", "__"]
        tables = [t for t in all_tables if not any(t.startswith(prefix) for prefix in exclude_prefixes)]

        # Order by dependencies (simple: put common tables first)
        priority_order = [
            "users",
            "vendors",
            "products",
            "categories",
            "boms",
            "bom_lines",
            "routings",
            "routing_operations",
            "work_centers",
            "resources",
            "quotes",
            "sales_orders",
            "sales_order_lines",
            "purchase_orders",
            "purchase_order_lines",
            "production_orders",
            "production_order_operations",
            "inventory",
            "inventory_transactions",
            "inventory_locations",
            "material_lots",
            "serial_numbers",
            "production_lot_consumptions",
            "customer_traceability_profiles",
        ]

        ordered = []
        remaining = []

        for table in priority_order:
            if table in tables:
                ordered.append(table)

        for table in tables:
            if table not in ordered:
                remaining.append(table)

        return ordered + remaining

    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """Get column definitions for a table."""
        inspector = inspect(self.source_engine)
        columns = inspector.get_columns(table_name)
        return columns

    def migrate_table(self, table_name: str) -> Dict[str, Any]:
        """Migrate a single table."""
        logger.info(f"Migrating table: {table_name}")

        result = {"table": table_name, "rows_read": 0, "rows_inserted": 0, "errors": []}

        try:
            # Read all rows from source
            query = text(f"SELECT * FROM [{table_name}]")
            rows = self.source_session.execute(query).fetchall()
            result["rows_read"] = len(rows)

            if len(rows) == 0:
                logger.info(f"  Table {table_name} is empty, skipping")
                return result

            # Get column names
            columns = [col.name for col in rows[0].__table__.columns] if rows else []
            if not columns:
                # Fallback: get columns from inspection
                inspector = inspect(self.source_engine)
                columns = [col["name"] for col in inspector.get_columns(table_name)]

            # Convert rows to dicts
            rows_data = []
            for row in rows:
                row_dict = {}
                for i, col_name in enumerate(columns):
                    value = row[i] if isinstance(row, tuple) else getattr(row, col_name, None)
                    # Handle SQL Server specific types
                    if isinstance(value, Decimal):
                        value = float(value)
                    elif isinstance(value, datetime):
                        value = value.isoformat()
                    elif value is None:
                        value = None
                    row_dict[col_name] = value
                rows_data.append(row_dict)

            # Insert into target (Postgres)
            if not self.dry_run:
                # Use execute_values for bulk insert
                conn = self.target_engine.raw_connection()
                cursor = conn.cursor()

                # Build INSERT statement
                cols_str = ", ".join([f'"{col}"' for col in columns])
                placeholders = ", ".join(["%s"] * len(columns))
                insert_sql = f'INSERT INTO "{table_name}" ({cols_str}) VALUES ({placeholders})'

                # Prepare values
                values = [tuple(row_dict.get(col) for col in columns) for row_dict in rows_data]

                try:
                    execute_values(cursor, insert_sql, values)
                    conn.commit()
                    result["rows_inserted"] = len(rows_data)
                    logger.info(f"  Inserted {len(rows_data)} rows into {table_name}")
                except Exception as e:
                    conn.rollback()
                    result["errors"].append(str(e))
                    logger.error(f"  Error inserting into {table_name}: {e}")
                finally:
                    cursor.close()
                    conn.close()
            else:
                result["rows_inserted"] = len(rows_data)
                logger.info(f"  [DRY RUN] Would insert {len(rows_data)} rows into {table_name}")

        except Exception as e:
            result["errors"].append(str(e))
            logger.error(f"  Error migrating {table_name}: {e}")

        return result

    def generate_reconciliation_report(self) -> Dict[str, Any]:
        """Generate reconciliation report comparing source and target."""
        report = {"generated_at": datetime.utcnow().isoformat(), "tables": {}}

        tables = self.get_table_list()

        for table in tables:
            try:
                # Count source rows
                source_count = self.source_session.execute(text(f"SELECT COUNT(*) FROM [{table}]")).scalar()

                # Count target rows
                target_count = self.target_session.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()

                report["tables"][table] = {
                    "source_count": source_count,
                    "target_count": target_count,
                    "match": source_count == target_count,
                    "difference": target_count - source_count,
                }
            except Exception as e:
                report["tables"][table] = {"error": str(e)}

        # Key totals
        key_tables = ["inventory", "production_orders", "purchase_orders", "sales_orders", "material_lots"]

        report["key_totals"] = {}
        for table in key_tables:
            if table in report["tables"]:
                report["key_totals"][table] = report["tables"][table]

        return report

    def migrate_all(self) -> Dict[str, Any]:
        """Migrate all tables."""
        logger.info("Starting migration from SQL Server to PostgreSQL")
        logger.info(f"Dry run: {self.dry_run}")

        tables = self.get_table_list()
        logger.info(f"Found {len(tables)} tables to migrate")

        results = {}
        for table in tables:
            result = self.migrate_table(table)
            results[table] = result

            if result["errors"]:
                self.stats["errors"].extend(result["errors"])
            else:
                self.stats["tables_migrated"] += 1
                self.stats["rows_migrated"] += result["rows_inserted"]

        # Generate reconciliation report
        logger.info("Generating reconciliation report...")
        reconciliation = self.generate_reconciliation_report()

        return {"stats": self.stats, "table_results": results, "reconciliation": reconciliation}

    def close(self):
        """Close connections."""
        self.source_session.close()
        self.target_session.close()
        self.source_engine.dispose()
        self.target_engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Migrate SQL Server database to PostgreSQL")
    parser.add_argument("--source-conn", required=True, help="SQL Server connection string")
    parser.add_argument("--target-conn", required=True, help="PostgreSQL connection string")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (don't actually insert)")
    parser.add_argument("--output", help="Output file for reconciliation report (JSON)")

    args = parser.parse_args()

    migrator = SQLServerToPostgresMigrator(
        source_conn_str=args.source_conn, target_conn_str=args.target_conn, dry_run=args.dry_run
    )

    try:
        results = migrator.migrate_all()

        # Print summary
        print("\n" + "=" * 80)
        print("MIGRATION SUMMARY")
        print("=" * 80)
        print(f"Tables migrated: {results['stats']['tables_migrated']}")
        print(f"Rows migrated: {results['stats']['rows_migrated']}")
        print(f"Errors: {len(results['stats']['errors'])}")

        if results["stats"]["errors"]:
            print("\nErrors:")
            for error in results["stats"]["errors"][:10]:  # Show first 10
                print(f"  - {error}")

        # Print reconciliation
        print("\n" + "=" * 80)
        print("RECONCILIATION REPORT")
        print("=" * 80)
        print("\nKey Totals:")
        for table, data in results["reconciliation"]["key_totals"].items():
            if "error" not in data:
                match_str = "✓" if data["match"] else "✗"
                print(f"  {match_str} {table}: Source={data['source_count']}, Target={data['target_count']}")

        # Save report if requested
        if args.output:
            import json

            with open(args.output, "w") as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\nFull report saved to: {args.output}")

    finally:
        migrator.close()


if __name__ == "__main__":
    main()
