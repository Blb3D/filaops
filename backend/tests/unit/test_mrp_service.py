"""
Unit Tests for MRP Service

Tests core MRP functionality:
1. BOM Explosion (single-level, multi-level, circular detection)
2. Net Requirements Calculation
3. Planned Order Generation

These tests use an in-memory SQLite database and test the MRP service
logic in isolation.
"""
import pytest
from decimal import Decimal
from datetime import date, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.services.mrp import MRPService, ComponentRequirement, NetRequirement, convert_uom


# ============================================================================
# Test Database Setup
# ============================================================================

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_all_tables():
    """Create all tables needed for MRP testing
    
    Note: We create tables manually to handle SQLite limitations:
    - SQLite doesn't support computed columns
    - We create a simplified inventory table without the computed column
    """
    from sqlalchemy import Table, Column, Integer, String, Numeric, DateTime, Date, Text, Boolean, ForeignKey, MetaData
    
    metadata = MetaData()
    
    # Products table
    Table('products', metadata,
        Column('id', Integer, primary_key=True),
        Column('sku', String(50), unique=True, nullable=False),
        Column('legacy_sku', String(50), nullable=True),
        Column('name', String(255), nullable=False),
        Column('description', Text, nullable=True),
        Column('category', String(100), nullable=True),
        Column('unit', String(20), default='EA'),
        Column('item_type', String(20), default='finished_good'),
        Column('procurement_type', String(20), default='buy'),
        Column('category_id', Integer, nullable=True),
        Column('material_type_id', Integer, nullable=True),
        Column('color_id', Integer, nullable=True),
        Column('cost_method', String(20), default='average'),
        Column('standard_cost', Numeric(10, 2), nullable=True),
        Column('average_cost', Numeric(10, 2), nullable=True),
        Column('last_cost', Numeric(10, 2), nullable=True),
        Column('cost', Numeric(18, 4), nullable=True),
        Column('selling_price', Numeric(18, 4), nullable=True),
        Column('weight', Numeric(18, 4), nullable=True),
        Column('weight_oz', Numeric(8, 2), nullable=True),
        Column('length_in', Numeric(8, 2), nullable=True),
        Column('width_in', Numeric(8, 2), nullable=True),
        Column('height_in', Numeric(8, 2), nullable=True),
        Column('lead_time_days', Integer, nullable=True),
        Column('min_order_qty', Numeric(10, 2), nullable=True),
        Column('reorder_point', Numeric(10, 2), nullable=True),
        Column('safety_stock', Numeric(18, 4), default=0),
        Column('preferred_vendor_id', Integer, nullable=True),
        Column('stocking_policy', String(20), default='on_demand'),
        Column('upc', String(50), nullable=True),
        Column('type', String(20), default='standard'),
        Column('gcode_file_path', String(500), nullable=True),
        Column('is_public', Boolean, default=True),
        Column('sales_channel', String(20), default='public'),
        Column('customer_id', Integer, nullable=True),
        Column('is_raw_material', Boolean, default=False),
        Column('has_bom', Boolean, default=False),
        Column('track_lots', Boolean, default=False),
        Column('track_serials', Boolean, default=False),
        Column('active', Boolean, default=True),
        Column('woocommerce_product_id', Integer, nullable=True),
        Column('squarespace_product_id', String(50), nullable=True),
        Column('created_at', DateTime, nullable=False),
        Column('updated_at', DateTime, nullable=False),
    )
    
    # BOMs table
    Table('boms', metadata,
        Column('id', Integer, primary_key=True),
        Column('product_id', Integer, ForeignKey('products.id'), nullable=False),
        Column('code', String(50), nullable=True),
        Column('name', String(255), nullable=True),
        Column('version', Integer, default=1),
        Column('revision', String(10), nullable=True),
        Column('active', Boolean, default=True),
        Column('total_cost', Numeric(18, 4), nullable=True),
        Column('assembly_time_minutes', Integer, nullable=True),
        Column('effective_date', Date, nullable=True),
        Column('notes', Text, nullable=True),
        Column('created_at', DateTime, nullable=False),
    )
    
    # BOM Lines table
    Table('bom_lines', metadata,
        Column('id', Integer, primary_key=True),
        Column('bom_id', Integer, ForeignKey('boms.id'), nullable=False),
        Column('component_id', Integer, ForeignKey('products.id'), nullable=False),
        Column('sequence', Integer, nullable=True),
        Column('quantity', Numeric(18, 4), nullable=False),
        Column('unit', String(20), default='EA'),
        Column('consume_stage', String(20), default='production'),
        Column('is_cost_only', Boolean, default=False),
        Column('scrap_factor', Numeric(5, 2), default=0),
        Column('notes', Text, nullable=True),
    )
    
    # Inventory Locations table
    Table('inventory_locations', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(100), nullable=False),
        Column('code', String(50), nullable=True),
        Column('type', String(50), nullable=True),
        Column('parent_id', Integer, nullable=True),
        Column('active', Boolean, default=True),
    )
    
    # Inventory table (simplified, no computed column)
    Table('inventory', metadata,
        Column('id', Integer, primary_key=True),
        Column('product_id', Integer, ForeignKey('products.id'), nullable=False),
        Column('location_id', Integer, ForeignKey('inventory_locations.id'), nullable=False),
        Column('on_hand_quantity', Numeric(10, 2), default=0),
        Column('allocated_quantity', Numeric(10, 2), default=0),
        # Note: available_quantity computed column omitted for SQLite compatibility
        Column('last_counted', DateTime, nullable=True),
        Column('created_at', DateTime, nullable=False),
        Column('updated_at', DateTime, nullable=False),
    )
    
    # Production Orders table
    Table('production_orders', metadata,
        Column('id', Integer, primary_key=True),
        Column('code', String(50), unique=True),
        Column('product_id', Integer, ForeignKey('products.id'), nullable=False),
        Column('bom_id', Integer, nullable=True),
        Column('routing_id', Integer, nullable=True),
        Column('sales_order_id', Integer, nullable=True),
        Column('sales_order_line_id', Integer, nullable=True),
        Column('parent_order_id', Integer, nullable=True),  # For split orders
        Column('split_sequence', Integer, nullable=True),   # 1, 2, 3... for child orders
        Column('quantity_ordered', Numeric(18, 4), nullable=False),
        Column('quantity_completed', Numeric(18, 4), default=0),
        Column('quantity_scrapped', Numeric(18, 4), default=0),
        Column('status', String(50), default='draft'),
        # QC Status fields (Sprint 3-4)
        Column('qc_status', String(50), default='not_required'),
        Column('qc_notes', Text, nullable=True),
        Column('qc_inspected_by', String(100), nullable=True),
        Column('qc_inspected_at', DateTime, nullable=True),
        Column('priority', Integer, default=5),
        Column('source', String(50), nullable=True),
        Column('due_date', Date, nullable=True),
        Column('scheduled_start', DateTime, nullable=True),
        Column('scheduled_end', DateTime, nullable=True),
        Column('actual_start', DateTime, nullable=True),
        Column('actual_end', DateTime, nullable=True),
        Column('estimated_time_minutes', Integer, nullable=True),
        Column('actual_time_minutes', Integer, nullable=True),
        Column('estimated_material_cost', Numeric(18, 4), nullable=True),
        Column('estimated_labor_cost', Numeric(18, 4), nullable=True),
        Column('estimated_total_cost', Numeric(18, 4), nullable=True),
        Column('actual_material_cost', Numeric(18, 4), nullable=True),
        Column('actual_labor_cost', Numeric(18, 4), nullable=True),
        Column('actual_total_cost', Numeric(18, 4), nullable=True),
        Column('assigned_to', String(100), nullable=True),
        Column('notes', Text, nullable=True),
        Column('scrap_reason', String(100), nullable=True),
        Column('scrapped_at', DateTime, nullable=True),
        Column('remake_of_id', Integer, nullable=True),
        Column('created_at', DateTime, nullable=False),
        Column('updated_at', DateTime, nullable=False),
        Column('created_by', String(100), nullable=True),
        Column('released_at', DateTime, nullable=True),
        Column('completed_at', DateTime, nullable=True),
    )
    
    # MRP Runs table
    Table('mrp_runs', metadata,
        Column('id', Integer, primary_key=True),
        Column('run_date', DateTime, nullable=False),
        Column('planning_horizon_days', Integer, default=30),
        Column('orders_processed', Integer, default=0),
        Column('components_analyzed', Integer, default=0),
        Column('shortages_found', Integer, default=0),
        Column('planned_orders_created', Integer, default=0),
        Column('status', String(20), default='running'),
        Column('error_message', Text, nullable=True),
        Column('created_by', Integer, nullable=True),
        Column('completed_at', DateTime, nullable=True),
    )
    
    # Purchase Orders table
    Table('purchase_orders', metadata,
        Column('id', Integer, primary_key=True),
        Column('po_number', String(50), unique=True),
        Column('vendor_id', Integer, nullable=True),
        Column('status', String(50), default='draft'),
        Column('order_date', Date, nullable=True),
        Column('expected_date', Date, nullable=True),
        Column('subtotal', Numeric(18, 4), default=0),
        Column('tax_amount', Numeric(18, 4), default=0),
        Column('shipping_cost', Numeric(18, 4), default=0),
        Column('total_amount', Numeric(18, 4), default=0),
        Column('notes', Text, nullable=True),
        Column('created_at', DateTime, nullable=False),
        Column('updated_at', DateTime, nullable=False),
        Column('created_by', String(100), nullable=True),
    )
    
    # Purchase Order Lines table
    Table('purchase_order_lines', metadata,
        Column('id', Integer, primary_key=True),
        Column('purchase_order_id', Integer, ForeignKey('purchase_orders.id'), nullable=False),
        Column('product_id', Integer, ForeignKey('products.id'), nullable=False),
        Column('line_number', Integer, nullable=False),
        Column('quantity_ordered', Numeric(18, 4), nullable=False),
        Column('quantity_received', Numeric(18, 4), default=0),
        Column('unit_cost', Numeric(18, 4), nullable=True),
        Column('line_total', Numeric(18, 4), default=0),
        Column('created_at', DateTime, nullable=False),
        Column('updated_at', DateTime, nullable=False),
    )
    
    # Planned Orders table
    Table('planned_orders', metadata,
        Column('id', Integer, primary_key=True),
        Column('order_type', String(20), nullable=False),
        Column('product_id', Integer, ForeignKey('products.id'), nullable=False),
        Column('quantity', Numeric(18, 4), nullable=False),
        Column('due_date', Date, nullable=False),
        Column('start_date', Date, nullable=False),
        Column('source_demand_type', String(50), nullable=True),
        Column('source_demand_id', Integer, nullable=True),
        Column('mrp_run_id', Integer, nullable=True),
        Column('status', String(20), default='planned'),
        Column('converted_to_po_id', Integer, nullable=True),
        Column('converted_to_mo_id', Integer, nullable=True),
        Column('notes', Text, nullable=True),
        Column('created_at', DateTime, nullable=False),
        Column('created_by', Integer, nullable=True),
        Column('updated_at', DateTime, nullable=True),
        Column('firmed_at', DateTime, nullable=True),
        Column('released_at', DateTime, nullable=True),
    )
    
    # Vendors table
    Table('vendors', metadata,
        Column('id', Integer, primary_key=True),
        Column('code', String(50), unique=True),
        Column('name', String(200), nullable=False),
        Column('contact_name', String(100), nullable=True),
        Column('email', String(200), nullable=True),
        Column('phone', String(50), nullable=True),
        Column('website', String(500), nullable=True),
        Column('payment_terms', String(100), nullable=True),
        Column('lead_time_days', Integer, nullable=True),
        Column('is_active', Boolean, default=True),
        Column('notes', Text, nullable=True),
        Column('created_at', DateTime, nullable=False),
        Column('updated_at', DateTime, nullable=False),
    )
    
    metadata.create_all(bind=engine)


