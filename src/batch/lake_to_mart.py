from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.window import Window
from pathlib import Path
import logging
from datetime import datetime, timedelta
from sqlalchemy import create_engine
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataMartProcessor:
    def __init__(self):
        self.spark = SparkSession.builder \
            .appName("DataMartProcessor") \
            .getOrCreate()
            
        self.spark.sparkContext.setLogLevel("WARN")
        
        # 경로 설정
        self.data_lake_path = Path("/data/lake")
        
        # 데이터베이스 연결 설정
        self.db_url = os.getenv("OLAP_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ecommerce_olap")
        self.engine = create_engine(self.db_url)
        
    def read_lake_data(self, path: str, start_date: datetime, end_date: datetime):
        """데이터 레이크에서 특정 기간의 데이터를 읽어옵니다."""
        return self.spark.read.parquet(str(self.data_lake_path / path)) \
            .where((col("window.start") >= start_date) & 
                  (col("window.end") < end_date))
    
    def process_customer_mart(self, start_date: datetime, end_date: datetime):
        """고객 관련 데이터 마트를 처리합니다."""
        logger.info("Processing customer mart data...")
        
        # 고객 데이터 읽기
        customers = self.read_lake_data("customers", start_date, end_date)
        
        # 일별 신규 고객 집계
        daily_customers = customers \
            .groupBy(date_trunc("day", col("window.start")).alias("date")) \
            .agg(
                sum("count").alias("new_customers")
            )
            
        # 누적 고객 수 계산
        window_spec = Window.orderBy("date")
        customer_growth = daily_customers \
            .withColumn("total_customers", 
                       sum("new_customers").over(window_spec))
        
        # 데이터베이스에 저장
        customer_growth.toPandas().to_sql(
            "customer_growth_mart",
            self.engine,
            if_exists="append",
            index=False
        )
        
    def process_sales_mart(self, start_date: datetime, end_date: datetime):
        """매출 관련 데이터 마트를 처리합니다."""
        logger.info("Processing sales mart data...")
        
        # 매출 데이터 읽기
        sales = self.read_lake_data("sales", start_date, end_date)
        
        # 일별 매출 집계
        daily_sales = sales \
            .groupBy(date_trunc("day", col("window.start")).alias("date")) \
            .agg(
                sum("total_sales").alias("daily_revenue"),
                sum("total_items").alias("total_items"),
                avg("avg_price").alias("average_item_price"),
                sum("total_freight").alias("total_freight")
            ) \
            .withColumn("total_revenue", 
                       col("daily_revenue") + col("total_freight"))
            
        # 7일 이동 평균 계산
        window_spec = Window.orderBy("date").rowsBetween(-6, 0)
        sales_trends = daily_sales \
            .withColumn("revenue_7day_avg",
                       avg("total_revenue").over(window_spec))
        
        # 데이터베이스에 저장
        sales_trends.toPandas().to_sql(
            "sales_trends_mart",
            self.engine,
            if_exists="append",
            index=False
        )
        
    def process_order_mart(self, start_date: datetime, end_date: datetime):
        """주문 관련 데이터 마트를 처리합니다."""
        logger.info("Processing order mart data...")
        
        # 주문 데이터 읽기
        orders = self.read_lake_data("orders", start_date, end_date)
        
        # 일별 주문 통계 집계
        daily_orders = orders \
            .groupBy(date_trunc("day", col("window.start")).alias("date")) \
            .agg(
                sum("total_orders").alias("daily_orders"),
                avg("avg_delivery_delay").alias("avg_delivery_delay"),
                sum("unique_customers").alias("unique_customers")
            )
            
        # 주문 성과 지표 계산
        order_performance = daily_orders \
            .withColumn("orders_per_customer",
                       col("daily_orders") / col("unique_customers"))
            
        # 데이터베이스에 저장
        order_performance.toPandas().to_sql(
            "order_performance_mart",
            self.engine,
            if_exists="append",
            index=False
        )
        
    def process_all_marts(self, days_ago: int = 1):
        """모든 데이터 마트를 처리합니다."""
        try:
            # 처리할 기간 설정
            end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            start_date = end_date - timedelta(days=days_ago)
            
            logger.info(f"Processing data marts for period: {start_date} to {end_date}")
            
            # 각 마트 처리
            self.process_customer_mart(start_date, end_date)
            self.process_sales_mart(start_date, end_date)
            self.process_order_mart(start_date, end_date)
            
            logger.info("Data mart processing completed successfully")
            
        except Exception as e:
            logger.error(f"Error processing data marts: {str(e)}")
            raise
        finally:
            self.spark.stop()

if __name__ == "__main__":
    processor = DataMartProcessor()
    # 기본적으로 어제의 데이터를 처리
    processor.process_all_marts(days_ago=1) 