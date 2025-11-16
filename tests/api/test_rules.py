"""Rules API tests."""

import pytest

from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.core.id_encryption import encrypt_email_id
from app.models.user_rule import RuleType, RuleAction


class TestRulesAPI:
    """Rules endpoint tests."""
    
    def test_create_rule_unauthorized(self, client: TestClient):
        """Test creating rule without authentication."""
        response = client.post("/api/v1/rules", json={})
        
        # FastAPI HTTPBearer returns 403 when no token is provided
        assert response.status_code in [401, 403]
    
    def test_create_similarity_rule_success(
        self,
        authenticated_client: TestClient,
        test_user,
        test_email
    ):
        """Test creating similarity-based rule."""
        encrypted_email_id = encrypt_email_id(test_email.id)
        
        rule_data = {
            "rule_name": "Test Similarity Rule",
            "description": "Test rule",
            "rule_type": "similarity_based",
            "action": "delete",
            "reference_email_id": test_email.id,
            "similarity_threshold": 0.8
        }
        
        response = authenticated_client.post("/api/v1/rules", json=rule_data)
        
        if response.status_code != 201:
            print(f"\n=== Response Status: {response.status_code} ===")
            print(f"Response Body: {response.json()}")
            print(f"Request Data: {rule_data}")
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.json()}"
        data = response.json()
        assert data["rule_name"] == rule_data["rule_name"]
        assert data["rule_type"] == rule_data["rule_type"]
        assert data["action"] == rule_data["action"]
    
    def test_create_similarity_rule_missing_fields(
        self,
        authenticated_client: TestClient,
        test_user
    ):
        """Test creating similarity rule without required fields."""
        rule_data = {
            "rule_name": "Test Rule",
            "rule_type": "similarity_based",
            "action": "delete"
            # Missing reference_email_id and similarity_threshold
        }
        
        response = authenticated_client.post("/api/v1/rules", json=rule_data)
        
        assert response.status_code == 400
    
    def test_create_metadata_rule_success(
        self,
        authenticated_client: TestClient,
        test_user
    ):
        """Test creating metadata-based rule."""
        rule_data = {
            "rule_name": "Test Metadata Rule",
            "rule_type": "metadata_based",
            "action": "archive",
            "sender_filter": "spam@example.com"
        }
        
        response = authenticated_client.post("/api/v1/rules", json=rule_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["rule_type"] == "metadata_based"
        assert data["sender_filter"] == rule_data["sender_filter"]
    
    def test_create_metadata_rule_no_filters(
        self,
        authenticated_client: TestClient,
        test_user
    ):
        """Test creating metadata rule without any filters."""
        rule_data = {
            "rule_name": "Test Rule",
            "rule_type": "metadata_based",
            "action": "delete"
            # No metadata filters
        }
        
        response = authenticated_client.post("/api/v1/rules", json=rule_data)
        
        assert response.status_code == 400
    
    def test_create_classification_rule_success(
        self,
        authenticated_client: TestClient,
        test_user
    ):
        """Test creating classification-based rule."""
        rule_data = {
            "rule_name": "Test Classification Rule",
            "rule_type": "classification_based",
            "action": "tag",
            "classification_category": "spam"
        }
        
        response = authenticated_client.post("/api/v1/rules", json=rule_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["rule_type"] == "classification_based"
        assert data["classification_category"] == "spam"
    
    def test_get_rules(
        self,
        authenticated_client: TestClient,
        test_user,
        test_user_rule
    ):
        """Test getting all rules."""
        response = authenticated_client.get("/api/v1/rules")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
    
    def test_get_rule_by_id(
        self,
        authenticated_client: TestClient,
        test_user,
        test_user_rule
    ):
        """Test getting rule by ID."""
        response = authenticated_client.get(f"/api/v1/rules/{test_user_rule.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user_rule.id
        assert data["rule_name"] == test_user_rule.rule_name
    
    def test_get_rule_not_found(
        self,
        authenticated_client: TestClient,
        test_user
    ):
        """Test getting non-existent rule."""
        response = authenticated_client.get("/api/v1/rules/99999")
        
        assert response.status_code == 404
    
    def test_update_rule(
        self,
        authenticated_client: TestClient,
        test_user,
        test_user_rule
    ):
        """Test updating rule."""
        update_data = {
            "rule_name": "Updated Rule Name",
            "is_active": False
        }
        
        response = authenticated_client.put(
            f"/api/v1/rules/{test_user_rule.id}",
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["rule_name"] == update_data["rule_name"]
        assert data["is_active"] == update_data["is_active"]
    
    def test_delete_rule(
        self,
        authenticated_client: TestClient,
        test_user,
        test_user_rule
    ):
        """Test deleting rule."""
        response = authenticated_client.delete(f"/api/v1/rules/{test_user_rule.id}")
        
        assert response.status_code == 204  # No Content
        
        # Verify rule is deleted
        get_response = authenticated_client.get(f"/api/v1/rules/{test_user_rule.id}")
        assert get_response.status_code == 404
    
    def test_create_rule_from_email(
        self,
        authenticated_client: TestClient,
        test_user,
        test_email
    ):
        """Test creating rule from email."""
        from app.core.id_encryption import encrypt_email_id
        
        encrypted_email_id = encrypt_email_id(test_email.id)
        
        request_data = {
            "rule_name": "Rule from Email",
            "action": "delete",
            "similarity_threshold": 0.7
        }
        
        response = authenticated_client.post(
            f"/api/v1/rules/from-email/{encrypted_email_id}",
            json=request_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["rule_type"] == "similarity_based"
        assert data["reference_email_id"] == test_email.id

