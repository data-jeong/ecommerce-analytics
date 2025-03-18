import pytest
from fastapi import HTTPException
from datetime import datetime, timedelta

from api.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    authenticate_user,
    get_user,
    create_user,
    update_user_password,
    deactivate_user
)

def test_password_hashing():
    """Test password hashing and verification."""
    password = "testpassword123"
    hashed = get_password_hash(password)
    
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)

def test_create_access_token():
    """Test JWT token creation."""
    data = {"sub": "test@example.com"}
    token = create_access_token(data)
    assert isinstance(token, str)
    
    # Test with expiration
    expires = timedelta(minutes=30)
    token = create_access_token(data, expires_delta=expires)
    assert isinstance(token, str)

def test_authenticate_user(test_db, test_user):
    """Test user authentication."""
    # Test valid credentials
    user = authenticate_user(test_db, "test@example.com", "testpassword")
    assert user is not None
    assert user.email == "test@example.com"
    
    # Test invalid password
    user = authenticate_user(test_db, "test@example.com", "wrongpassword")
    assert user is None
    
    # Test non-existent user
    user = authenticate_user(test_db, "nonexistent@example.com", "testpassword")
    assert user is None

def test_get_user(test_db, test_user):
    """Test getting user by username."""
    user = get_user(test_db, "test@example.com")
    assert user is not None
    assert user.email == "test@example.com"
    
    user = get_user(test_db, "nonexistent@example.com")
    assert user is None

def test_create_user(test_db):
    """Test user creation."""
    user = create_user(
        test_db,
        email="newuser@example.com",
        password="newpassword",
        full_name="New User"
    )
    assert user is not None
    assert user.email == "newuser@example.com"
    assert user.full_name == "New User"
    assert not user.is_superuser
    
    # Test creating superuser
    admin = create_user(
        test_db,
        email="admin@example.com",
        password="adminpass",
        full_name="Admin User",
        is_superuser=True
    )
    assert admin.is_superuser

def test_update_user_password(test_db, test_user):
    """Test password update."""
    new_password = "newpassword123"
    success = update_user_password(test_db, test_user.id, new_password)
    assert success
    
    # Verify new password works
    user = authenticate_user(test_db, test_user.email, new_password)
    assert user is not None

def test_deactivate_user(test_db, test_user):
    """Test user deactivation."""
    success = deactivate_user(test_db, test_user.id)
    assert success
    
    # Verify user is deactivated
    user = get_user(test_db, test_user.email)
    assert not user.is_active

def test_duplicate_email(test_db, test_user):
    """Test creating user with duplicate email."""
    with pytest.raises(Exception):  # SQLAlchemy will raise an integrity error
        create_user(
            test_db,
            email="test@example.com",  # Same as test_user
            password="password123",
            full_name="Another User"
        ) 