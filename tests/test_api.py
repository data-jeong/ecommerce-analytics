from datetime import datetime, timedelta
import pytest
from fastapi import status

def test_health_check(test_client):
    """Test the health check endpoint."""
    response = test_client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "healthy"}

def test_login(test_client, test_user):
    """Test the login endpoint."""
    # Test valid login
    response = test_client.post(
        "/auth/token",
        data={
            "username": "test@example.com",
            "password": "testpassword"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"
    
    # Test invalid password
    response = test_client.post(
        "/auth/token",
        data={
            "username": "test@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    # Test non-existent user
    response = test_client.post(
        "/auth/token",
        data={
            "username": "nonexistent@example.com",
            "password": "testpassword"
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_protected_endpoints(test_client, auth_headers):
    """Test protected endpoints require authentication."""
    # Test without auth headers
    response = test_client.get("/api/v1/sales/summary")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    # Test with auth headers
    response = test_client.get("/api/v1/sales/summary", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK

def test_sales_summary(test_client, auth_headers):
    """Test sales summary endpoint."""
    # Test default parameters
    response = test_client.get("/api/v1/sales/summary", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "total_sales" in data
    assert "average_order_value" in data
    assert "order_count" in data
    
    # Test with date range
    response = test_client.get(
        "/api/v1/sales/summary",
        params={
            "start_date": (datetime.now() - timedelta(days=30)).date().isoformat(),
            "end_date": datetime.now().date().isoformat()
        },
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK

def test_customer_cohorts(test_client, auth_headers):
    """Test customer cohorts endpoint."""
    response = test_client.get("/api/v1/customers/cohorts", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "cohort_date" in data[0]
        assert "customer_count" in data[0]
        assert "retention_rates" in data[0]

def test_product_performance(test_client, auth_headers):
    """Test product performance endpoint."""
    response = test_client.get("/api/v1/products/performance", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "product_id" in data[0]
        assert "revenue" in data[0]
        assert "units_sold" in data[0]

def test_seller_analytics(test_client, auth_headers):
    """Test seller analytics endpoint."""
    response = test_client.get("/api/v1/sellers/analytics", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "seller_id" in data[0]
        assert "total_sales" in data[0]
        assert "order_count" in data[0]

def test_rate_limiting(test_client, auth_headers):
    """Test rate limiting functionality."""
    # Make multiple requests in quick succession
    for _ in range(5):
        response = test_client.get("/api/v1/sales/summary", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
    
    # The next request should be rate limited
    response = test_client.get("/api/v1/sales/summary", headers=auth_headers)
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

def test_error_handling(test_client, auth_headers):
    """Test error handling for invalid parameters."""
    # Test invalid date format
    response = test_client.get(
        "/api/v1/sales/summary",
        params={"start_date": "invalid-date"},
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    # Test invalid date range
    response = test_client.get(
        "/api/v1/sales/summary",
        params={
            "start_date": "2024-01-01",
            "end_date": "2023-01-01"  # End date before start date
        },
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST 