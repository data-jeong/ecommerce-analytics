from typing import Dict, List, Any, Optional
import pandas as pd
from sqlalchemy import create_engine, text
from pymongo import MongoClient
import redis
from elasticsearch import Elasticsearch
import logging
from contextlib import contextmanager
import os
from ..observability.telemetry import TelemetryManager

logger = logging.getLogger(__name__)
telemetry = TelemetryManager("database-utils")

class DatabaseUtils:
    def __init__(self):
        # PostgreSQL OLTP
        self.oltp_engine = create_engine(
            os.getenv("OLTP_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ecommerce_oltp")
        )
        
        # PostgreSQL OLAP
        self.olap_engine = create_engine(
            os.getenv("OLAP_DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/ecommerce_olap")
        )
        
        # MongoDB
        self.mongo_client = MongoClient(
            os.getenv("MONGODB_URL", "mongodb://root:example@localhost:27017/")
        )
        self.mongo_db = self.mongo_client['ecommerce_logs']
        
        # Redis
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=0
        )
        
        # Elasticsearch
        self.es_client = Elasticsearch([os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")])
        
    @contextmanager
    def oltp_session(self):
        """OLTP 데이터베이스 세션 컨텍스트 매니저"""
        with self.oltp_engine.connect() as connection:
            with telemetry.create_span("oltp_database_session") as span:
                try:
                    yield connection
                except Exception as e:
                    telemetry.record_error("oltp_session_error")
                    telemetry.log_with_context("error", f"OLTP session error: {str(e)}", span)
                    raise
                
    @contextmanager
    def olap_session(self):
        """OLAP 데이터베이스 세션 컨텍스트 매니저"""
        with self.olap_engine.connect() as connection:
            with telemetry.create_span("olap_database_session") as span:
                try:
                    yield connection
                except Exception as e:
                    telemetry.record_error("olap_session_error")
                    telemetry.log_with_context("error", f"OLAP session error: {str(e)}", span)
                    raise
                
    def execute_oltp_query(self, query: str, params: Optional[Dict] = None) -> pd.DataFrame:
        """OLTP 데이터베이스에서 쿼리 실행"""
        with telemetry.create_span("execute_oltp_query") as span:
            span.set_attribute("query", query)
            try:
                with self.oltp_session() as connection:
                    result = pd.read_sql_query(text(query), connection, params=params)
                    telemetry.record_response_time(0.1, "oltp_query")  # 실제 시간 측정 필요
                    return result
            except Exception as e:
                telemetry.record_error("oltp_query_error")
                telemetry.log_with_context("error", f"OLTP query error: {str(e)}", span)
                raise
                
    def execute_olap_query(self, query: str, params: Optional[Dict] = None) -> pd.DataFrame:
        """OLAP 데이터베이스에서 쿼리 실행"""
        with telemetry.create_span("execute_olap_query") as span:
            span.set_attribute("query", query)
            try:
                with self.olap_session() as connection:
                    result = pd.read_sql_query(text(query), connection, params=params)
                    telemetry.record_response_time(0.1, "olap_query")  # 실제 시간 측정 필요
                    return result
            except Exception as e:
                telemetry.record_error("olap_query_error")
                telemetry.log_with_context("error", f"OLAP query error: {str(e)}", span)
                raise
                
    def get_mongo_logs(self, collection: str, query: Dict) -> List[Dict]:
        """MongoDB에서 로그 조회"""
        with telemetry.create_span("get_mongo_logs") as span:
            span.set_attribute("collection", collection)
            span.set_attribute("query", str(query))
            try:
                result = list(self.mongo_db[collection].find(query))
                telemetry.record_response_time(0.1, "mongo_query")  # 실제 시간 측정 필요
                return result
            except Exception as e:
                telemetry.record_error("mongo_query_error")
                telemetry.log_with_context("error", f"MongoDB query error: {str(e)}", span)
                raise
                
    def get_redis_cache(self, key: str) -> Optional[Dict]:
        """Redis에서 캐시된 데이터 조회"""
        with telemetry.create_span("get_redis_cache") as span:
            span.set_attribute("key", key)
            try:
                result = self.redis_client.get(key)
                telemetry.record_response_time(0.01, "redis_get")  # 실제 시간 측정 필요
                return result
            except Exception as e:
                telemetry.record_error("redis_get_error")
                telemetry.log_with_context("error", f"Redis get error: {str(e)}", span)
                raise
                
    def set_redis_cache(self, key: str, value: Any, expire: int = 3600):
        """Redis에 데이터 캐시"""
        with telemetry.create_span("set_redis_cache") as span:
            span.set_attribute("key", key)
            try:
                self.redis_client.setex(key, expire, value)
                telemetry.record_response_time(0.01, "redis_set")  # 실제 시간 측정 필요
            except Exception as e:
                telemetry.record_error("redis_set_error")
                telemetry.log_with_context("error", f"Redis set error: {str(e)}", span)
                raise
                
    def search_elasticsearch(self, index: str, query: Dict) -> List[Dict]:
        """Elasticsearch에서 데이터 검색"""
        with telemetry.create_span("search_elasticsearch") as span:
            span.set_attribute("index", index)
            span.set_attribute("query", str(query))
            try:
                result = self.es_client.search(index=index, body=query)
                telemetry.record_response_time(0.1, "elasticsearch_search")  # 실제 시간 측정 필요
                return [hit["_source"] for hit in result["hits"]["hits"]]
            except Exception as e:
                telemetry.record_error("elasticsearch_search_error")
                telemetry.log_with_context("error", f"Elasticsearch search error: {str(e)}", span)
                raise
                
    def get_common_analytics_queries(self) -> Dict[str, str]:
        """자주 사용되는 분석 쿼리 모음"""
        return {
            "daily_sales": """
                SELECT 
                    date_trunc('day', order_purchase_timestamp) as date,
                    COUNT(DISTINCT order_id) as total_orders,
                    SUM(payment_value) as total_revenue,
                    COUNT(DISTINCT customer_id) as unique_customers
                FROM fact_sales
                WHERE order_purchase_timestamp BETWEEN :start_date AND :end_date
                GROUP BY date_trunc('day', order_purchase_timestamp)
                ORDER BY date
            """,
            
            "product_performance": """
                SELECT 
                    p.product_category_name,
                    COUNT(DISTINCT fs.order_id) as total_orders,
                    SUM(fs.payment_value) as total_revenue,
                    AVG(fs.payment_value) as avg_order_value,
                    COUNT(DISTINCT fs.customer_id) as unique_customers
                FROM fact_sales fs
                JOIN dim_product p ON fs.product_id = p.product_id
                WHERE fs.order_purchase_timestamp BETWEEN :start_date AND :end_date
                GROUP BY p.product_category_name
                ORDER BY total_revenue DESC
            """,
            
            "customer_cohort": """
                WITH first_purchase AS (
                    SELECT 
                        customer_id,
                        MIN(date_trunc('month', order_purchase_timestamp)) as cohort_month
                    FROM fact_sales
                    GROUP BY customer_id
                )
                SELECT 
                    fp.cohort_month,
                    COUNT(DISTINCT fs.customer_id) as total_customers,
                    SUM(fs.payment_value) as total_revenue
                FROM fact_sales fs
                JOIN first_purchase fp ON fs.customer_id = fp.customer_id
                GROUP BY fp.cohort_month
                ORDER BY fp.cohort_month
            """,
            
            "seller_performance": """
                SELECT 
                    s.seller_id,
                    s.seller_city,
                    COUNT(DISTINCT fs.order_id) as total_orders,
                    SUM(fs.payment_value) as total_revenue,
                    AVG(fs.delivery_delay_days) as avg_delivery_delay,
                    AVG(fs.review_score) as avg_review_score
                FROM fact_sales fs
                JOIN dim_seller s ON fs.seller_id = s.seller_id
                WHERE fs.order_purchase_timestamp BETWEEN :start_date AND :end_date
                GROUP BY s.seller_id, s.seller_city
                ORDER BY total_revenue DESC
            """
        }
        
    def get_monitoring_queries(self) -> Dict[str, str]:
        """모니터링용 쿼리 모음"""
        return {
            "system_health": """
                SELECT 
                    date_trunc('hour', timestamp) as hour,
                    COUNT(*) as total_requests,
                    AVG(response_time) as avg_response_time,
                    MAX(response_time) as max_response_time,
                    SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as error_count
                FROM system_logs
                WHERE timestamp >= NOW() - INTERVAL '24 hours'
                GROUP BY date_trunc('hour', timestamp)
                ORDER BY hour
            """,
            
            "error_distribution": """
                SELECT 
                    error_type,
                    COUNT(*) as error_count,
                    AVG(response_time) as avg_response_time
                FROM system_logs
                WHERE status_code >= 400
                    AND timestamp >= NOW() - INTERVAL '24 hours'
                GROUP BY error_type
                ORDER BY error_count DESC
            """,
            
            "slow_queries": """
                SELECT 
                    query_text,
                    COUNT(*) as execution_count,
                    AVG(execution_time) as avg_execution_time,
                    MAX(execution_time) as max_execution_time
                FROM query_logs
                WHERE execution_time > 1000  -- 1초 이상
                    AND timestamp >= NOW() - INTERVAL '24 hours'
                GROUP BY query_text
                ORDER BY avg_execution_time DESC
            """
        }

# 사용 예시
if __name__ == "__main__":
    db_utils = DatabaseUtils()
    
    # 분석 쿼리 실행 예시
    start_date = "2024-01-01"
    end_date = "2024-01-31"
    
    daily_sales = db_utils.execute_olap_query(
        db_utils.get_common_analytics_queries()["daily_sales"],
        {"start_date": start_date, "end_date": end_date}
    )
    
    # 모니터링 쿼리 실행 예시
    system_health = db_utils.execute_olap_query(
        db_utils.get_monitoring_queries()["system_health"]
    )
    
    # MongoDB 로그 조회 예시
    recent_errors = db_utils.get_mongo_logs(
        "system_logs",
        {"level": "ERROR", "timestamp": {"$gte": "2024-01-01"}}
    )
    
    # Redis 캐시 사용 예시
    cached_data = db_utils.get_redis_cache("daily_stats")
    if cached_data is None:
        # 캐시가 없으면 계산하고 저장
        data = db_utils.execute_olap_query(
            "SELECT * FROM daily_stats WHERE date = CURRENT_DATE"
        )
        db_utils.set_redis_cache("daily_stats", data.to_json()) 