def drop_all_tables():
    """Drop all tables"""
    from sqlalchemy import MetaData
    metadata = MetaData()
    metadata.reflect(bind=engine)
    metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create a fresh database session for each test"""
    create_all_tables()
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        drop_all_tables()


@pytest.fixture
def mrp_service(db):
    """Create MRP service instance"""
    return MRPService(db)


# ============================================================================
# Product & BOM Fixtures
# ============================================================================

@pytest.fixture
def raw_material_pla(db):
    """Create a raw material (PLA filament)"""
    from app.models.product import Product
    
    product = Product(
        sku="MAT-PLA-BLK",
        name="PLA Filament - Black",
        item_type="supply",
        procurement_type="buy",
        unit="KG",
        standard_cost=Decimal("20.00"),
        lead_time_days=7,
        safety_stock=Decimal("2.0"),
        has_bom=False,
        active=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@pytest.fixture
def raw_material_petg(db):
    """Create another raw material (PETG filament)"""
    from app.models.product import Product
    
    product = Product(
        sku="MAT-PETG-WHT",
        name="PETG Filament - White",
        item_type="supply",
        procurement_type="buy",
        unit="KG",
        standard_cost=Decimal("25.00"),
        lead_time_days=10,
        safety_stock=Decimal("1.0"),
        has_bom=False,
        active=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@pytest.fixture
def packaging_box(db):
    """Create a packaging component"""
    from app.models.product import Product
    
    product = Product(
        sku="PKG-BOX-SM",
        name="Small Shipping Box",
        item_type="supply",
        procurement_type="buy",
        unit="EA",
        standard_cost=Decimal("0.50"),
        lead_time_days=3,
        min_order_qty=Decimal("100"),
        has_bom=False,
        active=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@pytest.fixture
def hardware_insert(db):
    """Create a hardware component (threaded insert)"""
    from app.models.product import Product
    
    product = Product(
        sku="HW-INSERT-M3",
        name="M3 Threaded Insert",
        item_type="component",
        procurement_type="buy",
        unit="EA",
        standard_cost=Decimal("0.10"),
        lead_time_days=14,
        min_order_qty=Decimal("500"),
        has_bom=False,
        active=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@pytest.fixture
def finished_product_simple(db, raw_material_pla, packaging_box):
    """Create a simple finished product with single-level BOM"""
    from app.models.product import Product
    from app.models.bom import BOM, BOMLine
    
    # Create the finished product
    product = Product(
        sku="FG-WIDGET-001",
        name="Simple Widget",
        item_type="finished_good",
        procurement_type="make",
        unit="EA",
        standard_cost=Decimal("15.00"),
        selling_price=Decimal("29.99"),
        has_bom=True,
        active=True,
    )
    db.add(product)
    db.flush()
    
    # Create BOM
    bom = BOM(
        product_id=product.id,
        code=f"BOM-{product.sku}",
        name=f"BOM for {product.name}",
        version=1,
        active=True,
    )
    db.add(bom)
    db.flush()
    
    # BOM Lines: 0.1kg PLA + 1 box
    line1 = BOMLine(
        bom_id=bom.id,
        component_id=raw_material_pla.id,
        sequence=1,
        quantity=Decimal("0.1"),  # 100g of filament
        unit="KG",
        scrap_factor=Decimal("5.0"),  # 5% scrap
    )
    db.add(line1)
    
    line2 = BOMLine(
        bom_id=bom.id,
        component_id=packaging_box.id,
        sequence=2,
        quantity=Decimal("1.0"),
        unit="EA",
        scrap_factor=Decimal("0"),
    )
    db.add(line2)
    
    db.commit()
    db.refresh(product)
    return product


@pytest.fixture
def sub_assembly(db, raw_material_petg, hardware_insert):
    """Create a sub-assembly (intermediate product with its own BOM)"""
    from app.models.product import Product
    from app.models.bom import BOM, BOMLine
    
    # Create sub-assembly product
    product = Product(
        sku="SA-BRACKET-001",
        name="Mounting Bracket Sub-Assembly",
        item_type="component",
        procurement_type="make",
        unit="EA",
        standard_cost=Decimal("5.00"),
        has_bom=True,
        active=True,
    )
    db.add(product)
    db.flush()
    
    # Create BOM for sub-assembly
    bom = BOM(
        product_id=product.id,
        code=f"BOM-{product.sku}",
        name=f"BOM for {product.name}",
        version=1,
        active=True,
    )
    db.add(bom)
    db.flush()
    
    # Sub-assembly needs: 0.05kg PETG + 4 inserts
    line1 = BOMLine(
        bom_id=bom.id,
        component_id=raw_material_petg.id,
        sequence=1,
        quantity=Decimal("0.05"),
        unit="KG",
        scrap_factor=Decimal("10.0"),  # Higher scrap for small parts
    )
    db.add(line1)
    
    line2 = BOMLine(
        bom_id=bom.id,
        component_id=hardware_insert.id,
        sequence=2,
        quantity=Decimal("4.0"),
        unit="EA",
        scrap_factor=Decimal("0"),
    )
    db.add(line2)
    
    db.commit()
    db.refresh(product)
    return product


@pytest.fixture
def finished_product_multilevel(db, raw_material_pla, packaging_box, sub_assembly):
    """Create a finished product with multi-level BOM (includes sub-assembly)"""
    from app.models.product import Product
    from app.models.bom import BOM, BOMLine
    
    # Create the finished product
    product = Product(
        sku="FG-GADGET-001",
        name="Complex Gadget",
        item_type="finished_good",
        procurement_type="make",
        unit="EA",
        standard_cost=Decimal("35.00"),
        selling_price=Decimal("79.99"),
        has_bom=True,
        active=True,
    )
    db.add(product)
    db.flush()
    
    # Create BOM
    bom = BOM(
        product_id=product.id,
        code=f"BOM-{product.sku}",
        name=f"BOM for {product.name}",
        version=1,
        active=True,
    )
    db.add(bom)
    db.flush()
    
    # BOM Lines: 0.2kg PLA + 2 brackets (sub-assembly) + 1 box
    line1 = BOMLine(
        bom_id=bom.id,
        component_id=raw_material_pla.id,
        sequence=1,
        quantity=Decimal("0.2"),
        unit="KG",
        scrap_factor=Decimal("5.0"),
    )
    db.add(line1)
    
    line2 = BOMLine(
        bom_id=bom.id,
        component_id=sub_assembly.id,
        sequence=2,
        quantity=Decimal("2.0"),  # 2 brackets per gadget
        unit="EA",
        scrap_factor=Decimal("0"),
    )
    db.add(line2)
    
    line3 = BOMLine(
        bom_id=bom.id,
        component_id=packaging_box.id,
        sequence=3,
        quantity=Decimal("1.0"),
        unit="EA",
        scrap_factor=Decimal("0"),
    )
    db.add(line3)
    
    db.commit()
    db.refresh(product)
    return product


@pytest.fixture
def circular_bom_product(db, raw_material_pla):
    """Create products with circular BOM reference for testing cycle detection"""
    from app.models.product import Product
    from app.models.bom import BOM, BOMLine
    
    # Create Product A
    product_a = Product(
        sku="CIRC-A",
        name="Circular Product A",
        item_type="component",
        procurement_type="make",
        unit="EA",
        has_bom=True,
        active=True,
    )
    db.add(product_a)
    
    # Create Product B
    product_b = Product(
        sku="CIRC-B",
        name="Circular Product B",
        item_type="component",
        procurement_type="make",
        unit="EA",
        has_bom=True,
        active=True,
    )
    db.add(product_b)
    db.flush()
    
    # BOM for A includes B
    bom_a = BOM(
        product_id=product_a.id,
        code="BOM-CIRC-A",
        name="BOM for Circular A",
        version=1,
        active=True,
    )
    db.add(bom_a)
    db.flush()
    
    line_a = BOMLine(
        bom_id=bom_a.id,
        component_id=product_b.id,
        sequence=1,
        quantity=Decimal("1.0"),
        unit="EA",
    )
    db.add(line_a)
    
    # BOM for B includes A (creates cycle!)
    bom_b = BOM(
        product_id=product_b.id,
        code="BOM-CIRC-B",
        name="BOM for Circular B",
        version=1,
        active=True,
    )
    db.add(bom_b)
    db.flush()
    
    line_b = BOMLine(
        bom_id=bom_b.id,
        component_id=product_a.id,  # Creates circular reference!
        sequence=1,
        quantity=Decimal("1.0"),
        unit="EA",
    )
    db.add(line_b)
    
    db.commit()
    db.refresh(product_a)
    return product_a


# ============================================================================
# Inventory Fixtures
# ============================================================================

@pytest.fixture
def inventory_location(db):
    """Create a default inventory location"""
    from app.models.inventory import InventoryLocation
    
    location = InventoryLocation(
        code="MAIN",
        name="Main Warehouse",
        active=True,
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


@pytest.fixture
def inventory_with_stock(db, inventory_location, raw_material_pla, raw_material_petg, 
                         packaging_box, hardware_insert):
    """Create inventory records with some stock
    
    Note: We use raw SQL INSERT to avoid issues with the computed column
    (available_quantity) computed column that SQLite doesn't support.
    """
    from sqlalchemy import text
    
    # Insert inventory records directly to avoid computed column issues
    inventories_data = [
        (raw_material_pla.id, inventory_location.id, Decimal("5.0"), Decimal("1.0")),
        (raw_material_petg.id, inventory_location.id, Decimal("2.0"), Decimal("0")),
        (packaging_box.id, inventory_location.id, Decimal("50"), Decimal("0")),
        (hardware_insert.id, inventory_location.id, Decimal("100"), Decimal("0")),
    ]
    
    for product_id, location_id, on_hand, allocated in inventories_data:
        db.execute(
            text("""
                INSERT INTO inventory (product_id, location_id, on_hand_quantity, allocated_quantity, created_at, updated_at)
                VALUES (:product_id, :location_id, :on_hand, :allocated, :now, :now)
            """),
            {
                "product_id": product_id,
                "location_id": location_id,
                "on_hand": float(on_hand),
                "allocated": float(allocated),
                "now": datetime.utcnow(),
            }
        )
    
    db.commit()
    return inventories_data


# ============================================================================
# BOM EXPLOSION TESTS
# ============================================================================

class TestBOMExplosion:
    """Tests for BOM explosion functionality"""
    
    def test_single_level_bom_explosion(self, db, mrp_service, finished_product_simple):
        """Test exploding a simple single-level BOM"""
        requirements = mrp_service.explode_bom(
            product_id=finished_product_simple.id,
            quantity=Decimal("10"),
        )
        
        # Should have 2 components: PLA + Box
        assert len(requirements) == 2
        
        # Find PLA requirement
        pla_req = next((r for r in requirements if "PLA" in r.product_sku), None)
        assert pla_req is not None
        assert pla_req.bom_level == 0
        # 10 units * 0.1kg * 1.05 (5% scrap) = 1.05kg
        expected_pla = Decimal("10") * Decimal("0.1") * Decimal("1.05")
        assert pla_req.gross_quantity == expected_pla
        
        # Find Box requirement
        box_req = next((r for r in requirements if "BOX" in r.product_sku), None)
        assert box_req is not None
        assert box_req.bom_level == 0
        # 10 units * 1 box * 1.0 (no scrap) = 10 boxes
        assert box_req.gross_quantity == Decimal("10")
    
    def test_multi_level_bom_explosion(self, db, mrp_service, finished_product_multilevel,
                                       raw_material_pla, raw_material_petg, 
                                       hardware_insert, packaging_box, sub_assembly):
        """Test exploding a multi-level BOM (product contains sub-assemblies)"""
        requirements = mrp_service.explode_bom(
            product_id=finished_product_multilevel.id,
            quantity=Decimal("5"),
        )
        
        # Should have components from both levels:
        # Level 0: PLA, Sub-assembly, Box
        # Level 1 (from sub-assembly): PETG, Inserts
        # But sub-assembly itself is also listed as Level 0 component
        
        # Find all unique SKUs
        skus = {r.product_sku for r in requirements}
        
        # Should include: PLA, Box, Sub-assembly, PETG, Inserts
        assert "MAT-PLA-BLK" in skus  # Direct component
        assert "PKG-BOX-SM" in skus    # Direct component
        assert "SA-BRACKET-001" in skus  # Sub-assembly
        assert "MAT-PETG-WHT" in skus  # From sub-assembly
        assert "HW-INSERT-M3" in skus  # From sub-assembly
        
        # Verify level 0 components
        level_0 = [r for r in requirements if r.bom_level == 0]
        assert len(level_0) == 3  # PLA, Sub-assembly, Box
        
        # Verify level 1 components (from sub-assembly explosion)
        level_1 = [r for r in requirements if r.bom_level == 1]
        assert len(level_1) == 2  # PETG, Inserts
        
        # Verify quantities cascade correctly
        # Sub-assembly: 5 gadgets * 2 brackets = 10 brackets
        bracket_req = next((r for r in requirements if r.product_sku == "SA-BRACKET-001"), None)
        assert bracket_req.gross_quantity == Decimal("10")
        
        # PETG from brackets: 10 brackets * 0.05kg * 1.10 (10% scrap) = 0.55kg
        petg_req = next((r for r in requirements if r.product_sku == "MAT-PETG-WHT"), None)
        expected_petg = Decimal("10") * Decimal("0.05") * Decimal("1.10")
        assert petg_req.gross_quantity == expected_petg
        
        # Inserts from brackets: 10 brackets * 4 inserts = 40 inserts
        insert_req = next((r for r in requirements if r.product_sku == "HW-INSERT-M3"), None)
        assert insert_req.gross_quantity == Decimal("40")
    
    def test_circular_reference_detection(self, db, mrp_service, circular_bom_product):
        """Test that circular BOM references don't cause infinite loops"""
        # This should NOT hang or raise an exception - it should handle the cycle gracefully
        requirements = mrp_service.explode_bom(
            product_id=circular_bom_product.id,
            quantity=Decimal("1"),
        )
        
        # Should return some requirements without infinite recursion
        # The exact behavior depends on implementation:
        # - Could return empty (detecting cycle at start)
        # - Could return first level only (breaking at cycle detection)
        # Key is that it terminates without error
        assert isinstance(requirements, list)
        # Should have at most a few items, not infinitely many
        assert len(requirements) < 10
    
    def test_product_without_bom(self, db, mrp_service, raw_material_pla):
        """Test exploding a product that has no BOM (raw material)"""
        requirements = mrp_service.explode_bom(
            product_id=raw_material_pla.id,
            quantity=Decimal("5"),
        )
        
        # Raw materials have no BOM, so no components
        assert len(requirements) == 0
    
    def test_bom_explosion_with_due_date(self, db, mrp_service, finished_product_simple):
        """Test that due date is passed through to requirements"""
        due = date.today() + timedelta(days=14)
        
        requirements = mrp_service.explode_bom(
            product_id=finished_product_simple.id,
            quantity=Decimal("10"),
            due_date=due,
        )
        
        for req in requirements:
            assert req.due_date == due
    
    def test_bom_explosion_with_source_tracking(self, db, mrp_service, finished_product_simple):
        """Test that demand source is tracked in requirements"""
        requirements = mrp_service.explode_bom(
            product_id=finished_product_simple.id,
            quantity=Decimal("10"),
            source_demand_type="production_order",
            source_demand_id=123,
        )
        
        for req in requirements:
            assert req.source_demand_type == "production_order"
            assert req.source_demand_id == 123


