import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from src.data_generator.generator import EcommerceDataGenerator
import pandas as pd
import json

@pytest.fixture
def mock_kafka_producer():
    with patch('kafka.KafkaProducer') as mock:
        yield mock.return_value

@pytest.fixture
def mock_elasticsearch():
    with patch('elasticsearch.Elasticsearch') as mock:
        yield mock.return_value

@pytest.fixture
def mock_redis():
    with patch('redis.Redis') as mock:
        yield mock.return_value

@pytest.fixture
def mock_mongo():
    with patch('pymongo.MongoClient') as mock:
        yield mock.return_value

@pytest.fixture
def data_generator(mock_kafka_producer, mock_elasticsearch, mock_redis, mock_mongo):
    with patch('pandas.read_csv') as mock_read_csv:
        # Mock the reference data
        mock_read_csv.return_value = pd.DataFrame({
            'product_id': ['1', '2'],
            'seller_id': ['A', 'B']
        })
        generator = EcommerceDataGenerator()
        return generator

def test_generate_customer(data_generator):
    """고객 데이터 생성 테스트"""
    customer = data_generator.generate_customer()
    
    assert isinstance(customer, dict)
    assert 'customer_id' in customer
    assert 'customer_unique_id' in customer
    assert 'customer_zip_code' in customer
    assert 'customer_city' in customer
    assert 'customer_state' in customer

def test_generate_order(data_generator):
    """주문 데이터 생성 테스트"""
    customer_id = "test_customer_id"
    order = data_generator.generate_order(customer_id)
    
    assert isinstance(order, dict)
    assert order['customer_id'] == customer_id
    assert 'order_id' in order
    assert 'order_status' in order
    assert 'order_purchase_timestamp' in order
    
    # 타임스탬프 검증
    purchase_time = datetime.fromisoformat(order['order_purchase_timestamp'])
    approved_time = datetime.fromisoformat(order['order_approved_at'])
    delivered_time = datetime.fromisoformat(order['order_delivered_customer_date'])
    
    assert approved_time > purchase_time
    assert delivered_time > approved_time

def test_generate_order_item(data_generator):
    """주문 아이템 데이터 생성 테스트"""
    order_id = "test_order_id"
    item = data_generator.generate_order_item(order_id)
    
    assert isinstance(item, dict)
    assert item['order_id'] == order_id
    assert 'product_id' in item
    assert 'seller_id' in item
    assert 'price' in item
    assert 'freight_value' in item
    
    assert item['price'] >= 10 and item['price'] <= 1000
    assert item['freight_value'] >= 5 and item['freight_value'] <= 50

def test_generate_order_payment(data_generator):
    """주문 결제 데이터 생성 테스트"""
    order_id = "test_order_id"
    total_amount = 150.75
    payment = data_generator.generate_order_payment(order_id, total_amount)
    
    assert isinstance(payment, dict)
    assert payment['order_id'] == order_id
    assert payment['payment_value'] == total_amount
    assert payment['payment_type'] in ['credit_card', 'boleto', 'voucher', 'debit_card']
    assert payment['payment_installments'] >= 1 and payment['payment_installments'] <= 12

def test_generate_order_review(data_generator):
    """주문 리뷰 데이터 생성 테스트"""
    order_id = "test_order_id"
    review = data_generator.generate_order_review(order_id)
    
    assert isinstance(review, dict)
    assert review['order_id'] == order_id
    assert 'review_id' in review
    assert 'review_score' in review
    assert review['review_score'] >= 1 and review['review_score'] <= 5
    assert 'review_comment_title' in review
    assert 'review_comment_message' in review

def test_generate_log_event(data_generator):
    """로그 이벤트 생성 테스트"""
    event_type = "test_event"
    data = {"test_key": "test_value"}
    event = data_generator.generate_log_event(event_type, data)
    
    assert isinstance(event, dict)
    assert event['event_type'] == event_type
    assert 'event_id' in event
    assert 'timestamp' in event
    assert event['data'] == data

def test_send_to_kafka(data_generator, mock_kafka_producer):
    """Kafka 전송 테스트"""
    topic = "test_topic"
    data = {"test_key": "test_value"}
    
    data_generator.send_to_kafka(topic, data)
    
    mock_kafka_producer.send.assert_called_once_with(topic, value=data)

def test_store_in_elasticsearch(data_generator, mock_elasticsearch):
    """Elasticsearch 저장 테스트"""
    index = "test_index"
    data = {"test_key": "test_value"}
    
    data_generator.store_in_elasticsearch(index, data)
    
    mock_elasticsearch.index.assert_called_once_with(index=index, document=data)

def test_cache_in_redis(data_generator, mock_redis):
    """Redis 캐시 테스트"""
    key = "test_key"
    data = {"test_key": "test_value"}
    
    data_generator.cache_in_redis(key, data)
    
    mock_redis.setex.assert_called_once()

def test_store_in_mongodb(data_generator, mock_mongo):
    """MongoDB 저장 테스트"""
    collection = "test_collection"
    data = {"test_key": "test_value"}
    
    data_generator.store_in_mongodb(collection, data)
    
    mock_mongo['ecommerce_logs'][collection].insert_one.assert_called_once_with(data)

def test_generate_batch(data_generator):
    """배치 데이터 생성 테스트"""
    with patch.object(data_generator, 'send_to_kafka') as mock_kafka, \
         patch.object(data_generator, 'store_in_elasticsearch') as mock_es, \
         patch.object(data_generator, 'cache_in_redis') as mock_redis, \
         patch.object(data_generator, 'store_in_mongodb') as mock_mongo:
        
        data_generator.generate_batch()
        
        # Kafka 전송 검증
        assert mock_kafka.call_count >= 4  # customers, orders, order_items, payments
        
        # Elasticsearch 저장 검증
        mock_es.assert_called_once()
        
        # Redis 캐시 검증
        mock_redis.assert_called_once()
        
        # MongoDB 저장 검증
        mock_mongo.assert_called_once() 