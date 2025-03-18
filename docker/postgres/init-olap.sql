-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "timescaledb";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS marts;
SET search_path TO marts;

-- Create dimension tables
CREATE TABLE dim_date (
    date_id DATE PRIMARY KEY,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    day_name VARCHAR(10) NOT NULL,
    month_name VARCHAR(10) NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    is_holiday BOOLEAN NOT NULL
);

CREATE TABLE dim_customer (
    customer_id UUID PRIMARY KEY,
    customer_city VARCHAR(100) NOT NULL,
    customer_state VARCHAR(2) NOT NULL,
    customer_region VARCHAR(20) NOT NULL,
    first_order_date DATE,
    last_order_date DATE,
    total_orders INTEGER DEFAULT 0,
    total_amount NUMERIC(12,2) DEFAULT 0,
    customer_segment VARCHAR(20),
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL,
    valid_to TIMESTAMP WITH TIME ZONE NOT NULL,
    is_current BOOLEAN NOT NULL
);

CREATE TABLE dim_seller (
    seller_id UUID PRIMARY KEY,
    seller_city VARCHAR(100) NOT NULL,
    seller_state VARCHAR(2) NOT NULL,
    seller_region VARCHAR(20) NOT NULL,
    first_sale_date DATE,
    last_sale_date DATE,
    total_sales INTEGER DEFAULT 0,
    total_revenue NUMERIC(12,2) DEFAULT 0,
    seller_rating NUMERIC(3,2),
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL,
    valid_to TIMESTAMP WITH TIME ZONE NOT NULL,
    is_current BOOLEAN NOT NULL
);

CREATE TABLE dim_product (
    product_id UUID PRIMARY KEY,
    product_category_name VARCHAR(100) NOT NULL,
    product_category_name_english VARCHAR(100),
    product_weight_g INTEGER,
    product_length_cm INTEGER,
    product_height_cm INTEGER,
    product_width_cm INTEGER,
    price_range VARCHAR(20),
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL,
    valid_to TIMESTAMP WITH TIME ZONE NOT NULL,
    is_current BOOLEAN NOT NULL
);

-- Create fact tables
CREATE TABLE fact_sales (
    sale_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL,
    customer_id UUID NOT NULL,
    seller_id UUID NOT NULL,
    product_id UUID NOT NULL,
    order_date DATE NOT NULL,
    order_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    order_status VARCHAR(20) NOT NULL,
    payment_type VARCHAR(20) NOT NULL,
    payment_installments INTEGER NOT NULL,
    price NUMERIC(10,2) NOT NULL,
    freight_value NUMERIC(10,2) NOT NULL,
    total_amount NUMERIC(10,2) NOT NULL,
    review_score INTEGER,
    delivery_delay_days INTEGER,
    FOREIGN KEY (order_date) REFERENCES dim_date(date_id),
    FOREIGN KEY (customer_id) REFERENCES dim_customer(customer_id),
    FOREIGN KEY (seller_id) REFERENCES dim_seller(seller_id),
    FOREIGN KEY (product_id) REFERENCES dim_product(product_id)
);

CREATE TABLE fact_customer_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL,
    date_id DATE NOT NULL,
    orders_count INTEGER NOT NULL DEFAULT 0,
    total_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    average_order_value NUMERIC(10,2),
    total_items INTEGER NOT NULL DEFAULT 0,
    unique_products INTEGER NOT NULL DEFAULT 0,
    favorite_category VARCHAR(100),
    review_score_avg NUMERIC(3,2),
    FOREIGN KEY (date_id) REFERENCES dim_date(date_id),
    FOREIGN KEY (customer_id) REFERENCES dim_customer(customer_id)
);

CREATE TABLE fact_seller_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    seller_id UUID NOT NULL,
    date_id DATE NOT NULL,
    orders_count INTEGER NOT NULL DEFAULT 0,
    total_revenue NUMERIC(12,2) NOT NULL DEFAULT 0,
    average_order_value NUMERIC(10,2),
    total_items INTEGER NOT NULL DEFAULT 0,
    unique_products INTEGER NOT NULL DEFAULT 0,
    top_category VARCHAR(100),
    review_score_avg NUMERIC(3,2),
    delivery_delay_avg NUMERIC(5,2),
    FOREIGN KEY (date_id) REFERENCES dim_date(date_id),
    FOREIGN KEY (seller_id) REFERENCES dim_seller(seller_id)
);

CREATE TABLE fact_product_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL,
    date_id DATE NOT NULL,
    orders_count INTEGER NOT NULL DEFAULT 0,
    total_revenue NUMERIC(12,2) NOT NULL DEFAULT 0,
    average_price NUMERIC(10,2),
    total_quantity INTEGER NOT NULL DEFAULT 0,
    review_score_avg NUMERIC(3,2),
    FOREIGN KEY (date_id) REFERENCES dim_date(date_id),
    FOREIGN KEY (product_id) REFERENCES dim_product(product_id)
);

-- Create hypertables for time-series data
SELECT create_hypertable('fact_sales', 'order_timestamp');
SELECT create_hypertable('fact_customer_metrics', 'date_id');
SELECT create_hypertable('fact_seller_metrics', 'date_id');
SELECT create_hypertable('fact_product_metrics', 'date_id');

-- Create indexes
CREATE INDEX idx_fact_sales_order_date ON fact_sales(order_date);
CREATE INDEX idx_fact_sales_customer ON fact_sales(customer_id);
CREATE INDEX idx_fact_sales_seller ON fact_sales(seller_id);
CREATE INDEX idx_fact_sales_product ON fact_sales(product_id);
CREATE INDEX idx_fact_sales_status ON fact_sales(order_status);

CREATE INDEX idx_customer_metrics_date ON fact_customer_metrics(date_id);
CREATE INDEX idx_customer_metrics_customer ON fact_customer_metrics(customer_id);

CREATE INDEX idx_seller_metrics_date ON fact_seller_metrics(date_id);
CREATE INDEX idx_seller_metrics_seller ON fact_seller_metrics(seller_id);

CREATE INDEX idx_product_metrics_date ON fact_product_metrics(date_id);
CREATE INDEX idx_product_metrics_product ON fact_product_metrics(product_id);

-- Create materialized views for common analytics
CREATE MATERIALIZED VIEW daily_sales_summary AS
SELECT 
    d.date_id,
    d.year,
    d.month,
    d.day_of_week,
    COUNT(DISTINCT fs.order_id) as total_orders,
    COUNT(DISTINCT fs.customer_id) as unique_customers,
    SUM(fs.total_amount) as total_revenue,
    AVG(fs.total_amount) as average_order_value,
    SUM(CASE WHEN fs.review_score >= 4 THEN 1 ELSE 0 END)::FLOAT / 
        NULLIF(COUNT(fs.review_score), 0) as satisfaction_rate
FROM dim_date d
LEFT JOIN fact_sales fs ON d.date_id = fs.order_date
GROUP BY d.date_id, d.year, d.month, d.day_of_week
WITH DATA;

CREATE MATERIALIZED VIEW monthly_category_performance AS
SELECT 
    d.year,
    d.month,
    dp.product_category_name,
    COUNT(DISTINCT fs.order_id) as total_orders,
    COUNT(DISTINCT fs.customer_id) as unique_customers,
    SUM(fs.total_amount) as total_revenue,
    AVG(fs.review_score) as average_review_score
FROM dim_date d
JOIN fact_sales fs ON d.date_id = fs.order_date
JOIN dim_product dp ON fs.product_id = dp.product_id
GROUP BY d.year, d.month, dp.product_category_name
WITH DATA;

-- Create indexes on materialized views
CREATE UNIQUE INDEX idx_daily_sales_summary_date ON daily_sales_summary(date_id);
CREATE UNIQUE INDEX idx_monthly_category_performance ON monthly_category_performance(year, month, product_category_name);

-- Create refresh functions
CREATE OR REPLACE FUNCTION refresh_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY daily_sales_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY monthly_category_performance;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT USAGE ON SCHEMA marts TO ${OLAP_DB_USER};
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA marts TO ${OLAP_DB_USER};
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA marts TO ${OLAP_DB_USER}; 