# ============================================================================
# NET REQUIREMENTS TESTS
# ============================================================================

class TestNetRequirements:
    """Tests for net requirements calculation"""
    
    def test_net_requirement_with_sufficient_stock(self, db, mrp_service, 
                                                    raw_material_pla, inventory_with_stock):
        """Test net requirement when inventory covers demand"""
        # Gross requirement: 1kg, Available: 4kg (5 on hand - 1 allocated)
        req = ComponentRequirement(
            product_id=raw_material_pla.id,
            product_sku=raw_material_pla.sku,
            product_name=raw_material_pla.name,
            bom_level=0,
            gross_quantity=Decimal("1.0"),
        )
        
        net_reqs = mrp_service.calculate_net_requirements([req])
        
        assert len(net_reqs) == 1
        net = net_reqs[0]
        
        assert net.gross_quantity == Decimal("1.0")
        assert net.on_hand_quantity == Decimal("5.0")
        assert net.allocated_quantity == Decimal("1.0")
        assert net.available_quantity == Decimal("4.0")
        # Net shortage should be 0 (or consider safety stock of 2)
        # Formula: Net = Gross - Available - Incoming + Safety
        # = 1.0 - 4.0 - 0 + 2.0 = -1.0 -> 0 (no negative shortages)
        assert net.net_shortage == Decimal("0")
    
    def test_net_requirement_with_shortage(self, db, mrp_service,
                                           raw_material_pla, inventory_with_stock):
        """Test net requirement when inventory doesn't cover demand"""
        # Gross requirement: 10kg, Available: 4kg, Safety: 2kg
        req = ComponentRequirement(
            product_id=raw_material_pla.id,
            product_sku=raw_material_pla.sku,
            product_name=raw_material_pla.name,
            bom_level=0,
            gross_quantity=Decimal("10.0"),
        )
        
        net_reqs = mrp_service.calculate_net_requirements([req])
        
        assert len(net_reqs) == 1
        net = net_reqs[0]
        
        assert net.gross_quantity == Decimal("10.0")
        assert net.available_quantity == Decimal("4.0")
        # Net = Gross - On-Hand - Incoming + Safety (uses on_hand, not available, to avoid double-counting)
        # = 10.0 - 5.0 - 0 + 2.0 = 7.0
        assert net.net_shortage == Decimal("7.0")
    
    def test_net_requirement_with_no_inventory(self, db, mrp_service, raw_material_pla):
        """Test net requirement when product has no inventory records"""
        # Don't use the inventory_with_stock fixture
        req = ComponentRequirement(
            product_id=raw_material_pla.id,
            product_sku=raw_material_pla.sku,
            product_name=raw_material_pla.name,
            bom_level=0,
            gross_quantity=Decimal("5.0"),
        )
        
        net_reqs = mrp_service.calculate_net_requirements([req])
        
        assert len(net_reqs) == 1
        net = net_reqs[0]
        
        assert net.on_hand_quantity == Decimal("0")
        assert net.available_quantity == Decimal("0")
        # Net = 5.0 - 0 - 0 + 2.0 (safety) = 7.0
        assert net.net_shortage == Decimal("7.0")
    
    def test_aggregates_multiple_requirements(self, db, mrp_service,
                                              raw_material_pla, raw_material_petg,
                                              inventory_with_stock):
        """Test calculating net requirements for multiple products"""
        reqs = [
            ComponentRequirement(
                product_id=raw_material_pla.id,
                product_sku=raw_material_pla.sku,
                product_name=raw_material_pla.name,
                bom_level=0,
                gross_quantity=Decimal("2.0"),
            ),
            ComponentRequirement(
                product_id=raw_material_petg.id,
                product_sku=raw_material_petg.sku,
                product_name=raw_material_petg.name,
                bom_level=0,
                gross_quantity=Decimal("3.0"),
            ),
        ]
        
        net_reqs = mrp_service.calculate_net_requirements(reqs)
        
        assert len(net_reqs) == 2
        
        # PLA: 2kg needed, 4kg available, 2kg safety = no shortage
        pla_net = next((n for n in net_reqs if n.product_sku == "MAT-PLA-BLK"), None)
        assert pla_net is not None
        assert pla_net.net_shortage == Decimal("0")
        
        # PETG: 3kg needed, 2kg available, 1kg safety = 2kg shortage
        petg_net = next((n for n in net_reqs if n.product_sku == "MAT-PETG-WHT"), None)
        assert petg_net is not None
        assert petg_net.net_shortage == Decimal("2.0")


