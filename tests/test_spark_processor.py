import pytest
from unittest.mock import Mock, patch
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, TimestampType, DoubleType
from src.streaming.spark_processor import SparkStreamProcessor
import json
from datetime import datetime

@pytest.fixture
def spark():
    """SparkSession fixture"""
    spark = (SparkSession.builder
            .appName("TestEcommerceStreamProcessor")
            .master("local[2]")
            .config("spark.sql.shuffle.partitions", "1")
            .getOrCreate())
    yield spark
    spark.stop()

@pytest.fixture
def stream_processor(spark):
    """SparkStreamProcessor fixture"""
    processor = SparkStreamProcessor()
    return processor

def test_define_schemas(stream_processor):
    """스키마 정의 테스트"""
    # Customer 스키마 검증
    customer_schema = stream_processor.customer_schema
    assert isinstance(customer_schema, StructType)
    assert len(customer_schema.fields) >= 5
    assert any(field.name == "customer_id" for field in customer_schema.fields)
    assert any(field.name == "customer_unique_id" for field in customer_schema.fields)
    
    # Order 스키마 검증
    order_schema = stream_processor.order_schema
    assert isinstance(order_schema, StructType)
    assert len(order_schema.fields) >= 7
    assert any(field.name == "order_id" for field in order_schema.fields)
    assert any(field.name == "customer_id" for field in order_schema.fields)
    
    # Order Item 스키마 검증
    order_item_schema = stream_processor.order_item_schema
    assert isinstance(order_item_schema, StructType)
    assert len(order_item_schema.fields) >= 5
    assert any(field.name == "order_id" for field in order_item_schema.fields)
    assert any(field.name == "product_id" for field in order_item_schema.fields)

def test_read_kafka_stream(stream_processor, spark):
    """Kafka 스트림 읽기 테스트"""
    with patch.object(spark.readStream, 'format') as mock_format:
        mock_format.return_value.option.return_value.option.return_value.schema.return_value.load.return_value = "test_stream"
        
        stream = stream_processor.read_kafka_stream("test_topic", stream_processor.customer_schema)
        
        assert stream == "test_stream"
        mock_format.assert_called_once_with("kafka")
        mock_format.return_value.option.assert_any_call("kafka.bootstrap.servers", "localhost:9092")
        mock_format.return_value.option.assert_any_call("subscribe", "test_topic")

def test_process_customers(stream_processor, spark):
    """고객 데이터 처리 테스트"""
    # 테스트 데이터 생성
    test_data = [
        {
            "customer_id": "1",
            "customer_unique_id": "A1",
            "customer_zip_code": "12345",
            "customer_city": "Seoul",
            "customer_state": "SP",
            "timestamp": datetime.now().isoformat()
        }
    ]
    
    # DataFrame 생성
    test_df = spark.createDataFrame(test_data)
    
    with patch.object(stream_processor, 'read_kafka_stream') as mock_read:
        mock_read.return_value = test_df.toDF(*test_df.columns)
        
        with patch.object(test_df.writeStream, 'format') as mock_write:
            mock_write.return_value.option.return_value.option.return_value.start.return_value = Mock()
            
            stream_processor.process_customers()
            
            mock_read.assert_called_once()
            mock_write.assert_called_once_with("parquet")

def test_process_orders(stream_processor, spark):
    """주문 데이터 처리 테스트"""
    # 테스트 데이터 생성
    test_data = [
        {
            "order_id": "1",
            "customer_id": "1",
            "order_status": "delivered",
            "order_purchase_timestamp": datetime.now().isoformat(),
            "order_approved_at": datetime.now().isoformat(),
            "order_delivered_customer_date": datetime.now().isoformat(),
            "timestamp": datetime.now().isoformat()
        }
    ]
    
    # DataFrame 생성
    test_df = spark.createDataFrame(test_data)
    
    with patch.object(stream_processor, 'read_kafka_stream') as mock_read:
        mock_read.return_value = test_df.toDF(*test_df.columns)
        
        with patch.object(test_df.writeStream, 'format') as mock_write:
            mock_write.return_value.option.return_value.option.return_value.start.return_value = Mock()
            
            stream_processor.process_orders()
            
            mock_read.assert_called_once()
            mock_write.assert_called_once_with("parquet")

def test_process_order_items(stream_processor, spark):
    """주문 아이템 데이터 처리 테스트"""
    # 테스트 데이터 생성
    test_data = [
        {
            "order_id": "1",
            "product_id": "1",
            "seller_id": "1",
            "price": 100.0,
            "freight_value": 10.0,
            "timestamp": datetime.now().isoformat()
        }
    ]
    
    # DataFrame 생성
    test_df = spark.createDataFrame(test_data)
    
    with patch.object(stream_processor, 'read_kafka_stream') as mock_read:
        mock_read.return_value = test_df.toDF(*test_df.columns)
        
        with patch.object(test_df.writeStream, 'format') as mock_write:
            mock_write.return_value.option.return_value.option.return_value.start.return_value = Mock()
            
            stream_processor.process_order_items()
            
            mock_read.assert_called_once()
            mock_write.assert_called_once_with("parquet")

def test_run(stream_processor):
    """전체 실행 테스트"""
    with patch.object(stream_processor, 'process_customers') as mock_customers, \
         patch.object(stream_processor, 'process_orders') as mock_orders, \
         patch.object(stream_processor, 'process_order_items') as mock_items:
        
        # Mock query objects
        mock_customers.return_value = Mock()
        mock_orders.return_value = Mock()
        mock_items.return_value = Mock()
        
        # Run the processor
        stream_processor.run()
        
        # Verify all processes were called
        mock_customers.assert_called_once()
        mock_orders.assert_called_once()
        mock_items.assert_called_once()

def test_error_handling(stream_processor):
    """에러 처리 테스트"""
    with patch.object(stream_processor, 'process_customers', side_effect=Exception("Test error")), \
         patch.object(stream_processor, 'process_orders') as mock_orders, \
         patch.object(stream_processor, 'process_order_items') as mock_items:
        
        # Run the processor and expect exception
        with pytest.raises(Exception) as exc_info:
            stream_processor.run()
        
        assert str(exc_info.value) == "Test error"
        
        # Verify other processes were not called after error
        mock_orders.assert_not_called()
        mock_items.assert_not_called() 