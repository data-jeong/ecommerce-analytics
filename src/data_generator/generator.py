import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import random
from typing import Dict, List
import json
import uuid
from pathlib import Path
import time
from kafka import KafkaProducer
from elasticsearch import Elasticsearch
import redis
from pymongo import MongoClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EcommerceDataGenerator:
    def __init__(self):
        self.fake = Faker('pt_BR')  # Brazilian Portuguese locale
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        self.es = Elasticsearch(['http://localhost:9200'])
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.mongo_client = MongoClient('mongodb://root:example@localhost:27017/')
        self.mongo_db = self.mongo_client['ecommerce_logs']
        
        # Load existing data for reference
        self.load_reference_data()
        
    def load_reference_data(self):
        """기존 데이터에서 참조할 데이터를 로드합니다."""
        data_path = Path("data/raw_data")
        
        self.products = pd.read_csv(data_path / "olist_products_dataset.csv")
        self.sellers = pd.read_csv(data_path / "olist_sellers_dataset.csv")
        self.categories = pd.read_csv(data_path / "product_category_name_translation.csv")
        
    def generate_customer(self) -> Dict:
        """새로운 고객 데이터를 생성합니다."""
        return {
            'customer_id': str(uuid.uuid4()),
            'customer_unique_id': str(uuid.uuid4()),
            'customer_zip_code': self.fake.postcode(),
            'customer_city': self.fake.city(),
            'customer_state': self.fake.state_abbr()
        }
    
    def generate_order(self, customer_id: str) -> Dict:
        """주문 데이터를 생성합니다."""
        purchase_timestamp = self.fake.date_time_between(
            start_date='-1h',
            end_date='now'
        )
        
        return {
            'order_id': str(uuid.uuid4()),
            'customer_id': customer_id,
            'order_status': random.choice(['created', 'approved', 'shipped', 'delivered']),
            'order_purchase_timestamp': purchase_timestamp.isoformat(),
            'order_approved_at': (purchase_timestamp + timedelta(minutes=random.randint(5, 60))).isoformat(),
            'order_delivered_carrier_date': (purchase_timestamp + timedelta(days=random.randint(1, 3))).isoformat(),
            'order_delivered_customer_date': (purchase_timestamp + timedelta(days=random.randint(3, 10))).isoformat(),
            'order_estimated_delivery_date': (purchase_timestamp + timedelta(days=15)).isoformat()
        }
    
    def generate_order_item(self, order_id: str) -> Dict:
        """주문 아이템 데이터를 생성합니다."""
        product = self.products.sample(1).iloc[0]
        seller = self.sellers.sample(1).iloc[0]
        
        return {
            'order_id': order_id,
            'order_item_id': random.randint(1, 5),
            'product_id': product['product_id'],
            'seller_id': seller['seller_id'],
            'shipping_limit_date': (datetime.now() + timedelta(days=7)).isoformat(),
            'price': round(random.uniform(10, 1000), 2),
            'freight_value': round(random.uniform(5, 50), 2)
        }
    
    def generate_order_payment(self, order_id: str, total_amount: float) -> Dict:
        """주문 결제 데이터를 생성합니다."""
        return {
            'order_id': order_id,
            'payment_sequential': 1,
            'payment_type': random.choice(['credit_card', 'boleto', 'voucher', 'debit_card']),
            'payment_installments': random.randint(1, 12),
            'payment_value': total_amount
        }
    
    def generate_order_review(self, order_id: str) -> Dict:
        """주문 리뷰 데이터를 생성합니다."""
        return {
            'review_id': str(uuid.uuid4()),
            'order_id': order_id,
            'review_score': random.randint(1, 5),
            'review_comment_title': self.fake.sentence(),
            'review_comment_message': self.fake.text(),
            'review_creation_date': datetime.now().isoformat(),
            'review_answer_timestamp': (datetime.now() + timedelta(days=1)).isoformat()
        }
    
    def generate_log_event(self, event_type: str, data: Dict) -> Dict:
        """로그 이벤트를 생성합니다."""
        return {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'event_id': str(uuid.uuid4()),
            'data': data
        }
    
    def send_to_kafka(self, topic: str, data: Dict):
        """Kafka로 데이터를 전송합니다."""
        try:
            self.kafka_producer.send(topic, value=data)
            logger.info(f"Sent data to Kafka topic: {topic}")
        except Exception as e:
            logger.error(f"Error sending data to Kafka: {str(e)}")
    
    def store_in_elasticsearch(self, index: str, data: Dict):
        """Elasticsearch에 데이터를 저장합니다."""
        try:
            self.es.index(index=index, document=data)
            logger.info(f"Stored data in Elasticsearch index: {index}")
        except Exception as e:
            logger.error(f"Error storing data in Elasticsearch: {str(e)}")
    
    def cache_in_redis(self, key: str, data: Dict):
        """Redis에 데이터를 캐시합니다."""
        try:
            self.redis_client.setex(
                key,
                timedelta(hours=1),
                json.dumps(data)
            )
            logger.info(f"Cached data in Redis with key: {key}")
        except Exception as e:
            logger.error(f"Error caching data in Redis: {str(e)}")
    
    def store_in_mongodb(self, collection: str, data: Dict):
        """MongoDB에 로그 데이터를 저장합니다."""
        try:
            self.mongo_db[collection].insert_one(data)
            logger.info(f"Stored log in MongoDB collection: {collection}")
        except Exception as e:
            logger.error(f"Error storing log in MongoDB: {str(e)}")
    
    def generate_batch(self):
        """데이터 배치를 생성하고 각 시스템에 전송합니다."""
        # 고객 생성
        customer = self.generate_customer()
        
        # 주문 생성
        order = self.generate_order(customer['customer_id'])
        
        # 주문 아이템 생성
        items = []
        total_amount = 0
        for _ in range(random.randint(1, 5)):
            item = self.generate_order_item(order['order_id'])
            total_amount += item['price'] + item['freight_value']
            items.append(item)
        
        # 결제 생성
        payment = self.generate_order_payment(order['order_id'], total_amount)
        
        # 리뷰 생성 (80% 확률)
        review = None
        if random.random() < 0.8:
            review = self.generate_order_review(order['order_id'])
        
        # Kafka로 데이터 전송
        self.send_to_kafka('customers', customer)
        self.send_to_kafka('orders', order)
        self.send_to_kafka('order_items', {'order_id': order['order_id'], 'items': items})
        self.send_to_kafka('payments', payment)
        if review:
            self.send_to_kafka('reviews', review)
        
        # 로그 이벤트 생성 및 저장
        log_event = self.generate_log_event('order_created', {
            'order_id': order['order_id'],
            'customer_id': customer['customer_id'],
            'total_amount': total_amount
        })
        
        # Elasticsearch에 로그 저장
        self.store_in_elasticsearch('order_logs', log_event)
        
        # Redis에 최근 주문 캐시
        self.cache_in_redis(f"order:{order['order_id']}", order)
        
        # MongoDB에 상세 로그 저장
        self.store_in_mongodb('order_logs', {
            'timestamp': datetime.now(),
            'order': order,
            'items': items,
            'payment': payment,
            'review': review,
            'customer': customer
        })
        
    def run(self, interval: float = 1.0):
        """지정된 간격으로 데이터를 지속적으로 생성합니다."""
        try:
            while True:
                self.generate_batch()
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Stopping data generation...")
        finally:
            self.kafka_producer.close()

if __name__ == "__main__":
    generator = EcommerceDataGenerator()
    generator.run() 