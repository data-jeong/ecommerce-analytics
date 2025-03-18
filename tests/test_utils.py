import pytest
from datetime import datetime, timedelta
import json
from unittest.mock import patch, MagicMock

from api.utils import (
    validate_date_range,
    format_currency,
    calculate_percentage_change,
    parse_iso_datetime,
    generate_cache_key,
    retry_with_backoff,
    sanitize_input,
    mask_sensitive_data,
    validate_email,
    rate_limit_key
)

def test_validate_date_range():
    """Test date range validation."""
    # Valid date range
    start_date = datetime.now() - timedelta(days=30)
    end_date = datetime.now()
    assert validate_date_range(start_date, end_date) is True
    
    # Invalid date range (end before start)
    with pytest.raises(ValueError):
        validate_date_range(end_date, start_date)
    
    # Invalid date range (future dates)
    future_date = datetime.now() + timedelta(days=1)
    with pytest.raises(ValueError):
        validate_date_range(start_date, future_date)

def test_format_currency():
    """Test currency formatting."""
    assert format_currency(1234.5678) == "$1,234.57"
    assert format_currency(1234.5678, decimals=3) == "$1,234.568"
    assert format_currency(1234.5678, currency="€") == "€1,234.57"
    assert format_currency(0) == "$0.00"
    assert format_currency(-1234.56) == "-$1,234.56"

def test_calculate_percentage_change():
    """Test percentage change calculation."""
    assert calculate_percentage_change(100, 150) == 50.0
    assert calculate_percentage_change(150, 100) == -33.33
    assert calculate_percentage_change(100, 100) == 0.0
    assert calculate_percentage_change(0, 100) == float('inf')
    assert calculate_percentage_change(100, 0) == -100.0

def test_parse_iso_datetime():
    """Test ISO datetime parsing."""
    # Test valid ISO format
    dt_str = "2024-01-01T12:00:00Z"
    parsed = parse_iso_datetime(dt_str)
    assert isinstance(parsed, datetime)
    assert parsed.year == 2024
    assert parsed.month == 1
    assert parsed.day == 1
    
    # Test invalid format
    with pytest.raises(ValueError):
        parse_iso_datetime("invalid-date")
    
    # Test different ISO formats
    assert isinstance(parse_iso_datetime("2024-01-01"), datetime)
    assert isinstance(parse_iso_datetime("2024-01-01T12:00:00+00:00"), datetime)

def test_generate_cache_key():
    """Test cache key generation."""
    params = {
        "user_id": 123,
        "start_date": "2024-01-01",
        "end_date": "2024-01-31"
    }
    
    # Test basic key generation
    key1 = generate_cache_key("test_prefix", params)
    assert isinstance(key1, str)
    assert key1.startswith("test_prefix:")
    
    # Test consistency
    key2 = generate_cache_key("test_prefix", params)
    assert key1 == key2
    
    # Test different params produce different keys
    different_params = params.copy()
    different_params["user_id"] = 456
    different_key = generate_cache_key("test_prefix", different_params)
    assert different_key != key1

@patch('time.sleep')
def test_retry_with_backoff(mock_sleep):
    """Test retry with exponential backoff."""
    # Test successful execution
    @retry_with_backoff(max_retries=3, initial_delay=0.1)
    def success_func():
        return "success"
    
    assert success_func() == "success"
    assert mock_sleep.call_count == 0
    
    # Test retry on failure
    mock_func = MagicMock(side_effect=[ValueError, ValueError, "success"])
    
    @retry_with_backoff(max_retries=3, initial_delay=0.1)
    def failure_func():
        return mock_func()
    
    assert failure_func() == "success"
    assert mock_sleep.call_count == 2
    
    # Test max retries exceeded
    mock_func = MagicMock(side_effect=ValueError)
    
    @retry_with_backoff(max_retries=3, initial_delay=0.1)
    def max_retries_func():
        return mock_func()
    
    with pytest.raises(ValueError):
        max_retries_func()
    assert mock_sleep.call_count == 5  # 2 from previous test + 3 from this test

def test_sanitize_input():
    """Test input sanitization."""
    # Test SQL injection prevention
    assert "select" not in sanitize_input("SELECT * FROM users")
    assert "'" not in sanitize_input("user's input")
    
    # Test XSS prevention
    assert "<script>" not in sanitize_input("<script>alert('xss')</script>")
    
    # Test valid input remains unchanged
    assert sanitize_input("John Doe") == "John Doe"
    assert sanitize_input("user@example.com") == "user@example.com"

def test_mask_sensitive_data():
    """Test sensitive data masking."""
    data = {
        "user": {
            "email": "user@example.com",
            "password": "secret123",
            "credit_card": "4111111111111111",
            "name": "John Doe"
        }
    }
    
    masked = mask_sensitive_data(data)
    assert masked["user"]["email"] != "user@example.com"
    assert "***" in masked["user"]["email"]
    assert masked["user"]["password"] == "********"
    assert masked["user"]["credit_card"] == "************1111"
    assert masked["user"]["name"] == "John Doe"  # Non-sensitive data unchanged

def test_validate_email():
    """Test email validation."""
    # Valid email addresses
    assert validate_email("user@example.com") is True
    assert validate_email("user.name@example.co.uk") is True
    assert validate_email("user+tag@example.com") is True
    
    # Invalid email addresses
    assert validate_email("not-an-email") is False
    assert validate_email("@example.com") is False
    assert validate_email("user@") is False
    assert validate_email("user@.com") is False
    assert validate_email("") is False

def test_rate_limit_key():
    """Test rate limit key generation."""
    # Test with different inputs
    key1 = rate_limit_key("127.0.0.1", "/api/endpoint", "GET")
    key2 = rate_limit_key("127.0.0.1", "/api/endpoint", "POST")
    key3 = rate_limit_key("127.0.0.2", "/api/endpoint", "GET")
    
    # Verify keys are different
    assert len({key1, key2, key3}) == 3
    
    # Verify consistent results
    assert rate_limit_key("127.0.0.1", "/api/endpoint", "GET") == key1
    
    # Verify key format
    assert isinstance(key1, str)
    assert ":" in key1  # Common separator in rate limit keys 