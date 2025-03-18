# Contributing Guide

## Getting Started

### Development Environment Setup

1. **Fork and Clone**:

```bash
# Fork the repository on GitHub
git clone https://github.com/yourusername/ecommerce-analytics.git
cd ecommerce-analytics
```

2. **Create Virtual Environment**:

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
.\venv\Scripts\activate   # Windows
```

3. **Install Dependencies**:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

4. **Set Up Pre-commit Hooks**:

```bash
pre-commit install
```

### Development Workflow

1. **Create Feature Branch**:

```bash
git checkout -b feature/your-feature-name
```

2. **Make Changes**:

- Write code following the style guide
- Add tests for new functionality
- Update documentation as needed

3. **Run Tests**:

```bash
# Run all tests
make test

# Run specific test categories
make test-unit
make test-integration
make test-e2e
```

4. **Check Code Quality**:

```bash
# Run linting
make lint

# Run type checking
make typecheck

# Run security checks
make security-check
```

## Code Style Guide

### Python Style Guide

1. **Code Formatting**:

- Use Black for code formatting
- Maximum line length: 88 characters
- Use double quotes for strings
- Use trailing commas in multi-line structures

2. **Naming Conventions**:

```python
# Classes: PascalCase
class CustomerAnalytics:
    pass

# Functions and variables: snake_case
def calculate_metrics():
    customer_count = 0

# Constants: UPPER_CASE
MAX_RETRY_COUNT = 3

# Private methods/variables: _leading_underscore
def _internal_helper():
    pass
```

3. **Type Hints**:

```python
from typing import List, Dict, Optional

def process_orders(
    orders: List[Dict[str, any]],
    customer_id: Optional[str] = None
) -> Dict[str, float]:
    """
    Process orders and return metrics.

    Args:
        orders: List of order dictionaries
        customer_id: Optional customer ID filter

    Returns:
        Dictionary containing order metrics
    """
    pass
```

### SQL Style Guide

1. **Query Formatting**:

```sql
-- Use UPPER CASE for SQL keywords
SELECT
    customer_id,
    COUNT(DISTINCT order_id) as total_orders,
    SUM(price) as total_spent
FROM
    orders
WHERE
    status = 'completed'
GROUP BY
    customer_id
HAVING
    COUNT(DISTINCT order_id) > 1
ORDER BY
    total_spent DESC;
```

2. **Naming Conventions**:

```sql
-- Tables: plural nouns
CREATE TABLE customers (
    -- Primary keys: id
    id UUID PRIMARY KEY,
    -- Foreign keys: entity_id
    organization_id UUID REFERENCES organizations(id),
    -- Timestamps: _at suffix
    created_at TIMESTAMP WITH TIME ZONE
);

-- Indexes: ix_table_columns
CREATE INDEX ix_customers_email ON customers(email);

-- Views: entity_view
CREATE VIEW customer_metrics_view AS
SELECT ...;
```

## Testing Guidelines

### Unit Tests

1. **Test Structure**:

```python
import pytest
from unittest.mock import Mock, patch

def test_customer_metrics_calculation():
    # Arrange
    test_data = [
        {"customer_id": "1", "amount": 100},
        {"customer_id": "1", "amount": 200},
    ]

    # Act
    result = calculate_customer_metrics(test_data)

    # Assert
    assert result["total_spent"] == 300
    assert result["average_order"] == 150

@pytest.mark.asyncio
async def test_async_function():
    # Test async functions
    result = await process_async_task()
    assert result is not None

@pytest.mark.parametrize("input,expected", [
    (100, True),
    (0, False),
    (-1, False),
])
def test_validate_amount(input, expected):
    # Parametrized test
    assert validate_amount(input) == expected
```

2. **Mocking**:

```python
@patch('module.redis_client')
def test_cached_function(mock_redis):
    # Configure mock
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True

    # Test function
    result = get_cached_value('key')

    # Verify mock calls
    mock_redis.get.assert_called_once_with('key')
