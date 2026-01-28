"""
Integration tests for Accounting Export endpoints

Tests the tax time sales export functionality
"""

from datetime import datetime, timedelta
from io import StringIO
import csv


class TestSalesExport:
    """Test sales export endpoint for tax time"""

    def test_sales_export_requires_authentication(self, client):
        """Test that sales export returns 401 without auth"""
        response = client.get(
            "/api/v1/admin/accounting/export/sales", params={"start_date": "2025-01-01", "end_date": "2025-12-31"}
        )
        assert response.status_code == 401

    def test_sales_export_requires_admin_role(self, client, customer_headers):
        """Test that sales export returns 403 for non-admin users"""
        response = client.get(
            "/api/v1/admin/accounting/export/sales",
            params={"start_date": "2025-01-01", "end_date": "2025-12-31"},
            headers=customer_headers,
        )
        assert response.status_code == 403

    def test_sales_export_requires_start_date(self, client, admin_headers):
        """Test that sales export requires start_date parameter"""
        response = client.get(
            "/api/v1/admin/accounting/export/sales", params={"end_date": "2025-12-31"}, headers=admin_headers
        )
        assert response.status_code == 422  # Validation error

    def test_sales_export_requires_end_date(self, client, admin_headers):
        """Test that sales export requires end_date parameter"""
        response = client.get(
            "/api/v1/admin/accounting/export/sales", params={"start_date": "2025-01-01"}, headers=admin_headers
        )
        assert response.status_code == 422  # Validation error

    def test_sales_export_returns_csv(self, client, admin_headers):
        """Test that sales export returns CSV format"""
        today = datetime.now().date()
        start_date = (today - timedelta(days=365)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")

        response = client.get(
            "/api/v1/admin/accounting/export/sales",
            params={"start_date": start_date, "end_date": end_date, "format": "csv"},
            headers=admin_headers,
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "Content-Disposition" in response.headers
        assert "sales_export_" in response.headers["Content-Disposition"]

    def test_sales_export_csv_structure(self, client, admin_headers, sample_sales_order):
        """Test that sales export CSV has correct structure"""
        today = datetime.now().date()
        start_date = (today - timedelta(days=365)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")

        response = client.get(
            "/api/v1/admin/accounting/export/sales",
            params={"start_date": start_date, "end_date": end_date},
            headers=admin_headers,
        )

        assert response.status_code == 200

        # Parse CSV - skip disclaimer header lines (lines starting with # or "# when quoted)
        csv_content = response.text
        lines = csv_content.strip().split("\n")
        data_lines = [line for line in lines if not line.lstrip('"').startswith("#") and line.strip()]
        filtered_content = "\n".join(data_lines)
        csv_reader = csv.DictReader(StringIO(filtered_content))

        # Check headers
        expected_headers = [
            "Order Number",
            "Order Date",
            "Customer Name",
            "Subtotal",
            "Tax Amount",
            "Shipping",
            "Total",
            "Status",
            "Payment Status",
        ]

        assert csv_reader.fieldnames == expected_headers

        # Check that we have at least one row (from the sample order)
        rows = list(csv_reader)
        assert len(rows) >= 1

        # Verify first row has expected fields
        first_row = rows[0]
        assert "Order Number" in csv_reader.fieldnames
        assert first_row["Order Number"]  # Should have a value

    def test_sales_export_date_filtering(self, client, admin_headers, sample_sales_order):
        """Test that date filtering works correctly"""
        # Test with a future date range (should return no results)
        future_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")

        response = client.get(
            "/api/v1/admin/accounting/export/sales",
            params={"start_date": future_date, "end_date": future_date},
            headers=admin_headers,
        )

        assert response.status_code == 200

        # Parse CSV - skip disclaimer headers, check only data header row exists (no data rows)
        csv_content = response.text
        lines = csv_content.strip().split("\n")
        data_lines = [line for line in lines if not line.lstrip('"').startswith("#") and line.strip()]
        # Should only have header row (no data rows)
        assert len(data_lines) == 1

    def test_sales_export_format_parameter_optional(self, client, admin_headers):
        """Test that format parameter is optional and defaults to csv"""
        today = datetime.now().date()
        start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")

        response = client.get(
            "/api/v1/admin/accounting/export/sales",
            params={
                "start_date": start_date,
                "end_date": end_date,
                # format not provided - should default to "csv"
            },
            headers=admin_headers,
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"

    def test_sales_export_includes_disclaimer(self, client, admin_headers):
        """Test that sales export includes compliance disclaimer header"""
        today = datetime.now().date()
        start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")

        response = client.get(
            "/api/v1/admin/accounting/export/sales",
            params={"start_date": start_date, "end_date": end_date},
            headers=admin_headers,
        )

        assert response.status_code == 200
        csv_content = response.text

        # Verify disclaimer is present
        assert "For Reference Only" in csv_content
        assert "qualified accountant" in csv_content
        assert "tax filings" in csv_content
