from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import get_db, get_olap_db
from .auth import get_current_user
from .schemas import *
from .utils import TelemetryManager, DatabaseUtils
from .config import Settings

# Initialize FastAPI app
app = FastAPI(
    title="E-commerce Analytics API",
    description="Advanced Analytics API for E-commerce Platform",
    version="1.0.0"
)

# Initialize components
settings = Settings()
telemetry = TelemetryManager("ecommerce-analytics")
db_utils = DatabaseUtils()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Advanced Analytics Endpoints
@app.get("/api/v1/analytics/customer-lifetime-value", response_model=List[CustomerLTV])
async def get_customer_ltv(
    lookback_days: int = 365,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_olap_db)
):
    with telemetry.create_span("get_customer_ltv") as span:
        span.set_attribute("lookback_days", lookback_days)
        
        try:
            query = """
                WITH customer_purchases AS (
                    SELECT 
                        fs.customer_id,
                        SUM(fs.total_amount) as total_spent,
                        COUNT(DISTINCT fs.order_id) as total_orders,
                        AVG(fs.total_amount) as avg_order_value,
                        MAX(fs.order_timestamp) as last_purchase,
                        MIN(fs.order_timestamp) as first_purchase
                    FROM marts.fact_sales fs
                    WHERE fs.order_timestamp >= CURRENT_DATE - INTERVAL ':days days'
                    GROUP BY fs.customer_id
                )
                SELECT 
                    cp.customer_id,
                    cp.total_spent,
                    cp.total_orders,
                    cp.avg_order_value,
                    cp.total_spent / NULLIF(EXTRACT(DAYS FROM (cp.last_purchase - cp.first_purchase)), 0) * 365 as annual_value,
                    dc.customer_segment,
                    EXTRACT(DAYS FROM (CURRENT_TIMESTAMP - cp.last_purchase)) as days_since_last_purchase
                FROM customer_purchases cp
                JOIN marts.dim_customer dc ON cp.customer_id = dc.customer_id
                WHERE dc.is_current = true
                ORDER BY total_spent DESC
            """
            
            results = db.execute(text(query), {"days": lookback_days})
            return [dict(r) for r in results]
        except Exception as e:
            telemetry.record_error("get_customer_ltv", str(e))
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/product-recommendations", response_model=List[ProductRecommendation])
async def get_product_recommendations(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_olap_db)
):
    with telemetry.create_span("get_product_recommendations") as span:
        span.set_attribute("product_id", product_id)
        
        try:
            query = """
                WITH co_purchased AS (
                    SELECT 
                        p1.product_id as source_product_id,
                        p2.product_id as recommended_product_id,
                        COUNT(*) as co_purchase_count
                    FROM marts.fact_sales fs1
                    JOIN marts.fact_sales fs2 ON fs1.customer_id = fs2.customer_id 
                        AND fs1.order_id != fs2.order_id
                        AND fs2.order_timestamp > fs1.order_timestamp
                        AND fs2.order_timestamp <= fs1.order_timestamp + INTERVAL '30 days'
                    JOIN marts.dim_product p1 ON fs1.product_id = p1.product_id
                    JOIN marts.dim_product p2 ON fs2.product_id = p2.product_id
                    WHERE p1.product_id = :product_id
                        AND p1.is_current = true
                        AND p2.is_current = true
                    GROUP BY p1.product_id, p2.product_id
                )
                SELECT 
                    cp.recommended_product_id,
                    dp.product_category_name,
                    cp.co_purchase_count,
                    AVG(fs.price) as avg_price,
                    AVG(fs.review_score) as avg_rating
                FROM co_purchased cp
                JOIN marts.dim_product dp ON cp.recommended_product_id = dp.product_id
                JOIN marts.fact_sales fs ON dp.product_id = fs.product_id
                WHERE dp.is_current = true
                GROUP BY cp.recommended_product_id, dp.product_category_name, cp.co_purchase_count
                ORDER BY co_purchase_count DESC, avg_rating DESC
                LIMIT 10
            """
            
            results = db.execute(text(query), {"product_id": product_id})
            return [dict(r) for r in results]
        except Exception as e:
            telemetry.record_error("get_product_recommendations", str(e))
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/customer-segmentation", response_model=List[CustomerSegment])
async def get_customer_segmentation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_olap_db)
):
    with telemetry.create_span("get_customer_segmentation") as span:
        try:
            query = """
                WITH customer_metrics AS (
                    SELECT 
                        customer_id,
                        COUNT(DISTINCT order_id) as frequency,
                        AVG(total_amount) as avg_order_value,
                        SUM(total_amount) as total_spent,
                        MAX(order_timestamp) as last_purchase,
                        MIN(order_timestamp) as first_purchase
                    FROM marts.fact_sales
                    WHERE order_timestamp >= CURRENT_DATE - INTERVAL '365 days'
                    GROUP BY customer_id
                ),
                segments AS (
                    SELECT 
                        cm.*,
                        CASE 
                            WHEN frequency > 10 AND total_spent > 1000 THEN 'VIP'
                            WHEN frequency > 5 AND total_spent > 500 THEN 'Loyal'
                            WHEN frequency > 2 AND total_spent > 200 THEN 'Regular'
                            WHEN last_purchase >= CURRENT_DATE - INTERVAL '90 days' THEN 'New'
                            ELSE 'At Risk'
                        END as segment
                    FROM customer_metrics cm
                )
                SELECT 
                    segment,
                    COUNT(*) as customer_count,
                    AVG(frequency) as avg_frequency,
                    AVG(avg_order_value) as avg_order_value,
                    AVG(total_spent) as avg_total_spent,
                    AVG(EXTRACT(DAYS FROM (last_purchase - first_purchase))) as avg_customer_age_days
                FROM segments
                GROUP BY segment
                ORDER BY avg_total_spent DESC
            """
            
            results = db.execute(text(query))
            return [dict(r) for r in results]
        except Exception as e:
            telemetry.record_error("get_customer_segmentation", str(e))
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/market-basket", response_model=List[MarketBasketInsight])
async def get_market_basket_analysis(
    min_support: float = 0.01,
    min_confidence: float = 0.1,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_olap_db)
):
    with telemetry.create_span("get_market_basket_analysis") as span:
        span.set_attribute("min_support", min_support)
        span.set_attribute("min_confidence", min_confidence)
        
        try:
            query = """
                WITH frequent_pairs AS (
                    SELECT 
                        p1.product_category_name as category1,
                        p2.product_category_name as category2,
                        COUNT(DISTINCT fs1.order_id) as pair_count,
                        COUNT(DISTINCT fs1.order_id)::float / (
                            SELECT COUNT(DISTINCT order_id) FROM marts.fact_sales
                        ) as support
                    FROM marts.fact_sales fs1
                    JOIN marts.fact_sales fs2 ON fs1.order_id = fs2.order_id
                        AND fs1.product_id < fs2.product_id
                    JOIN marts.dim_product p1 ON fs1.product_id = p1.product_id
                    JOIN marts.dim_product p2 ON fs2.product_id = p2.product_id
                    WHERE p1.is_current = true AND p2.is_current = true
                    GROUP BY p1.product_category_name, p2.product_category_name
                    HAVING COUNT(DISTINCT fs1.order_id)::float / (
                        SELECT COUNT(DISTINCT order_id) FROM marts.fact_sales
                    ) >= :min_support
                )
                SELECT 
                    fp.category1,
                    fp.category2,
                    fp.support,
                    fp.pair_count::float / NULLIF(cat1.category_count, 0) as confidence_1_2,
                    fp.pair_count::float / NULLIF(cat2.category_count, 0) as confidence_2_1,
                    fp.pair_count
                FROM frequent_pairs fp
                JOIN (
                    SELECT 
                        p.product_category_name,
                        COUNT(DISTINCT fs.order_id) as category_count
                    FROM marts.fact_sales fs
                    JOIN marts.dim_product p ON fs.product_id = p.product_id
                    WHERE p.is_current = true
                    GROUP BY p.product_category_name
                ) cat1 ON fp.category1 = cat1.product_category_name
                JOIN (
                    SELECT 
                        p.product_category_name,
                        COUNT(DISTINCT fs.order_id) as category_count
                    FROM marts.fact_sales fs
                    JOIN marts.dim_product p ON fs.product_id = p.product_id
                    WHERE p.is_current = true
                    GROUP BY p.product_category_name
                ) cat2 ON fp.category2 = cat2.product_category_name
                WHERE fp.pair_count::float / NULLIF(cat1.category_count, 0) >= :min_confidence
                   OR fp.pair_count::float / NULLIF(cat2.category_count, 0) >= :min_confidence
                ORDER BY fp.support DESC
            """
            
            results = db.execute(
                text(query), 
                {"min_support": min_support, "min_confidence": min_confidence}
            )
            return [dict(r) for r in results]
        except Exception as e:
            telemetry.record_error("get_market_basket_analysis", str(e))
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/sales-forecasting", response_model=List[SalesForecast])
async def get_sales_forecast(
    forecast_days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_olap_db)
):
    with telemetry.create_span("get_sales_forecast") as span:
        span.set_attribute("forecast_days", forecast_days)
        
        try:
            # Get historical daily sales
            query = """
                SELECT 
                    date_id,
                    SUM(total_revenue) as daily_revenue,
                    COUNT(DISTINCT order_id) as order_count
                FROM marts.fact_sales
                WHERE date_id >= CURRENT_DATE - INTERVAL '365 days'
                GROUP BY date_id
                ORDER BY date_id
            """
            
            results = db.execute(text(query))
            df = pd.DataFrame([dict(r) for r in results])
            
            # Simple time series forecasting using moving averages and trend
            df['ma7'] = df['daily_revenue'].rolling(window=7).mean()
            df['ma30'] = df['daily_revenue'].rolling(window=30).mean()
            
            # Calculate trend
            df['trend'] = np.arange(len(df))
            model = np.polyfit(df['trend'], df['daily_revenue'], 1)
            
            # Generate forecast
            forecast_dates = pd.date_range(
                start=df['date_id'].max() + pd.Timedelta(days=1),
                periods=forecast_days
            )
            
            forecasts = []
            for date in forecast_dates:
                forecast = {
                    'date': date.strftime('%Y-%m-%d'),
                    'forecasted_revenue': float(
                        df['ma7'].iloc[-1] * 0.5 +
                        df['ma30'].iloc[-1] * 0.3 +
                        (model[0] * (len(df) + len(forecasts)) + model[1]) * 0.2
                    ),
                    'confidence_lower': 0.0,  # Would need more sophisticated modeling
                    'confidence_upper': 0.0   # Would need more sophisticated modeling
                }
                forecasts.append(forecast)
            
            return forecasts
        except Exception as e:
            telemetry.record_error("get_sales_forecast", str(e))
            raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()} 