# API Documentation

## Authentication

### Login

```http
POST /auth/token
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=userpassword
```

Response:

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

### Create API Key

```http
POST /api/v1/api-keys
Authorization: Bearer {token}
Content-Type: application/json

{
    "name": "My API Key",
    "expires_at": "2024-12-31T23:59:59Z"
}
```

Response:

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "key": "sk_test_123...",
  "name": "My API Key",
  "expires_at": "2024-12-31T23:59:59Z",
  "created_at": "2024-01-01T00:00:00Z"
}
```

## Analytics Endpoints

### Sales Summary

```http
GET /api/v1/sales/summary
Authorization: Bearer {token}
```

Query Parameters:

- `start_date` (optional): Start date in ISO format
- `end_date` (optional): End date in ISO format
- `granularity` (optional): daily|weekly|monthly (default: daily)

Response:

```json
{
  "total_sales": 1234567.89,
  "average_order_value": 123.45,
  "order_count": 1000,
  "time_series": [
    {
      "date": "2024-01-01",
      "sales": 12345.67,
      "orders": 100
    }
  ]
}
```

### Customer Cohorts

```http
GET /api/v1/customers/cohorts
Authorization: Bearer {token}
```

Query Parameters:

- `start_date` (optional): Start date in ISO format
- `end_date` (optional): End date in ISO format
- `cohort_size` (optional): Size of cohorts in days (default: 30)

Response:

```json
[
  {
    "cohort_date": "2024-01",
    "customer_count": 1000,
    "retention_rates": {
      "month_1": 0.8,
      "month_2": 0.6,
      "month_3": 0.4
    },
    "average_value": 234.56
  }
]
```

### Product Performance

```http
GET /api/v1/products/performance
Authorization: Bearer {token}
```

Query Parameters:

- `start_date` (optional): Start date in ISO format
- `end_date` (optional): End date in ISO format
- `category` (optional): Filter by product category
- `limit` (optional): Number of products to return (default: 100)

Response:

```json
[
  {
    "product_id": "123e4567-e89b-12d3-a456-426614174000",
    "category": "electronics",
    "revenue": 123456.78,
    "units_sold": 1000,
    "average_rating": 4.5,
    "return_rate": 0.02
  }
]
```

### Customer Lifetime Value

```http
GET /api/v1/customers/ltv
Authorization: Bearer {token}
```

Query Parameters:

- `segment` (optional): Customer segment filter
- `min_orders` (optional): Minimum number of orders
- `limit` (optional): Number of customers to return (default: 100)

Response:

```json
[
  {
    "customer_id": "123e4567-e89b-12d3-a456-426614174000",
    "ltv": 1234.56,
    "total_orders": 10,
    "average_order_value": 123.45,
    "first_order_date": "2024-01-01T00:00:00Z",
    "last_order_date": "2024-06-01T00:00:00Z"
  }
]
```

### Market Basket Analysis

```http
GET /api/v1/products/basket-analysis
Authorization: Bearer {token}
```

Query Parameters:

- `min_support` (optional): Minimum support value (default: 0.01)
- `min_confidence` (optional): Minimum confidence value (default: 0.5)
- `category` (optional): Filter by product category

Response:

```json
[
  {
    "antecedent": ["product_a", "product_b"],
    "consequent": ["product_c"],
    "support": 0.15,
    "confidence": 0.75,
    "lift": 2.5
  }
]
```

## Rate Limiting

The API implements rate limiting based on the following rules:

- Anonymous requests: 60 requests per hour
- Authenticated users: 1000 requests per hour
- API key users: Configurable limit (default: 10000 requests per hour)

Rate limit headers are included in all responses:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## Error Responses

The API uses standard HTTP status codes and returns error details in JSON format:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid date range specified",
    "details": {
      "start_date": "Must be before end_date",
      "end_date": "Must be after start_date"
    }
  }
}
```

Common error codes:

- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `422`: Validation Error
- `429`: Too Many Requests
- `500`: Internal Server Error

## Pagination

List endpoints support pagination using the following query parameters:

- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 100, max: 1000)

Response headers include pagination metadata:

```http
X-Total-Count: 1234
X-Page: 1
X-Per-Page: 100
X-Total-Pages: 13
```

## Filtering

Most endpoints support filtering using query parameters:

- Exact match: `field=value`
- Range: `field_min=value&field_max=value`
- Multiple values: `field=value1,value2`
- Pattern matching: `field_like=pattern`

Example:

```http
GET /api/v1/products/performance?category=electronics&price_min=100&price_max=1000
```

## Sorting

Use the `sort` and `order` parameters for sorting:

- `sort`: Field to sort by
- `order`: asc|desc (default: asc)

Example:

```http
GET /api/v1/products/performance?sort=revenue&order=desc
```

## Caching

The API implements caching using the following headers:

```http
Cache-Control: public, max-age=3600
ETag: "33a64df551425fcc55e4d42a148795d9f25f89d4"
```

Conditional requests are supported using:

- `If-None-Match`
- `If-Modified-Since`
