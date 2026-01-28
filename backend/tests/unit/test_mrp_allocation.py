"""
Tests for MRP Per-Order Allocation Fix

These tests verify that the MRP calculation correctly handles:
- Scenario A: Single order's own allocation (no double-count)
- Scenario B: Multiple orders competing for materials (correct shortage)

The fix uses get_allocations_by_production_order() to track which PO owns
which allocations, then adjusts the available inventory accordingly.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch

from app.services.mrp import MRPService, ComponentRequirement
from app.services.inventory_service import get_allocations_by_production_order


class TestGetAllocationsByProductionOrder:
    """Tests for the get_allocations_by_production_order helper function."""

    def test_empty_product_ids_returns_empty_dict(self, db_session):
        """When no product IDs provided, returns empty dict."""
        result = get_allocations_by_production_order(db_session, [])
        assert result == {}

    def test_no_reservations_returns_empty_dict(self, db_session):
        """When no reservation transactions exist, returns empty dict."""
        # Use non-existent product IDs
        result = get_allocations_by_production_order(db_session, [999999, 999998])
        assert result == {}


class TestMRPCalculateNetRequirementsAllocation:
    """
    Tests for MRP calculate_net_requirements with per-order allocation handling.

    These are the CRITICAL tests that verify both scenarios work:
    - Scenario A: Own allocation doesn't double-count
    - Scenario B: Competing orders show correct shortage
    """

    @pytest.fixture
    def mock_mrp_service(self, db_session):
        """Create MRP service with mocked dependencies."""
        service = MRPService(db_session)
        return service

    def test_scenario_a_own_allocation_no_double_count(self, mock_mrp_service):
        """
        Scenario A: Single order's own allocation should NOT cause double-counting.

        Setup:
        - Product with 2000g on-hand
        - PO-001 needs 1000g, has already reserved 1000g
        - allocated_quantity = 1000g (for PO-001)

        Expected:
        - available = 2000 - 1000 = 1000g
        - BUT since PO-001's demand (1000g) is in gross, and PO-001's allocation
          is added back, effective available = 1000 + 1000 = 2000g
        - Net shortage = 1000 - 2000 = 0 (no shortage)
        """
        product_id = 1
        po_id = 101

        # Mock inventory levels
        with patch.object(mock_mrp_service, "_get_inventory_levels") as mock_inv:
            mock_inv.return_value = {
                product_id: {
                    "on_hand": Decimal("2000"),
                    "allocated": Decimal("1000"),  # Reserved for PO-001
                    "available": Decimal("1000"),  # on_hand - allocated
                }
            }

            # Mock incoming supply (none)
            with patch.object(mock_mrp_service, "_get_incoming_supply") as mock_supply:
                mock_supply.return_value = {}

                # Mock the allocations_by_production_order helper
                with patch("app.services.inventory_service.get_allocations_by_production_order") as mock_alloc:
                    # PO-001 has 1000g allocated for product_id 1
                    mock_alloc.return_value = {product_id: {po_id: Decimal("1000")}}

                    # Mock product query
                    mock_product = Mock()
                    mock_product.id = product_id
                    mock_product.safety_stock = 0
                    mock_product.lead_time_days = 7
                    mock_product.reorder_point = None
                    mock_product.min_order_qty = None
                    mock_product.has_bom = False
                    mock_product.standard_cost = Decimal("10")
                    mock_product.last_cost = Decimal("10")
                    mock_product.material_type_id = None
                    mock_product.unit = "G"

                    with patch.object(mock_mrp_service.db, "query") as mock_query:
                        mock_query.return_value.filter.return_value.all.return_value = [mock_product]

                        # Create requirement for PO-001
                        req = ComponentRequirement(
                            product_id=product_id,
                            product_sku="TEST-001",
                            product_name="Test Product",
                            bom_level=0,
                            gross_quantity=Decimal("1000"),  # PO-001 needs 1000g
                        )

                        # Calculate with source_production_order_ids including PO-001
                        result = mock_mrp_service.calculate_net_requirements([req], source_production_order_ids={po_id})

                        assert len(result) == 1
                        net_req = result[0]

                        # Key assertion: No shortage because PO-001's allocation is added back
                        assert net_req.net_shortage == Decimal(
                            "0"
                        ), f"Expected 0 shortage (own allocation added back), got {net_req.net_shortage}"

    def test_scenario_b_competing_orders_correct_shortage(self, mock_mrp_service):
        """
        Scenario B: Multiple orders competing for materials shows correct shortage.

        Setup:
        - Product with 10000g on-hand
        - PO-OTHER has reserved 9000g (other order, NOT in our calculation)
        - PO-NEW needs 1500g (no reservation yet, IS in our calculation)
        - allocated_quantity = 9000g (all for PO-OTHER)

        Expected:
        - available = 10000 - 9000 = 1000g
        - PO-NEW is in source_production_order_ids, but has NO allocation to add back
        - Net shortage = 1500 - 1000 = 500g shortage
        """
        product_id = 1
        po_other_id = 100  # NOT in our calculation
        po_new_id = 101  # IS in our calculation

        # Mock inventory levels
        with patch.object(mock_mrp_service, "_get_inventory_levels") as mock_inv:
            mock_inv.return_value = {
                product_id: {
                    "on_hand": Decimal("10000"),
                    "allocated": Decimal("9000"),  # Reserved for PO-OTHER
                    "available": Decimal("1000"),  # on_hand - allocated
                }
            }

            # Mock incoming supply (none)
            with patch.object(mock_mrp_service, "_get_incoming_supply") as mock_supply:
                mock_supply.return_value = {}

                # Mock the allocations_by_production_order helper
                with patch("app.services.inventory_service.get_allocations_by_production_order") as mock_alloc:
                    # PO-OTHER has 9000g allocated, PO-NEW has 0g
                    mock_alloc.return_value = {
                        product_id: {po_other_id: Decimal("9000")}
                        # Note: po_new_id is NOT in this dict - it has no allocation
                    }

                    # Mock product query
                    mock_product = Mock()
                    mock_product.id = product_id
                    mock_product.safety_stock = 0
                    mock_product.lead_time_days = 7
                    mock_product.reorder_point = None
                    mock_product.min_order_qty = None
                    mock_product.has_bom = False
                    mock_product.standard_cost = Decimal("10")
                    mock_product.last_cost = Decimal("10")
                    mock_product.material_type_id = None
                    mock_product.unit = "G"

                    with patch.object(mock_mrp_service.db, "query") as mock_query:
                        mock_query.return_value.filter.return_value.all.return_value = [mock_product]

                        # Create requirement for PO-NEW (1500g needed)
                        req = ComponentRequirement(
                            product_id=product_id,
                            product_sku="TEST-001",
                            product_name="Test Product",
                            bom_level=0,
                            gross_quantity=Decimal("1500"),  # PO-NEW needs 1500g
                        )

                        # Calculate with source_production_order_ids including only PO-NEW
                        # (PO-OTHER is not in our calculation)
                        result = mock_mrp_service.calculate_net_requirements(
                            [req], source_production_order_ids={po_new_id}
                        )

                        assert len(result) == 1
                        net_req = result[0]

                        # Key assertion: 500g shortage because only 1000g available
                        # PO-NEW has no allocation to add back
                        assert net_req.net_shortage == Decimal(
                            "500"
                        ), f"Expected 500g shortage, got {net_req.net_shortage}"

    def test_scenario_b_without_source_po_ids_uses_available(self, mock_mrp_service):
        """
        When no source_production_order_ids provided, use standard available calculation.

        This is the baseline behavior - allocations are subtracted from on_hand.
        """
        product_id = 1

        # Mock inventory levels
        with patch.object(mock_mrp_service, "_get_inventory_levels") as mock_inv:
            mock_inv.return_value = {
                product_id: {
                    "on_hand": Decimal("2000"),
                    "allocated": Decimal("500"),
                    "available": Decimal("1500"),
                }
            }

            # Mock incoming supply (none)
            with patch.object(mock_mrp_service, "_get_incoming_supply") as mock_supply:
                mock_supply.return_value = {}

                # Mock product query
                mock_product = Mock()
                mock_product.id = product_id
                mock_product.safety_stock = 0
                mock_product.lead_time_days = 7
                mock_product.reorder_point = None
                mock_product.min_order_qty = None
                mock_product.has_bom = False
                mock_product.standard_cost = Decimal("10")
                mock_product.last_cost = Decimal("10")
                mock_product.material_type_id = None
                mock_product.unit = "G"

                with patch.object(mock_mrp_service.db, "query") as mock_query:
                    mock_query.return_value.filter.return_value.all.return_value = [mock_product]

                    req = ComponentRequirement(
                        product_id=product_id,
                        product_sku="TEST-001",
                        product_name="Test Product",
                        bom_level=0,
                        gross_quantity=Decimal("2000"),  # Need 2000g
                    )

                    # Calculate WITHOUT source_production_order_ids
                    result = mock_mrp_service.calculate_net_requirements([req])

                    assert len(result) == 1
                    net_req = result[0]

                    # Standard calculation: 2000 - 1500 = 500g shortage
                    assert net_req.net_shortage == Decimal(
                        "500"
                    ), f"Expected 500g shortage (standard calculation), got {net_req.net_shortage}"

    def test_empty_requirements_returns_empty_list(self, mock_mrp_service):
        """When no requirements provided, returns empty list."""
        result = mock_mrp_service.calculate_net_requirements([])
        assert result == []

    def test_multiple_products_with_allocations(self, mock_mrp_service):
        """Test handling multiple products with different allocation scenarios."""
        product_a_id = 1
        product_b_id = 2
        po_id = 101

        # Mock inventory levels for both products
        with patch.object(mock_mrp_service, "_get_inventory_levels") as mock_inv:
            mock_inv.return_value = {
                product_a_id: {
                    "on_hand": Decimal("1000"),
                    "allocated": Decimal("500"),  # PO-101 has 500
                    "available": Decimal("500"),
                },
                product_b_id: {
                    "on_hand": Decimal("2000"),
                    "allocated": Decimal("0"),  # No allocations
                    "available": Decimal("2000"),
                },
            }

            with patch.object(mock_mrp_service, "_get_incoming_supply") as mock_supply:
                mock_supply.return_value = {}

                with patch("app.services.inventory_service.get_allocations_by_production_order") as mock_alloc:
                    mock_alloc.return_value = {
                        product_a_id: {po_id: Decimal("500")}
                        # product_b has no allocations
                    }

                    mock_product_a = Mock()
                    mock_product_a.id = product_a_id
                    mock_product_a.safety_stock = 0
                    mock_product_a.lead_time_days = 7
                    mock_product_a.reorder_point = None
                    mock_product_a.min_order_qty = None
                    mock_product_a.has_bom = False
                    mock_product_a.standard_cost = Decimal("10")
                    mock_product_a.last_cost = Decimal("10")
                    mock_product_a.material_type_id = None
                    mock_product_a.unit = "G"

                    mock_product_b = Mock()
                    mock_product_b.id = product_b_id
                    mock_product_b.safety_stock = 0
                    mock_product_b.lead_time_days = 7
                    mock_product_b.reorder_point = None
                    mock_product_b.min_order_qty = None
                    mock_product_b.has_bom = False
                    mock_product_b.standard_cost = Decimal("10")
                    mock_product_b.last_cost = Decimal("10")
                    mock_product_b.material_type_id = None
                    mock_product_b.unit = "G"

                    with patch.object(mock_mrp_service.db, "query") as mock_query:
                        mock_query.return_value.filter.return_value.all.return_value = [mock_product_a, mock_product_b]

                        reqs = [
                            ComponentRequirement(
                                product_id=product_a_id,
                                product_sku="A",
                                product_name="Product A",
                                bom_level=0,
                                gross_quantity=Decimal("800"),
                            ),
                            ComponentRequirement(
                                product_id=product_b_id,
                                product_sku="B",
                                product_name="Product B",
                                bom_level=0,
                                gross_quantity=Decimal("1500"),
                            ),
                        ]

                        result = mock_mrp_service.calculate_net_requirements(reqs, source_production_order_ids={po_id})

                        assert len(result) == 2

                        # Product A: available=500, add back 500 for PO-101 = 1000
                        # Need 800, have 1000, shortage = 0
                        a_result = next(r for r in result if r.product_id == product_a_id)
                        assert a_result.net_shortage == Decimal(
                            "0"
                        ), f"Product A expected 0 shortage, got {a_result.net_shortage}"

                        # Product B: available=2000, no allocation to add back
                        # Need 1500, have 2000, shortage = 0
                        b_result = next(r for r in result if r.product_id == product_b_id)
                        assert b_result.net_shortage == Decimal(
                            "0"
                        ), f"Product B expected 0 shortage, got {b_result.net_shortage}"
