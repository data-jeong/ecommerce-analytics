import pytest
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta

from api.database import (
    get_db,
    Base,
    User,
    APIKey,
    AuditLog,
    RateLimit
)

def test_database_connection(test_db):
    """Test database connection and session creation."""
    assert test_db is not None
    # Test that we can execute a simple query
    result = test_db.execute("SELECT 1").scalar()
    assert result == 1

def test_create_tables(test_db):
    """Test table creation."""
    # Verify that all tables exist
    inspector = Base.metadata.inspector
    tables = inspector.get_table_names()
    
    assert "users" in tables
    assert "api_keys" in tables
    assert "audit_logs" in tables
    assert "rate_limits" in tables

def test_user_crud(test_db):
    """Test CRUD operations for User model."""
    # Create
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        full_name="Test User"
    )
    test_db.add(user)
    test_db.commit()
    
    # Read
    retrieved_user = test_db.query(User).filter_by(email="test@example.com").first()
    assert retrieved_user is not None
    assert retrieved_user.email == "test@example.com"
    assert retrieved_user.full_name == "Test User"
    
    # Update
    retrieved_user.full_name = "Updated Name"
    test_db.commit()
    updated_user = test_db.query(User).filter_by(email="test@example.com").first()
    assert updated_user.full_name == "Updated Name"
    
    # Delete
    test_db.delete(retrieved_user)
    test_db.commit()
    deleted_user = test_db.query(User).filter_by(email="test@example.com").first()
    assert deleted_user is None

def test_api_key_crud(test_db, test_user):
    """Test CRUD operations for APIKey model."""
    # Create
    api_key = APIKey(
        key="test_key_123",
        user_id=test_user.id,
        name="Test Key"
    )
    test_db.add(api_key)
    test_db.commit()
    
    # Read
    retrieved_key = test_db.query(APIKey).filter_by(key="test_key_123").first()
    assert retrieved_key is not None
    assert retrieved_key.user_id == test_user.id
    assert retrieved_key.name == "Test Key"
    
    # Update
    retrieved_key.name = "Updated Key Name"
    test_db.commit()
    updated_key = test_db.query(APIKey).filter_by(key="test_key_123").first()
    assert updated_key.name == "Updated Key Name"
    
    # Delete
    test_db.delete(retrieved_key)
    test_db.commit()
    deleted_key = test_db.query(APIKey).filter_by(key="test_key_123").first()
    assert deleted_key is None

def test_audit_log_crud(test_db, test_user):
    """Test CRUD operations for AuditLog model."""
    # Create
    log = AuditLog(
        user_id=test_user.id,
        action="test_action",
        resource_type="test_resource",
        resource_id="123",
        ip_address="127.0.0.1"
    )
    test_db.add(log)
    test_db.commit()
    
    # Read
    retrieved_log = test_db.query(AuditLog).filter_by(user_id=test_user.id).first()
    assert retrieved_log is not None
    assert retrieved_log.action == "test_action"
    assert retrieved_log.resource_type == "test_resource"
    
    # Verify created_at is set
    assert isinstance(retrieved_log.created_at, datetime)
    
    # Update (though audit logs typically shouldn't be updated)
    retrieved_log.ip_address = "127.0.0.2"
    test_db.commit()
    updated_log = test_db.query(AuditLog).filter_by(user_id=test_user.id).first()
    assert updated_log.ip_address == "127.0.0.2"

def test_rate_limit_crud(test_db, test_user):
    """Test CRUD operations for RateLimit model."""
    # Create
    rate_limit = RateLimit(
        user_id=test_user.id,
        endpoint="/api/test",
        requests_count=1,
        reset_at=datetime.now() + timedelta(hours=1)
    )
    test_db.add(rate_limit)
    test_db.commit()
    
    # Read
    retrieved_limit = test_db.query(RateLimit).filter_by(user_id=test_user.id).first()
    assert retrieved_limit is not None
    assert retrieved_limit.endpoint == "/api/test"
    assert retrieved_limit.requests_count == 1
    
    # Update
    retrieved_limit.requests_count += 1
    test_db.commit()
    updated_limit = test_db.query(RateLimit).filter_by(user_id=test_user.id).first()
    assert updated_limit.requests_count == 2
    
    # Delete
    test_db.delete(retrieved_limit)
    test_db.commit()
    deleted_limit = test_db.query(RateLimit).filter_by(user_id=test_user.id).first()
    assert deleted_limit is None

def test_unique_constraints(test_db):
    """Test unique constraints on models."""
    # Test unique email constraint
    user1 = User(
        email="unique@example.com",
        hashed_password="hashed_password",
        full_name="Test User 1"
    )
    test_db.add(user1)
    test_db.commit()
    
    user2 = User(
        email="unique@example.com",  # Same email
        hashed_password="hashed_password",
        full_name="Test User 2"
    )
    with pytest.raises(IntegrityError):
        test_db.add(user2)
        test_db.commit()
    test_db.rollback()

def test_cascade_delete(test_db, test_user):
    """Test cascade delete behavior."""
    # Create related records
    api_key = APIKey(key="cascade_test_key", user_id=test_user.id)
    audit_log = AuditLog(
        user_id=test_user.id,
        action="test_action",
        resource_type="test_resource"
    )
    rate_limit = RateLimit(
        user_id=test_user.id,
        endpoint="/api/test",
        requests_count=1
    )
    
    test_db.add_all([api_key, audit_log, rate_limit])
    test_db.commit()
    
    # Delete user and verify cascade
    test_db.delete(test_user)
    test_db.commit()
    
    # Verify related records are deleted
    assert test_db.query(APIKey).filter_by(user_id=test_user.id).first() is None
    assert test_db.query(AuditLog).filter_by(user_id=test_user.id).first() is None
    assert test_db.query(RateLimit).filter_by(user_id=test_user.id).first() is None

def test_timestamps(test_db, test_user):
    """Test automatic timestamp handling."""
    # Create a new user and verify created_at is set
    assert test_user.created_at is not None
    original_updated_at = test_user.updated_at
    
    # Update user and verify updated_at changes
    test_user.full_name = "Updated Name"
    test_db.commit()
    assert test_user.updated_at != original_updated_at 