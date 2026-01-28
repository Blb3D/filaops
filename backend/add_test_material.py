"""Add test material to routing operation"""

from decimal import Decimal
from app.db.session import SessionLocal
from app.models.manufacturing import RoutingOperationMaterial

db = SessionLocal()

# Add Black PLA to operation 20 (Print step for WIDGET-01)
material = RoutingOperationMaterial(
    routing_operation_id=20,
    component_id=1637,  # Black PLA
    quantity=Decimal("37"),
    quantity_per="unit",
    unit="G",
    scrap_factor=Decimal("5"),
    is_cost_only=False,
    is_optional=False,
    notes="Black PLA filament for print",
)
db.add(material)
db.commit()
db.refresh(material)

print(f"Created material ID: {material.id}")
print(f"  Operation: {material.routing_operation_id}")
print(f"  Component: {material.component_id}")
print(f"  Quantity: {material.quantity} {material.unit} per {material.quantity_per}")

db.close()
