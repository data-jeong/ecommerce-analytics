import pytest
from unittest.mock import Mock, patch
from pyspark.sql import SparkSession
from datetime import datetime, timedelta
from src.processing.data_mart_processor import DataMartProcessor
import pandas as pd

@pytest.fixture
def spark():
    """SparkSession fixture"""
    spark = (SparkSession.builder
            .appName("TestDataMartProcessor")
            .master("local[2]")
            .config("spark.sql.shuffle.partitions", "1")
            .getOrCreate())
    yield spark
    spark.stop()

@pytest.fixture
def data_mart_processor(spark):
    """DataMartProcessor fixture"""
    with patch('sqlalchemy.create_engine'):
        processor = DataMartProcessor()
        return processor

def test_read_lake_data(data_mart_processor, spark):
    """데이터 레이크 읽기 테스트"""
    # 테스트 기간 설정
    start_date = datetime.now() - timedelta(days=1)
    end_date = datetime.now()
    
    with patch.object(spark.read, 'parquet') as mock_read:
        # Mock DataFrame 생성
        test_data = [
            {
                "order_id": "1",
                "timestamp": datetime.now().isoformat(),
                "value": 100.0
            }
        ]
        mock_read.return_value = spark.createDataFrame(test_data)
        
        # 데이터 읽기 테스트
        df = data_mart_processor.read_lake_data("test_path", start_date, end_date)
        
        assert df is not None
        mock_read.assert_called_once_with("test_path")

def test_process_customer_mart(data_mart_processor):
    """고객 마트 처리 테스트"""
    test_date = datetime.now() - timedelta(days=1)
    
    with patch.object(data_mart_processor, 'read_lake_data') as mock_read, \
         patch.object(data_mart_processor, 'engine') as mock_engine:
        
        # Mock DataFrame 생성
        test_data = {
            'customer_id': ['1', '2'],
            'registration_date': [test_date, test_date],
            'last_order_date': [test_date, test_date],
            'total_orders': [5, 3],
            'total_spent': [500.0, 300.0]
        }
        mock_read.return_value = pd.DataFrame(test_data)
        
        # 처리 실행
        data_mart_processor.process_customer_mart(test_date)
        
        # 검증
        mock_read.assert_called_once()
        mock_engine.connect.assert_called_once()

def test_process_sales_mart(data_mart_processor):
    """매출 마트 처리 테스트"""
    test_date = datetime.now() - timedelta(days=1)
    
    with patch.object(data_mart_processor, 'read_lake_data') as mock_read, \
         patch.object(data_mart_processor, 'engine') as mock_engine:
        
        # Mock DataFrame 생성
        test_data = {
            'order_date': [test_date] * 3,
            'product_category': ['A', 'B', 'C'],
            'total_sales': [1000.0, 2000.0, 3000.0],
            'order_count': [10, 20, 30],
            'average_order_value': [100.0, 100.0, 100.0]
        }
        mock_read.return_value = pd.DataFrame(test_data)
        
        # 처리 실행
        data_mart_processor.process_sales_mart(test_date)
        
        # 검증
        mock_read.assert_called_once()
        mock_engine.connect.assert_called_once()

def test_process_order_mart(data_mart_processor):
    """주문 마트 처리 테스트"""
    test_date = datetime.now() - timedelta(days=1)
    
    with patch.object(data_mart_processor, 'read_lake_data') as mock_read, \
         patch.object(data_mart_processor, 'engine') as mock_engine:
        
        # Mock DataFrame 생성
        test_data = {
            'order_date': [test_date] * 3,
            'order_status': ['delivered', 'processing', 'cancelled'],
            'delivery_time': [24, 0, 0],
            'order_count': [50, 30, 20],
            'total_items': [100, 60, 40]
        }
        mock_read.return_value = pd.DataFrame(test_data)
        
        # 처리 실행
        data_mart_processor.process_order_mart(test_date)
        
        # 검증
        mock_read.assert_called_once()
        mock_engine.connect.assert_called_once()

def test_process_all_marts(data_mart_processor):
    """전체 마트 처리 테스트"""
    days_ago = 1
    
    with patch.object(data_mart_processor, 'process_customer_mart') as mock_customer, \
         patch.object(data_mart_processor, 'process_sales_mart') as mock_sales, \
         patch.object(data_mart_processor, 'process_order_mart') as mock_order:
        
        # 처리 실행
        data_mart_processor.process_all_marts(days_ago)
        
        # 검증
        mock_customer.assert_called_once()
        mock_sales.assert_called_once()
        mock_order.assert_called_once()

def test_error_handling(data_mart_processor):
    """에러 처리 테스트"""
    days_ago = 1
    
    with patch.object(data_mart_processor, 'process_customer_mart', 
                     side_effect=Exception("Test error")), \
         patch.object(data_mart_processor, 'process_sales_mart') as mock_sales, \
         patch.object(data_mart_processor, 'process_order_mart') as mock_order:
        
        # 에러 발생 테스트
        with pytest.raises(Exception) as exc_info:
            data_mart_processor.process_all_marts(days_ago)
        
        assert str(exc_info.value) == "Test error"
        
        # 다른 프로세스가 호출되지 않았는지 검증
        mock_sales.assert_not_called()
        mock_order.assert_not_called()

def test_date_handling(data_mart_processor):
    """날짜 처리 테스트"""
    # 과거 날짜 테스트
    days_ago = 7
    
    with patch.object(data_mart_processor, 'process_customer_mart') as mock_customer:
        data_mart_processor.process_all_marts(days_ago)
        
        call_date = mock_customer.call_args[0][0]
        expected_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_ago)
        
        assert call_date.date() == expected_date.date()

def test_database_connection(data_mart_processor):
    """데이터베이스 연결 테스트"""
    with patch('sqlalchemy.create_engine') as mock_create_engine:
        # 새로운 프로세서 인스턴스 생성
        processor = DataMartProcessor()
        
        # 데이터베이스 URL이 올바르게 사용되었는지 검증
        mock_create_engine.assert_called_once()
        assert "postgresql" in str(mock_create_engine.call_args) 