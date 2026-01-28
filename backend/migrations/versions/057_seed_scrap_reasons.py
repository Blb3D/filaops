"""
Seed default scrap reasons for production operations.

These are common scrap reasons for 3D printing manufacturing.

Revision ID: 057_seed_scrap_reasons
Revises: 056_migrate_bom
Create Date: 2025-01-21
"""

from alembic import op
from sqlalchemy import text

# revision identifiers
revision = "057_seed_scrap_reasons"
down_revision = "056_migrate_bom"
branch_labels = None
depends_on = None


DEFAULT_SCRAP_REASONS = [
    # (code, name, description, sequence)
    # Print failures
    ("adhesion", "Adhesion Failure", "Part did not adhere to bed properly", 10),
    ("layer_shift", "Layer Shift", "Layers shifted during print causing misalignment", 20),
    ("stringing", "Stringing", "Excessive stringing between features", 30),
    ("warping", "Warping", "Part warped during cooling", 40),
    ("nozzle_clog", "Nozzle Clog", "Nozzle became clogged during print", 50),
    # Physical damage
    ("damage", "Physical Damage", "Part was damaged during handling or post-processing", 60),
    # Quality issues
    ("quality_fail", "Quality Fail", "Part failed quality inspection", 70),
    ("dimensional", "Dimensional Out of Spec", "Part dimensions outside tolerance", 80),
    ("surface_defect", "Surface Defect", "Visible surface quality issues", 90),
    # Material issues
    ("material_defect", "Material Defect", "Raw material had defects", 100),
    ("wrong_material", "Wrong Material", "Wrong material was used", 110),
    # Other
    ("operator_error", "Operator Error", "Error made by operator", 120),
    ("machine_failure", "Machine Failure", "Printer or machine malfunction", 130),
    ("other", "Other", "Other reason - specify in notes", 999),
]


def upgrade():
    """Insert default scrap reasons if they don't exist."""
    connection = op.get_bind()

    for code, name, description, sequence in DEFAULT_SCRAP_REASONS:
        # Check if already exists
        existing = connection.execute(
            text("SELECT id FROM scrap_reasons WHERE code = :code"), {"code": code}
        ).fetchone()

        if not existing:
            connection.execute(
                text("""
                    INSERT INTO scrap_reasons (code, name, description, sequence, active, created_at, updated_at)
                    VALUES (:code, :name, :description, :sequence, true, NOW(), NOW())
                """),
                {
                    "code": code,
                    "name": name,
                    "description": description,
                    "sequence": sequence,
                },
            )
            print(f"  Added scrap reason: {code}")
        else:
            print(f"  Scrap reason already exists: {code}")


def downgrade():
    """Remove seeded scrap reasons."""
    connection = op.get_bind()

    codes = [r[0] for r in DEFAULT_SCRAP_REASONS]
    placeholders = ", ".join([f":code{i}" for i in range(len(codes))])
    params = {f"code{i}": code for i, code in enumerate(codes)}

    connection.execute(text(f"DELETE FROM scrap_reasons WHERE code IN ({placeholders})"), params)