# ============================================================================
# PLANNED ORDER GENERATION TESTS
# ============================================================================

class TestPlannedOrderGeneration:
    """Tests for planned order generation"""
    
    def test_generates_purchase_order_for_buy_item(self, db, mrp_service, raw_material_pla):
        """Test that buy items generate planned purchase orders"""
        from app.models.mrp import MRPRun
        
        # Create MRP run record first
        mrp_run = MRPRun(
            run_date=datetime.utcnow(),
            planning_horizon_days=30,
            status="running",
        )
        db.add(mrp_run)
        db.flush()
        
        shortage = NetRequirement(
            product_id=raw_material_pla.id,
            product_sku=raw_material_pla.sku,
            product_name=raw_material_pla.name,
            gross_quantity=Decimal("10"),
            on_hand_quantity=Decimal("0"),
            allocated_quantity=Decimal("0"),
            available_quantity=Decimal("0"),
            incoming_quantity=Decimal("0"),
            safety_stock=Decimal("2"),
            net_shortage=Decimal("12"),
            lead_time_days=7,
            item_type="supply",
        )
        
        planned_orders = mrp_service.generate_planned_orders([shortage], mrp_run.id)
        
        assert len(planned_orders) == 1
        po = planned_orders[0]
        assert po.order_type == "purchase"
        assert po.product_id == raw_material_pla.id
        assert po.quantity == Decimal("12")
        assert po.status == "planned"
    
    def test_generates_production_order_for_make_item(self, db, mrp_service, 
                                                       finished_product_simple):
        """Test that make items generate planned production orders"""
        from app.models.mrp import MRPRun
        
        mrp_run = MRPRun(
            run_date=datetime.utcnow(),
            planning_horizon_days=30,
            status="running",
        )
        db.add(mrp_run)
        db.flush()
        
        shortage = NetRequirement(
            product_id=finished_product_simple.id,
            product_sku=finished_product_simple.sku,
            product_name=finished_product_simple.name,
            gross_quantity=Decimal("20"),
            on_hand_quantity=Decimal("5"),
            allocated_quantity=Decimal("0"),
            available_quantity=Decimal("5"),
            incoming_quantity=Decimal("0"),
            safety_stock=Decimal("0"),
            net_shortage=Decimal("15"),
            lead_time_days=5,
            item_type="finished_good",
        )
        
        planned_orders = mrp_service.generate_planned_orders([shortage], mrp_run.id)
        
        assert len(planned_orders) == 1
        po = planned_orders[0]
        assert po.order_type == "production"  # Has BOM, so production
        assert po.product_id == finished_product_simple.id
        assert po.quantity == Decimal("15")
    
    def test_respects_minimum_order_quantity(self, db, mrp_service, packaging_box):
        """Test that planned orders respect minimum order quantities"""
        from app.models.mrp import MRPRun
        
        mrp_run = MRPRun(
            run_date=datetime.utcnow(),
            planning_horizon_days=30,
            status="running",
        )
        db.add(mrp_run)
        db.flush()
        
        # Need only 10 boxes, but min order qty is 100
        shortage = NetRequirement(
            product_id=packaging_box.id,
            product_sku=packaging_box.sku,
            product_name=packaging_box.name,
            gross_quantity=Decimal("10"),
            on_hand_quantity=Decimal("0"),
            allocated_quantity=Decimal("0"),
            available_quantity=Decimal("0"),
            incoming_quantity=Decimal("0"),
            safety_stock=Decimal("0"),
            net_shortage=Decimal("10"),
            lead_time_days=3,
            min_order_qty=Decimal("100"),  # Min 100 per order
            item_type="supply",
        )
        
        planned_orders = mrp_service.generate_planned_orders([shortage], mrp_run.id)
        
        assert len(planned_orders) == 1
        po = planned_orders[0]
        # Should order 100, not 10
        assert po.quantity == Decimal("100")
    
    def test_no_order_for_zero_shortage(self, db, mrp_service, raw_material_pla):
        """Test that no order is created when there's no shortage"""
        from app.models.mrp import MRPRun
        
        mrp_run = MRPRun(
            run_date=datetime.utcnow(),
            planning_horizon_days=30,
            status="running",
        )
        db.add(mrp_run)
        db.flush()
        
        # No shortage
        no_shortage = NetRequirement(
            product_id=raw_material_pla.id,
            product_sku=raw_material_pla.sku,
            product_name=raw_material_pla.name,
            gross_quantity=Decimal("5"),
            on_hand_quantity=Decimal("10"),
            allocated_quantity=Decimal("0"),
            available_quantity=Decimal("10"),
            incoming_quantity=Decimal("0"),
            safety_stock=Decimal("0"),
            net_shortage=Decimal("0"),
            lead_time_days=7,
            item_type="supply",
        )
        
        planned_orders = mrp_service.generate_planned_orders([no_shortage], mrp_run.id)
        
        assert len(planned_orders) == 0
    
    def test_calculates_dates_with_lead_time(self, db, mrp_service, hardware_insert):
        """Test that planned order dates account for lead time"""
        from app.models.mrp import MRPRun
        
        mrp_run = MRPRun(
            run_date=datetime.utcnow(),
            planning_horizon_days=30,
            status="running",
        )
        db.add(mrp_run)
        db.flush()
        
        shortage = NetRequirement(
            product_id=hardware_insert.id,
            product_sku=hardware_insert.sku,
            product_name=hardware_insert.name,
            gross_quantity=Decimal("100"),
            on_hand_quantity=Decimal("0"),
            allocated_quantity=Decimal("0"),
            available_quantity=Decimal("0"),
            incoming_quantity=Decimal("0"),
            safety_stock=Decimal("0"),
            net_shortage=Decimal("100"),
            lead_time_days=14,  # 14 day lead time
            min_order_qty=Decimal("500"),
            item_type="component",
        )
        
        planned_orders = mrp_service.generate_planned_orders([shortage], mrp_run.id)
        
        assert len(planned_orders) == 1
        po = planned_orders[0]
        
        # Due date should be ~2 weeks out (default)
        assert po.due_date >= date.today()
        
        # Start date should be lead_time days before due date
        # (unless that would be in the past)
        expected_start = po.due_date - timedelta(days=14)
        if expected_start < date.today():
            expected_start = date.today()
        assert po.start_date == expected_start


