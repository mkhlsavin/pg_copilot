"""
Tests for Leads API endpoints.
"""

import pytest
from fastapi import status


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health check returns healthy status."""
        response = client.get("/api/v1/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "codegraph-leads"
        assert "version" in data


class TestLeadCreation:
    """Tests for lead creation endpoint."""

    def test_create_lead_success(self, client, sample_lead_data):
        """Test successful lead creation."""
        response = client.post("/api/v1/leads", json=sample_lead_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert "message" in data

    def test_create_lead_minimal_data(self, client):
        """Test lead creation with minimal required fields."""
        minimal_data = {
            "name": "Test",
            "email": "test@example.com",
            "company": "Company",
        }
        response = client.post("/api/v1/leads", json=minimal_data)

        assert response.status_code == status.HTTP_201_CREATED

    def test_create_lead_invalid_email(self, client):
        """Test lead creation with invalid email."""
        data = {
            "name": "Test",
            "email": "invalid-email",
            "company": "Company",
        }
        response = client.post("/api/v1/leads", json=data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_lead_missing_required_fields(self, client):
        """Test lead creation with missing required fields."""
        data = {"name": "Test"}
        response = client.post("/api/v1/leads", json=data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_lead_empty_name(self, client):
        """Test lead creation with empty name."""
        data = {
            "name": "",
            "email": "test@example.com",
            "company": "Company",
        }
        response = client.post("/api/v1/leads", json=data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestLeadListEndpoint:
    """Tests for lead listing endpoint."""

    def test_list_leads_requires_auth(self, client):
        """Test that list endpoint requires API key."""
        response = client.get("/api/v1/leads")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_leads_with_invalid_key(self, client):
        """Test list with invalid API key."""
        response = client.get(
            "/api/v1/leads",
            headers={"X-API-Key": "wrong-key"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_leads_with_valid_key(self, client, sample_lead_data):
        """Test list with valid API key."""
        # First create a lead
        client.post("/api/v1/leads", json=sample_lead_data)

        # Then list
        response = client.get(
            "/api/v1/leads",
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "pages" in data

    def test_list_leads_pagination(self, client, sample_lead_data):
        """Test list pagination."""
        # Create multiple leads
        for i in range(5):
            lead_data = sample_lead_data.copy()
            lead_data["email"] = f"test{i}@example.com"
            client.post("/api/v1/leads", json=lead_data)

        # Test pagination
        response = client.get(
            "/api/v1/leads",
            params={"page": 1, "page_size": 2},
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] >= 5


class TestLeadDetailEndpoint:
    """Tests for lead detail endpoint."""

    def test_get_lead_not_found(self, client):
        """Test getting non-existent lead."""
        response = client.get(
            "/api/v1/leads/00000000-0000-0000-0000-000000000000",
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_lead_success(self, client, sample_lead_data):
        """Test getting existing lead."""
        # Create lead
        create_response = client.post("/api/v1/leads", json=sample_lead_data)
        lead_id = create_response.json()["id"]

        # Get lead
        response = client.get(
            f"/api/v1/leads/{lead_id}",
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == lead_id
        assert data["name"] == sample_lead_data["name"]
        assert data["email"] == sample_lead_data["email"]


class TestLeadUpdateEndpoint:
    """Tests for lead update endpoint."""

    def test_update_lead_status(self, client, sample_lead_data):
        """Test updating lead status."""
        # Create lead
        create_response = client.post("/api/v1/leads", json=sample_lead_data)
        lead_id = create_response.json()["id"]

        # Update status
        response = client.patch(
            f"/api/v1/leads/{lead_id}",
            json={"status": "contacted"},
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "contacted"

    def test_update_lead_notes(self, client, sample_lead_data):
        """Test updating lead notes."""
        # Create lead
        create_response = client.post("/api/v1/leads", json=sample_lead_data)
        lead_id = create_response.json()["id"]

        # Update notes
        response = client.patch(
            f"/api/v1/leads/{lead_id}",
            json={"notes": "Called, scheduled demo"},
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["notes"] == "Called, scheduled demo"


class TestLeadDeleteEndpoint:
    """Tests for lead deletion endpoint."""

    def test_delete_lead_not_found(self, client):
        """Test deleting non-existent lead."""
        response = client.delete(
            "/api/v1/leads/00000000-0000-0000-0000-000000000000",
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_lead_success(self, client, sample_lead_data):
        """Test successful lead deletion."""
        # Create lead
        create_response = client.post("/api/v1/leads", json=sample_lead_data)
        lead_id = create_response.json()["id"]

        # Delete lead
        response = client.delete(
            f"/api/v1/leads/{lead_id}",
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify deletion
        get_response = client.get(
            f"/api/v1/leads/{lead_id}",
            headers={"X-API-Key": "test-api-key"},
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND


class TestStatsEndpoint:
    """Tests for statistics endpoint."""

    def test_get_stats(self, client, sample_lead_data):
        """Test getting statistics."""
        # Create some leads
        client.post("/api/v1/leads", json=sample_lead_data)

        response = client.get(
            "/api/v1/leads/stats",
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total" in data
        assert "by_status" in data
        assert "today" in data
        assert "this_week" in data
        assert "this_month" in data


class TestExportEndpoint:
    """Tests for export endpoint."""

    def test_export_leads_csv(self, client, sample_lead_data):
        """Test exporting leads to CSV."""
        # Create lead
        client.post("/api/v1/leads", json=sample_lead_data)

        response = client.get(
            "/api/v1/leads/export",
            headers={"X-API-Key": "test-api-key"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert "text/csv" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]

        # Verify CSV content
        content = response.text
        assert "ID,Name,Email" in content
        assert sample_lead_data["email"] in content
