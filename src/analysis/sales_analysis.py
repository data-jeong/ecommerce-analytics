import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy import func
from loguru import logger

from src.database.connection import get_olap_session
from src.database.models.olap import (
    DimDate, DimCustomer, DimProduct, DimSeller,
    FactSales, FactCustomerSatisfaction
)

class SalesAnalyzer:
    def __init__(self):
        self.session = get_olap_session()
    
    def analyze_daily_sales(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """일별 매출 분석"""
        query = (
            self.session.query(
                DimDate.date,
                func.count(FactSales.sale_id).label('total_orders'),
                func.sum(FactSales.total_amount).label('total_revenue'),
                func.avg(FactSales.total_amount).label('average_order_value')
            )
            .join(FactSales, DimDate.date_id == FactSales.order_date_id)
            .filter(DimDate.date.between(start_date, end_date))
            .group_by(DimDate.date)
            .order_by(DimDate.date)
        )
        
        return pd.read_sql(query.statement, query.session.bind)
    
    def analyze_category_performance(self) -> pd.DataFrame:
        """카테고리별 성과 분석"""
        query = (
            self.session.query(
                DimProduct.product_category_name_english,
                func.count(FactSales.sale_id).label('total_sales'),
                func.sum(FactSales.total_amount).label('total_revenue'),
                func.avg(FactSales.price).label('average_price'),
                func.avg(FactSales.shipping_days).label('average_shipping_days')
            )
            .join(FactSales, DimProduct.product_id == FactSales.product_id)
            .group_by(DimProduct.product_category_name_english)
            .order_by(func.sum(FactSales.total_amount).desc())
        )
        
        return pd.read_sql(query.statement, query.session.bind)
    
    def analyze_customer_segments(self) -> pd.DataFrame:
        """고객 세그먼트 분석"""
        query = (
            self.session.query(
                DimCustomer.customer_region,
                DimCustomer.customer_city_size,
                func.count(distinct(FactSales.customer_id)).label('total_customers'),
                func.count(FactSales.sale_id).label('total_orders'),
                func.sum(FactSales.total_amount).label('total_revenue'),
                func.avg(FactSales.total_amount).label('average_order_value')
            )
            .join(FactSales, DimCustomer.customer_id == FactSales.customer_id)
            .group_by(DimCustomer.customer_region, DimCustomer.customer_city_size)
            .order_by(func.sum(FactSales.total_amount).desc())
        )
        
        return pd.read_sql(query.statement, query.session.bind)
    
    def analyze_seller_performance(self) -> pd.DataFrame:
        """판매자 성과 분석"""
        query = (
            self.session.query(
                DimSeller.seller_id,
                DimSeller.seller_city,
                DimSeller.seller_state,
                func.count(FactSales.sale_id).label('total_orders'),
                func.sum(FactSales.total_amount).label('total_revenue'),
                func.avg(FactSales.delivery_delay_days).label('average_delivery_delay')
            )
            .join(FactSales, DimSeller.seller_id == FactSales.seller_id)
            .group_by(DimSeller.seller_id, DimSeller.seller_city, DimSeller.seller_state)
            .order_by(func.sum(FactSales.total_amount).desc())
        )
        
        return pd.read_sql(query.statement, query.session.bind)
    
    def calculate_rfm_scores(self, analysis_date: datetime) -> pd.DataFrame:
        """RFM 분석 수행"""
        # 최근성(Recency) 계산
        recency_query = (
            self.session.query(
                FactSales.customer_id,
                func.max(DimDate.date).label('last_purchase_date')
            )
            .join(DimDate, FactSales.order_date_id == DimDate.date_id)
            .group_by(FactSales.customer_id)
        )
        
        recency_df = pd.read_sql(recency_query.statement, recency_query.session.bind)
        recency_df['recency'] = (
            analysis_date - pd.to_datetime(recency_df['last_purchase_date'])
        ).dt.days
        
        # 구매빈도(Frequency) 계산
        frequency_query = (
            self.session.query(
                FactSales.customer_id,
                func.count(FactSales.sale_id).label('frequency')
            )
            .group_by(FactSales.customer_id)
        )
        
        frequency_df = pd.read_sql(frequency_query.statement, frequency_query.session.bind)
        
        # 구매금액(Monetary) 계산
        monetary_query = (
            self.session.query(
                FactSales.customer_id,
                func.sum(FactSales.total_amount).label('monetary')
            )
            .group_by(FactSales.customer_id)
        )
        
        monetary_df = pd.read_sql(monetary_query.statement, monetary_query.session.bind)
        
        # RFM 데이터프레임 생성
        rfm_df = recency_df.merge(frequency_df, on='customer_id')
        rfm_df = rfm_df.merge(monetary_df, on='customer_id')
        
        # RFM 점수 계산 (1-5점)
        rfm_df['R_score'] = pd.qcut(rfm_df['recency'], q=5, labels=[5,4,3,2,1])
        rfm_df['F_score'] = pd.qcut(rfm_df['frequency'], q=5, labels=[1,2,3,4,5])
        rfm_df['M_score'] = pd.qcut(rfm_df['monetary'], q=5, labels=[1,2,3,4,5])
        
        # 종합 점수 계산
        rfm_df['RFM_score'] = (
            rfm_df['R_score'].astype(str) +
            rfm_df['F_score'].astype(str) +
            rfm_df['M_score'].astype(str)
        )
        
        return rfm_df
    
    def close(self):
        """세션 종료"""
        self.session.close()

def main():
    analyzer = SalesAnalyzer()
    
    try:
        # 일별 매출 분석
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        daily_sales = analyzer.analyze_daily_sales(start_date, end_date)
        logger.info("Daily sales analysis completed")
        
        # 카테고리 성과 분석
        category_performance = analyzer.analyze_category_performance()
        logger.info("Category performance analysis completed")
        
        # 고객 세그먼트 분석
        customer_segments = analyzer.analyze_customer_segments()
        logger.info("Customer segment analysis completed")
        
        # 판매자 성과 분석
        seller_performance = analyzer.analyze_seller_performance()
        logger.info("Seller performance analysis completed")
        
        # RFM 분석
        rfm_analysis = analyzer.calculate_rfm_scores(end_date)
        logger.info("RFM analysis completed")
        
        # 결과 저장
        output_dir = Path("data/analysis_results")
        output_dir.mkdir(exist_ok=True)
        
        daily_sales.to_csv(output_dir / "daily_sales.csv", index=False)
        category_performance.to_csv(output_dir / "category_performance.csv", index=False)
        customer_segments.to_csv(output_dir / "customer_segments.csv", index=False)
        seller_performance.to_csv(output_dir / "seller_performance.csv", index=False)
        rfm_analysis.to_csv(output_dir / "rfm_analysis.csv", index=False)
        
        logger.info("Analysis results saved successfully")
        
    finally:
        analyzer.close()

if __name__ == "__main__":
    main() 