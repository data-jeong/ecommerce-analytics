# Database Schema Documentation

## OLTP Database (PostgreSQL)

### Core Tables

#### Users

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_superuser BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX ix_users_email ON users(email);
```

#### API Keys

```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    last_used_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX ix_api_keys_user_id ON api_keys(user_id);
```

#### Audit Logs

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(255),
    details JSONB,
    ip_address VARCHAR(45),
    user_agent VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX ix_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX ix_audit_logs_created_at ON audit_logs(created_at);
```

#### Rate Limits

```sql
CREATE TABLE rate_limits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    api_key_id UUID REFERENCES api_keys(id) ON DELETE CASCADE,
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    requests_count INTEGER NOT NULL DEFAULT 0,
    window_start TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX ix_rate_limits_user_id ON rate_limits(user_id);
CREATE INDEX ix_rate_limits_api_key_id ON rate_limits(api_key_id);
CREATE INDEX ix_rate_limits_window_start ON rate_limits(window_start);
```

### Olist Data Tables

#### Customers

```sql
CREATE TABLE customers (
    customer_id UUID PRIMARY KEY,
    customer_unique_id UUID NOT NULL,
    customer_zip_code VARCHAR(10) NOT NULL,
    customer_city VARCHAR(100) NOT NULL,
    customer_state CHAR(2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX ix_customers_customer_unique_id ON customers(customer_unique_id);
CREATE INDEX ix_customers_customer_state ON customers(customer_state);
```

#### Orders

```sql
CREATE TABLE orders (
    order_id UUID PRIMARY KEY,
    customer_id UUID NOT NULL REFERENCES customers(customer_id),
    order_status VARCHAR(20) NOT NULL,
    order_purchase_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    order_approved_at TIMESTAMP WITH TIME ZONE,
    order_delivered_carrier_date TIMESTAMP WITH TIME ZONE,
    order_delivered_customer_date TIMESTAMP WITH TIME ZONE,
    order_estimated_delivery_date TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX ix_orders_customer_id ON orders(customer_id);
CREATE INDEX ix_orders_order_purchase_timestamp ON orders(order_purchase_timestamp);
CREATE INDEX ix_orders_order_status ON orders(order_status);
```

#### Products

```sql
CREATE TABLE products (
    product_id UUID PRIMARY KEY,
    product_category_name VARCHAR(100),
    product_name_length INTEGER,
    product_description_length INTEGER,
    product_photos_qty INTEGER,
    product_weight_g INTEGER,
    product_length_cm INTEGER,
    product_height_cm INTEGER,
    product_width_cm INTEGER
);

CREATE INDEX ix_products_product_category_name ON products(product_category_name);
```

#### Order Items

```sql
CREATE TABLE order_items (
    order_id UUID NOT NULL REFERENCES orders(order_id),
    order_item_id INTEGER NOT NULL,
    product_id UUID NOT NULL REFERENCES products(product_id),
    seller_id UUID NOT NULL,
    shipping_limit_date TIMESTAMP WITH TIME ZONE NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    freight_value DECIMAL(10,2) NOT NULL,
    PRIMARY KEY (order_id, order_item_id)
);

CREATE INDEX ix_order_items_product_id ON order_items(product_id);
CREATE INDEX ix_order_items_seller_id ON order_items(seller_id);
```

## OLAP Database (PostgreSQL)

### Analytical Views

#### Customer Analytics

```sql
CREATE MATERIALIZED VIEW customer_analytics AS
SELECT
    c.customer_id,
    c.customer_state,
    COUNT(DISTINCT o.order_id) as total_orders,
    SUM(oi.price) as total_spent,
    AVG(oi.price) as avg_order_value,
    MIN(o.order_purchase_timestamp) as first_purchase,
    MAX(o.order_purchase_timestamp) as last_purchase,
    COUNT(DISTINCT p.product_category_name) as unique_categories_bought
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
LEFT JOIN order_items oi ON o.order_id = oi.order_id
LEFT JOIN products p ON oi.product_id = p.product_id
GROUP BY c.customer_id, c.customer_state;

CREATE UNIQUE INDEX ix_customer_analytics_customer_id ON customer_analytics(customer_id);
```

#### Product Performance

```sql
CREATE MATERIALIZED VIEW product_performance AS
SELECT
    p.product_id,
    p.product_category_name,
    COUNT(DISTINCT oi.order_id) as total_orders,
    SUM(oi.price) as total_revenue,
    AVG(oi.price) as avg_price,
    SUM(oi.freight_value) as total_freight,
    COUNT(DISTINCT o.customer_id) as unique_customers
FROM products p
LEFT JOIN order_items oi ON p.product_id = oi.product_id
LEFT JOIN orders o ON oi.order_id = o.order_id
GROUP BY p.product_id, p.product_category_name;

CREATE UNIQUE INDEX ix_product_performance_product_id ON product_performance(product_id);
```

## Caching Layer (Redis)

### Key Patterns

- User Sessions: `session:{user_id}`
- API Rate Limits: `rate_limit:{api_key}:{endpoint}`
- Cache Keys: `cache:{entity}:{id}`
- Analytics Cache: `analytics:{metric}:{parameters}`

### TTL Settings

- User Sessions: 24 hours
- Rate Limits: 1 hour
- Cache Keys: 1 hour
- Analytics Cache: 6 hours

## Document Store (MongoDB)

### Collections

#### Log Events

```javascript
{
    _id: ObjectId,
    timestamp: ISODate,
    level: String,
    service: String,
    message: String,
    context: {
        user_id: UUID,
        request_id: String,
        path: String,
        method: String,
        ip: String,
        user_agent: String
    },
    metadata: Object
}
```

#### Analytics Results

```javascript
{
    _id: ObjectId,
    analysis_type: String,
    parameters: Object,
    results: Object,
    created_at: ISODate,
    updated_at: ISODate,
    version: Number
}
```

## Search Engine (Elasticsearch)

### Indices

#### Products

```json
{
  "mappings": {
    "properties": {
      "product_id": { "type": "keyword" },
      "category": { "type": "keyword" },
      "name": { "type": "text" },
      "description": { "type": "text" },
      "price": { "type": "float" },
      "created_at": { "type": "date" },
      "updated_at": { "type": "date" }
    }
  }
}
```

#### Audit Logs

```json
{
  "mappings": {
    "properties": {
      "timestamp": { "type": "date" },
      "user_id": { "type": "keyword" },
      "action": { "type": "keyword" },
      "resource": { "type": "keyword" },
      "details": { "type": "object" },
      "metadata": { "type": "object" }
    }
  }
}
```
