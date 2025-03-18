from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SparkStreamProcessor:
    def __init__(self):
        self.spark = SparkSession.builder \
            .appName("EcommerceStreamProcessor") \
            .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.2.0") \
            .getOrCreate()
            
        self.spark.sparkContext.setLogLevel("WARN")
        
        # 데이터 레이크 경로 설정
        self.data_lake_path = Path("/data/lake")
        self.data_lake_path.mkdir(parents=True, exist_ok=True)
        
        # 스키마 정의
        self.define_schemas()
        
    def define_schemas(self):
        """각 토픽에 대한 스키마를 정의합니다."""
        self.customer_schema = StructType([
            StructField("customer_id", StringType(), True),
            StructField("customer_unique_id", StringType(), True),
            StructField("customer_zip_code", StringType(), True),
            StructField("customer_city", StringType(), True),
            StructField("customer_state", StringType(), True)
        ])
        
        self.order_schema = StructType([
            StructField("order_id", StringType(), True),
            StructField("customer_id", StringType(), True),
            StructField("order_status", StringType(), True),
            StructField("order_purchase_timestamp", StringType(), True),
            StructField("order_approved_at", StringType(), True),
            StructField("order_delivered_carrier_date", StringType(), True),
            StructField("order_delivered_customer_date", StringType(), True),
            StructField("order_estimated_delivery_date", StringType(), True)
        ])
        
        self.order_item_schema = StructType([
            StructField("order_id", StringType(), True),
            StructField("items", ArrayType(StructType([
                StructField("order_id", StringType(), True),
                StructField("order_item_id", IntegerType(), True),
                StructField("product_id", StringType(), True),
                StructField("seller_id", StringType(), True),
                StructField("shipping_limit_date", StringType(), True),
                StructField("price", DoubleType(), True),
                StructField("freight_value", DoubleType(), True)
            ])), True)
        ])
        
    def read_kafka_stream(self, topic: str, schema: StructType) -> DataFrame:
        """Kafka 스트림을 읽어옵니다."""
        return self.spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", "localhost:9092") \
            .option("subscribe", topic) \
            .load() \
            .select(from_json(col("value").cast("string"), schema).alias("data")) \
            .select("data.*")
    
    def process_customers(self):
        """고객 데이터 스트림을 처리합니다."""
        customers = self.read_kafka_stream("customers", self.customer_schema)
        
        # 시간별 새로운 고객 수 계산
        customer_counts = customers \
            .withWatermark("timestamp", "1 hour") \
            .groupBy(window("timestamp", "1 hour")) \
            .count()
            
        # 데이터 레이크에 저장
        query = customer_counts.writeStream \
            .outputMode("append") \
            .format("parquet") \
            .option("path", str(self.data_lake_path / "customers")) \
            .option("checkpointLocation", str(self.data_lake_path / "checkpoints" / "customers")) \
            .start()
            
        return query
    
    def process_orders(self):
        """주문 데이터 스트림을 처리합니다."""
        orders = self.read_kafka_stream("orders", self.order_schema)
        
        # 배송 지연 계산
        orders_with_delay = orders \
            .withColumn("delivery_delay",
                       when(col("order_delivered_customer_date").isNotNull(),
                            datediff(to_timestamp("order_delivered_customer_date"),
                                   to_timestamp("order_estimated_delivery_date")))
                       .otherwise(None))
        
        # 시간별 주문 통계
        order_stats = orders_with_delay \
            .withWatermark("order_purchase_timestamp", "1 hour") \
            .groupBy(window("order_purchase_timestamp", "1 hour")) \
            .agg(
                count("order_id").alias("total_orders"),
                avg("delivery_delay").alias("avg_delivery_delay"),
                countDistinct("customer_id").alias("unique_customers")
            )
            
        # 데이터 레이크에 저장
        query = order_stats.writeStream \
            .outputMode("append") \
            .format("parquet") \
            .option("path", str(self.data_lake_path / "orders")) \
            .option("checkpointLocation", str(self.data_lake_path / "checkpoints" / "orders")) \
            .start()
            
        return query
    
    def process_order_items(self):
        """주문 아이템 데이터 스트림을 처리합니다."""
        order_items = self.read_kafka_stream("order_items", self.order_item_schema)
        
        # items 배열을 펼치고 집계
        exploded_items = order_items \
            .select("order_id", explode("items").alias("item")) \
            .select("order_id", "item.*")
        
        # 시간별 매출 통계
        sales_stats = exploded_items \
            .withWatermark("timestamp", "1 hour") \
            .groupBy(window("timestamp", "1 hour")) \
            .agg(
                sum("price").alias("total_sales"),
                avg("price").alias("avg_price"),
                sum("freight_value").alias("total_freight"),
                count("order_id").alias("total_items")
            )
            
        # 데이터 레이크에 저장
        query = sales_stats.writeStream \
            .outputMode("append") \
            .format("parquet") \
            .option("path", str(self.data_lake_path / "sales")) \
            .option("checkpointLocation", str(self.data_lake_path / "checkpoints" / "sales")) \
            .start()
            
        return query
    
    def run(self):
        """모든 스트림 처리를 시작합니다."""
        try:
            # 각 스트림 처리 시작
            queries = [
                self.process_customers(),
                self.process_orders(),
                self.process_order_items()
            ]
            
            # 모든 쿼리가 종료될 때까지 대기
            for query in queries:
                query.awaitTermination()
                
        except KeyboardInterrupt:
            logger.info("Stopping stream processing...")
            self.spark.stop()
        except Exception as e:
            logger.error(f"Error in stream processing: {str(e)}")
            self.spark.stop()
            raise

if __name__ == "__main__":
    processor = SparkStreamProcessor()
    processor.run() 