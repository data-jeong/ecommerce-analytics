# Performance Optimization Guide

## Caching Strategy

### Redis Caching Implementation

1. **Cache Configuration**:

```python
CACHE_CONFIG = {
    'default_ttl': 3600,  # 1 hour
    'analytics_ttl': 21600,  # 6 hours
    'user_session_ttl': 86400,  # 24 hours
    'max_memory': '2gb',
    'eviction_policy': 'allkeys-lru'
}

redis_client = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    decode_responses=True
)
```

2. **Caching Decorator**:

```python
def cache_result(ttl: int = None, prefix: str = None):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = generate_cache_key(func, args, kwargs, prefix)

            # Try to get from cache
            cached_result = await redis_client.get(cache_key)
            if cached_result:
                return json.loads(cached_result)

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await redis_client.setex(
                cache_key,
                ttl or CACHE_CONFIG['default_ttl'],
                json.dumps(result)
            )
            return result
        return wrapper
    return decorator
```

3. **Cache Invalidation**:

```python
async def invalidate_cache_pattern(pattern: str):
    """Invalidate all cache keys matching the pattern."""
    keys = await redis_client.keys(pattern)
    if keys:
        await redis_client.delete(*keys)

@cache_result(ttl=3600, prefix='product')
async def get_product_analytics(product_id: str) -> dict:
    # Function implementation
    pass

# Invalidate on product update
async def update_product(product_id: str, data: dict):
    await db.update_product(product_id, data)
    await invalidate_cache_pattern(f'product:{product_id}:*')
```

### Database Query Caching

1. **Materialized Views**:

```sql
-- Create materialized view for daily sales metrics
CREATE MATERIALIZED VIEW daily_sales_metrics AS
SELECT
    DATE_TRUNC('day', order_purchase_timestamp) as date,
    COUNT(DISTINCT order_id) as total_orders,
    COUNT(DISTINCT customer_id) as unique_customers,
    SUM(payment_value) as total_revenue
FROM orders o
JOIN order_payments op ON o.order_id = op.order_id
GROUP BY DATE_TRUNC('day', order_purchase_timestamp);

-- Create index on the materialized view
CREATE INDEX ix_daily_sales_metrics_date ON daily_sales_metrics(date);

-- Refresh materialized view
CREATE OR REPLACE FUNCTION refresh_daily_sales_metrics()
RETURNS trigger AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY daily_sales_metrics;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
```

2. **Query Result Caching**:

```python
class QueryCache:
    def __init__(self, redis_client, ttl=3600):
        self.redis = redis_client
        self.ttl = ttl

    async def get_or_execute(self, query: str, params: tuple = None) -> List[Dict]:
        cache_key = f"query:{hashlib.sha256(f'{query}:{params}'.encode()).hexdigest()}"

        # Try cache first
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        # Execute query and cache results
        results = await db.fetch_all(query, params)
        await self.redis.setex(cache_key, self.ttl, json.dumps(results))
        return results
```

## Database Optimization

### Index Optimization

1. **Index Analysis**:

```sql
-- Find missing indexes
SELECT
    schemaname || '.' || relname as table,
    seq_scan - idx_scan as too_much_seq,
    case when seq_scan - idx_scan > 0
        then 'Missing Index?'
        else 'OK'
    end as index_use_status,
    pg_size_pretty(pg_relation_size(format('%I.%I', schemaname, relname)::regclass)) as table_size,
    idx_scan as index_scans_count
FROM
    pg_stat_user_tables
WHERE
    pg_relation_size(format('%I.%I', schemaname, relname)::regclass) > 80000
ORDER BY
    too_much_seq DESC;

-- Create optimal indexes based on query patterns
CREATE INDEX CONCURRENTLY ix_orders_customer_status
ON orders(customer_id, order_status, order_purchase_timestamp);
```

2. **Partial Indexes**:

```sql
-- Create partial index for active orders
CREATE INDEX ix_orders_active
ON orders(order_purchase_timestamp)
WHERE order_status NOT IN ('delivered', 'canceled');

-- Create partial index for high-value customers
CREATE INDEX ix_customers_high_value
ON customers(customer_id)
WHERE lifetime_value > 1000;
```

### Query Optimization

1. **Query Rewriting**:

```python
class QueryOptimizer:
    @staticmethod
    def optimize_select(query: str) -> str:
        """Optimize SELECT queries by adding appropriate hints."""
        if 'ORDER BY' in query and 'LIMIT' in query:
            return query.replace(
                'ORDER BY',
                'ORDER BY /*+ INDEX_RS_ASC(t) */'
            )
        return query

    @staticmethod
    def batch_process(items: List, batch_size: int = 1000):
        """Process items in batches to avoid memory issues."""
        return (items[i:i + batch_size] for i in range(0, len(items), batch_size))
```

2. **Efficient Joins**:

```sql
-- Use hash joins for large tables
SET enable_hashjoin = on;
SET enable_mergejoin = off;
SET enable_nestloop = off;

-- Example optimized query
EXPLAIN ANALYZE
SELECT /*+ HASHJOIN(o oi) */
    c.customer_id,
    COUNT(DISTINCT o.order_id) as total_orders,
    SUM(oi.price) as total_spent
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY c.customer_id;
```

## Code Performance

### Asynchronous Processing

