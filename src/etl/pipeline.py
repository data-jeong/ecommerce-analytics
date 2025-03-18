import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from loguru import logger

from src.database.connection import get_oltp_session, get_olap_session
from src.database.models.oltp import Customer as OltpCustomer
from src.database.models.olap import (
    DimDate, DimCustomer, DimSeller, DimProduct,
    FactSales, FactCustomerSatisfaction, FactSellerPerformance
)

class ETLPipeline:
    def __init__(self):
        self.oltp_session = get_oltp_session()
        self.olap_session = get_olap_session()
        
    def extract_from_csv(self, file_path: Path) -> pd.DataFrame:
        """CSV 파일에서 데이터를 추출합니다."""
        logger.info(f"Extracting data from {file_path}")
        return pd.read_csv(file_path)
    
    def transform_date_dimension(self, df: pd.DataFrame, date_column: str) -> pd.DataFrame:
        """날짜 차원 테이블 데이터를 변환합니다."""
        dates = pd.to_datetime(df[date_column].unique())
        
        date_dim = pd.DataFrame({
            'date': dates,
            'day': dates.day,
            'month': dates.month,
            'year': dates.year,
            'quarter': dates.quarter,
            'day_of_week': dates.dayofweek,
            'is_weekend': (dates.dayofweek >= 5).astype(int)
        })
        
        return date_dim
    
    def transform_customer_dimension(self, df: pd.DataFrame) -> pd.DataFrame:
        """고객 차원 테이블 데이터를 변환합니다."""
        # 도시 크기 분류
        city_populations = {
            'Sao Paulo': 'Large',
            'Rio de Janeiro': 'Large',
            'Brasilia': 'Large',
            # 다른 도시들은 실제 데이터에 맞게 추가
        }
        
        df['customer_city_size'] = df['customer_city'].map(
            lambda x: city_populations.get(x, 'Medium')
        )
        
        # 지역 분류
        state_regions = {
            'SP': 'Southeast',
            'RJ': 'Southeast',
            'MG': 'Southeast',
            # 다른 주들은 실제 데이터에 맞게 추가
        }
        
        df['customer_region'] = df['customer_state'].map(
            lambda x: state_regions.get(x, 'Other')
        )
        
        return df
    
    def transform_product_dimension(self, df: pd.DataFrame) -> pd.DataFrame:
        """상품 차원 테이블 데이터를 변환합니다."""
        # 부피 계산
        df['product_volume_cm3'] = (
            df['product_length_cm'] *
            df['product_height_cm'] *
            df['product_width_cm']
        )
        
        # 크기 분류
        df['product_size_category'] = pd.qcut(
            df['product_volume_cm3'],
            q=3,
            labels=['Small', 'Medium', 'Large']
        )
        
        # 무게 분류
        df['product_weight_category'] = pd.qcut(
            df['product_weight_g'],
            q=3,
            labels=['Light', 'Medium', 'Heavy']
        )
        
        return df
    
    def transform_sales_fact(self, orders_df: pd.DataFrame, items_df: pd.DataFrame) -> pd.DataFrame:
        """판매 팩트 테이블 데이터를 변환합니다."""
        # 주문과 아이템 데이터 병합
        sales = orders_df.merge(items_df, on='order_id')
        
        # 배송 지연일 계산
        sales['delivery_delay_days'] = (
            pd.to_datetime(sales['order_delivered_customer_date']) -
            pd.to_datetime(sales['order_estimated_delivery_date'])
        ).dt.days
        
        # 배송 소요일 계산
        sales['shipping_days'] = (
            pd.to_datetime(sales['order_delivered_customer_date']) -
            pd.to_datetime(sales['order_purchase_timestamp'])
        ).dt.days
        
        # 총 금액 계산
        sales['total_amount'] = sales['price'] + sales['freight_value']
        
        return sales
    
    def load_dimension(self, df: pd.DataFrame, model, session: Session):
        """차원 테이블에 데이터를 로드합니다."""
        logger.info(f"Loading {model.__tablename__} dimension")
        
        for _, row in df.iterrows():
            obj = model(**row.to_dict())
            session.merge(obj)
        
        session.commit()
    
    def load_fact(self, df: pd.DataFrame, model, session: Session):
        """팩트 테이블에 데이터를 로드합니다."""
        logger.info(f"Loading {model.__tablename__} fact table")
        
        # 배치 처리를 위한 청크 크기
        chunk_size = 1000
        
        for i in range(0, len(df), chunk_size):
            chunk = df.iloc[i:i + chunk_size]
            
            for _, row in chunk.iterrows():
                obj = model(**row.to_dict())
                session.add(obj)
            
            session.commit()
    
    def run(self, data_path: Path):
        """ETL 파이프라인을 실행합니다."""
        try:
            logger.info("Starting ETL pipeline")
            
            # 데이터 추출
            customers_df = self.extract_from_csv(data_path / "olist_customers_dataset.csv")
            orders_df = self.extract_from_csv(data_path / "olist_orders_dataset.csv")
            items_df = self.extract_from_csv(data_path / "olist_order_items_dataset.csv")
            products_df = self.extract_from_csv(data_path / "olist_products_dataset.csv")
            
            # 차원 테이블 변환 및 로드
            date_dim = self.transform_date_dimension(orders_df, 'order_purchase_timestamp')
            self.load_dimension(date_dim, DimDate, self.olap_session)
            
            customer_dim = self.transform_customer_dimension(customers_df)
            self.load_dimension(customer_dim, DimCustomer, self.olap_session)
            
            product_dim = self.transform_product_dimension(products_df)
            self.load_dimension(product_dim, DimProduct, self.olap_session)
            
            # 팩트 테이블 변환 및 로드
            sales_fact = self.transform_sales_fact(orders_df, items_df)
            self.load_fact(sales_fact, FactSales, self.olap_session)
            
            logger.info("ETL pipeline completed successfully")
            
        except Exception as e:
            logger.error(f"Error in ETL pipeline: {str(e)}")
            raise
        
        finally:
            self.oltp_session.close()
            self.olap_session.close()

if __name__ == "__main__":
    data_path = Path("data/raw_data")
    etl = ETLPipeline()
    etl.run(data_path) 