```

### Integration Tests

1. **Database Tests**:

```python
@pytest.mark.integration
async def test_database_operations(test_db):
    # Create test data
    customer = Customer(name="Test User")
    await test_db.add(customer)
    await test_db.commit()

    # Query and verify
    result = await test_db.query(Customer).first()
    assert result.name == "Test User"
```

2. **API Tests**:

```python
from fastapi.testclient import TestClient

def test_api_endpoint(test_client: TestClient):
    response = test_client.get("/api/v1/metrics")
    assert response.status_code == 200
    assert "data" in response.json()
```

## Documentation Standards

### Code Documentation

1. **Function Docstrings**:

```python
def calculate_customer_ltv(
    transactions: List[Dict],
    timeframe_days: int = 365
) -> float:
    """
    Calculate Customer Lifetime Value based on transaction history.

    Args:
        transactions: List of transaction dictionaries containing:
            - amount: Transaction amount
            - date: Transaction date
        timeframe_days: Number of days to consider (default: 365)

    Returns:
        float: Calculated LTV value

    Raises:
        ValueError: If transactions list is empty
        TypeError: If transaction format is invalid
    """
    pass
```

2. **Class Documentation**:

```python
class AnalyticsProcessor:
    """
    Process analytics data and generate metrics.

    This class handles the processing of raw analytics data
    and generates various metrics for reporting.

    Attributes:
        batch_size (int): Size of processing batches
        cache_ttl (int): Cache TTL in seconds

    Example:
        processor = AnalyticsProcessor(batch_size=1000)
        metrics = await processor.process_data(data)
    """
```

### API Documentation

1. **OpenAPI/Swagger**:

```python
from fastapi import APIRouter, Query

router = APIRouter()

@router.get("/metrics")
async def get_metrics(
    start_date: str = Query(
        ...,
        description="Start date in YYYY-MM-DD format",
        example="2024-01-01"
    ),
    end_date: str = Query(
        ...,
        description="End date in YYYY-MM-DD format",
        example="2024-12-31"
    )
) -> Dict[str, Any]:
    """
    Get analytics metrics for a date range.

    This endpoint returns various analytics metrics calculated
    for the specified date range.

    Args:
        start_date: Start date of the analysis period
        end_date: End date of the analysis period

    Returns:
        Dictionary containing:
        - total_revenue: Total revenue in the period
        - order_count: Number of orders
        - average_order_value: Average order value
    """
    pass
```

## Pull Request Process

### PR Guidelines

1. **PR Template**:

```markdown
## Description

Brief description of the changes

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Tested manually

## Checklist

- [ ] Code follows style guide
- [ ] Documentation updated
- [ ] Tests passing
- [ ] PR is linked to issue
```

2. **Review Process**:

- At least one approval required
- All tests must pass
- Code coverage must not decrease
- No merge conflicts

### Release Process

1. **Version Bumping**:

```bash
# Update version in setup.py
# Update CHANGELOG.md
git add setup.py CHANGELOG.md
git commit -m "Bump version to X.Y.Z"
git tag vX.Y.Z
git push origin main --tags
```

2. **Release Notes**:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added

- New feature A
- New feature B

### Changed

- Updated dependency X
- Modified behavior of Y

### Fixed

- Bug in feature Z
- Performance issue in W
```

## Security Guidelines

### Security Best Practices

1. **Code Security**:

- No hardcoded secrets
- Input validation
- Output encoding
- Secure dependencies

2. **Data Security**:

- Encrypt sensitive data
- Use parameterized queries
- Implement rate limiting
- Follow least privilege principle

### Reporting Security Issues

1. **Responsible Disclosure**:

- Email security@example.com
- Include detailed description
- Provide reproduction steps
- Allow time for fixes

## Community Guidelines

### Communication

1. **Channels**:

- GitHub Issues for bugs/features
- Discussions for questions
- Wiki for documentation
- Slack for real-time chat

2. **Code of Conduct**:

- Be respectful and inclusive
- Focus on constructive feedback
- Follow project guidelines
- Help others learn and grow