# ============================================================================
# INTEGRATION TESTS (FULL MRP RUN)
# ============================================================================

class TestFullMRPRun:
    """Integration tests for complete MRP runs"""
    
    def test_full_mrp_run_creates_planned_orders(self, db, mrp_service,
                                                  finished_product_multilevel,
                                                  inventory_with_stock,
                                                  inventory_location):
        """Test a complete MRP run with production orders generates planned orders"""
        from app.models.production_order import ProductionOrder
        
        # Create a production order for 10 gadgets
        prod_order = ProductionOrder(
            code="MO-TEST-001",
            product_id=finished_product_multilevel.id,
            quantity_ordered=Decimal("10"),
            quantity_completed=Decimal("0"),
            status="released",
            due_date=date.today() + timedelta(days=14),
            qc_status="not_required",  # Explicitly set to avoid SQLite schema issues
        )
        db.add(prod_order)
        db.commit()
        
        # Run MRP
        result = mrp_service.run_mrp(
            planning_horizon_days=30,
            include_draft_orders=True,
            regenerate_planned=True,
        )
        
        assert result.orders_processed >= 1
        assert result.components_analyzed > 0
        # Should have some shortages for components
        # (inventory may not cover demand for PETG, inserts, etc.)
        assert len(result.requirements) > 0


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling"""
    
    def test_empty_requirements_list(self, db, mrp_service):
        """Test handling of empty requirements"""
        net_reqs = mrp_service.calculate_net_requirements([])
        assert len(net_reqs) == 0
    
    def test_inactive_bom_not_exploded(self, db, mrp_service, finished_product_simple):
        """Test that inactive BOMs are not used in explosion"""
        from app.models.bom import BOM
        
        # Deactivate the BOM
        bom = db.query(BOM).filter(
            BOM.product_id == finished_product_simple.id
        ).first()
        bom.active = False
        db.commit()
        
        requirements = mrp_service.explode_bom(
            product_id=finished_product_simple.id,
            quantity=Decimal("10"),
        )
        
        # Should return empty since no active BOM
        assert len(requirements) == 0
    
    def test_zero_quantity_explosion(self, db, mrp_service, finished_product_simple):
        """Test BOM explosion with zero quantity"""
        requirements = mrp_service.explode_bom(
            product_id=finished_product_simple.id,
            quantity=Decimal("0"),
        )
        
        # Should return requirements with zero quantities
        for req in requirements:
            assert req.gross_quantity == Decimal("0")
    
    def test_decimal_precision_maintained(self, db, mrp_service, finished_product_simple):
        """Test that decimal precision is maintained in calculations"""
        requirements = mrp_service.explode_bom(
            product_id=finished_product_simple.id,
            quantity=Decimal("0.333"),
        )
        
        # Verify quantities are Decimal, not float
        for req in requirements:
            assert isinstance(req.gross_quantity, Decimal)


# ============================================================================
# UOM Conversion Tests
# ============================================================================

def test_convert_uom_basic_conversions():
    """Test basic UOM conversions"""
    # Mass conversions
    assert convert_uom(Decimal('1000'), 'G', 'KG') == Decimal('1')
    assert convert_uom(Decimal('1'), 'KG', 'G') == Decimal('1000')
    
    # Same unit
    assert convert_uom(Decimal('100'), 'KG', 'KG') == Decimal('100')
    
    # Volume conversions
    assert convert_uom(Decimal('1000'), 'ML', 'L') == Decimal('1')
    assert convert_uom(Decimal('1'), 'L', 'ML') == Decimal('1000')


def test_convert_uom_incompatible_bases():
    """Test conversion between incompatible unit bases returns original quantity"""
    # Cannot convert mass to volume
    result = convert_uom(Decimal('100'), 'KG', 'L')
    assert result == Decimal('100')  # Returns original quantity
    
    # Cannot convert count to mass
    result = convert_uom(Decimal('5'), 'EA', 'KG')
    assert result == Decimal('5')  # Returns original quantity


def test_convert_uom_unknown_units():
    """Test conversion with unknown units returns original quantity"""
    result = convert_uom(Decimal('100'), 'UNKNOWN', 'KG')
    assert result == Decimal('100')  # Returns original quantity
    
    result = convert_uom(Decimal('100'), 'KG', 'UNKNOWN')
    assert result == Decimal('100')  # Returns original quantity


def test_convert_uom_zero_factor_raises_error():
    """Test that zero conversion factor raises ValueError"""
    from app.services.mrp import UOM_CONVERSIONS
    
    # Temporarily add a UOM with zero factor to test the guard
    original_conversions = UOM_CONVERSIONS.copy()
    
    try:
        # Add invalid UOM with zero factor
        UOM_CONVERSIONS['ZERO_FROM'] = {'base': 'KG', 'factor': Decimal('0')}
        UOM_CONVERSIONS['ZERO_TO'] = {'base': 'KG', 'factor': Decimal('0')}
        
        # Test zero from_factor
        with pytest.raises(ValueError) as exc_info:
            convert_uom(Decimal('100'), 'ZERO_FROM', 'KG')
        assert 'Invalid UOM conversion factor' in str(exc_info.value)
        assert 'ZERO_FROM' in str(exc_info.value)
        assert 'factor is 0' in str(exc_info.value)
        
        # Test zero to_factor
        with pytest.raises(ValueError) as exc_info:
            convert_uom(Decimal('100'), 'KG', 'ZERO_TO')
        assert 'Invalid UOM conversion factor' in str(exc_info.value)
        assert 'ZERO_TO' in str(exc_info.value)
        assert 'factor is 0' in str(exc_info.value)
        
    finally:
        # Restore original conversions
        UOM_CONVERSIONS.clear()
        UOM_CONVERSIONS.update(original_conversions)


def test_convert_uom_none_factor_raises_error():
    """Test that None/missing conversion factor raises ValueError"""
    from app.services.mrp import UOM_CONVERSIONS
    
    # Temporarily add a UOM with missing factor to test the guard
    original_conversions = UOM_CONVERSIONS.copy()
    
    try:
        # Add invalid UOM with None factor
        UOM_CONVERSIONS['NONE_FACTOR'] = {'base': 'KG', 'factor': None}
        
        # Test None factor
        with pytest.raises(ValueError) as exc_info:
            convert_uom(Decimal('100'), 'NONE_FACTOR', 'KG')
        assert 'Invalid UOM conversion factor' in str(exc_info.value)
        assert 'NONE_FACTOR' in str(exc_info.value)
        
    finally:
        # Restore original conversions
        UOM_CONVERSIONS.clear()
        UOM_CONVERSIONS.update(original_conversions)