1. **Background Tasks**:

```python
from fastapi_utils.tasks import repeat_every

class BackgroundTasks:
    def __init__(self):
        self.queue = asyncio.Queue()

    @repeat_every(seconds=60)
    async def process_analytics_queue(self):
        """Process analytics tasks in background."""
        while not self.queue.empty():
            task = await self.queue.get()
            try:
                await self._process_task(task)
            except Exception as e:
                logger.error(f"Error processing task: {e}")
            finally:
                self.queue.task_done()

    async def _process_task(self, task: dict):
        """Process individual analytics task."""
        if task['type'] == 'update_metrics':
            await update_customer_metrics(task['customer_id'])
        elif task['type'] == 'generate_report':
            await generate_analytics_report(task['params'])
```

2. **Parallel Processing**:

```python
from concurrent.futures import ThreadPoolExecutor
import multiprocessing

class ParallelProcessor:
    def __init__(self):
        self.executor = ThreadPoolExecutor(
            max_workers=multiprocessing.cpu_count()
        )

    async def process_in_parallel(self, items: List, processor_func):
        """Process items in parallel using ThreadPoolExecutor."""
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(self.executor, processor_func, item)
            for item in items
        ]
        return await asyncio.gather(*tasks)
```

### Memory Optimization

1. **Efficient Data Structures**:

```python
from typing import NamedTuple
from dataclasses import dataclass

@dataclass(frozen=True)
class CustomerMetrics:
    """Memory-efficient customer metrics using slots."""
    customer_id: str
    total_orders: int
    total_spent: float
    average_order_value: float

    def to_dict(self) -> dict:
        return asdict(self)

class OrderSummary(NamedTuple):
    """Immutable order summary using named tuple."""
    order_id: str
    total_items: int
    total_value: float
    status: str
```

2. **Generator Functions**:

```python
async def stream_large_dataset(query: str, batch_size: int = 1000):
    """Stream large datasets to avoid memory issues."""
    offset = 0
    while True:
        batch = await db.fetch_all(
            f"{query} LIMIT {batch_size} OFFSET {offset}"
        )
        if not batch:
            break
        yield batch
        offset += batch_size

async def process_large_dataset():
    async for batch in stream_large_dataset("SELECT * FROM orders"):
        await process_batch(batch)
```

## API Performance

### Response Optimization

1. **Compression Middleware**:

```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(
    GZipMiddleware,
    minimum_size=1000  # Only compress responses larger than 1KB
)
```

2. **Response Caching**:

```python
from starlette.responses import Response

@app.middleware("http")
async def cache_response_middleware(request: Request, call_next):
    if request.method != "GET":
        return await call_next(request)

    cache_key = f"response:{request.url.path}:{request.query_params}"
    cached_response = await redis_client.get(cache_key)

    if cached_response:
        return Response(
            content=cached_response,
            media_type="application/json",
            headers={"X-Cache": "HIT"}
        )

    response = await call_next(request)
    if response.status_code == 200:
        await redis_client.setex(
            cache_key,
            CACHE_CONFIG['default_ttl'],
            response.body
        )

    return response
```

## Monitoring and Profiling

### Performance Monitoring

1. **Query Performance Tracking**:

```python
class QueryTracker:
    def __init__(self):
        self.slow_query_threshold = 1.0  # seconds

    async def track_query(self, query: str, params: tuple = None):
        start_time = time.time()
        try:
            result = await db.fetch_all(query, params)
            duration = time.time() - start_time

            if duration > self.slow_query_threshold:
                await self.log_slow_query(query, duration)

            return result
        except Exception as e:
            await self.log_query_error(query, e)
            raise

    async def log_slow_query(self, query: str, duration: float):
        await log_to_monitoring_system(
            event_type="slow_query",
            query=query,
            duration=duration
        )
```

2. **Resource Usage Monitoring**:

```python
import psutil
from prometheus_client import Gauge, Histogram

# Metrics
api_requests = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['endpoint', 'method']
)
memory_usage = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes'
)

@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    api_requests.labels(
        endpoint=request.url.path,
        method=request.method
    ).observe(duration)

    memory_usage.set(psutil.Process().memory_info().rss)

    return response
```

## Performance Testing

### Load Testing

1. **Locust Test Configuration**:

```python
from locust import HttpUser, task, between

class AnalyticsUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def get_sales_summary(self):
        self.client.get("/api/v1/sales/summary")

    @task(2)
    def get_customer_metrics(self):
        self.client.get("/api/v1/customers/metrics")

    @task(1)
    def generate_report(self):
        self.client.post("/api/v1/reports/generate", json={
            "type": "sales",
            "period": "daily"
        })
```

2. **Performance Benchmarks**:

```python
import asyncio
import statistics
from typing import List

async def run_performance_benchmark(
    func,
    iterations: int = 1000
) -> dict:
    """Run performance benchmark for a function."""
    durations: List[float] = []

    for _ in range(iterations):
        start_time = time.time()
        await func()
        duration = time.time() - start_time
        durations.append(duration)

    return {
        'min': min(durations),
        'max': max(durations),
        'avg': statistics.mean(durations),
        'median': statistics.median(durations),
        'p95': statistics.quantiles(durations, n=20)[18],
        'p99': statistics.quantiles(durations, n=100)[98]
    }
```
