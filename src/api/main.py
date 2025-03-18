from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import uvicorn
import jwt
from datetime import datetime, timedelta
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import get_db
from .models import *
from .schemas import *
from .auth import *
from .utils import TelemetryManager
from .config import Settings

# Initialize FastAPI app
app = FastAPI(
    title="E-commerce Analytics API",
    description="API for E-commerce Analytics Platform",
    version="1.0.0"
)

# Load settings
settings = Settings()

# Initialize telemetry
telemetry = TelemetryManager("ecommerce-api")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Authentication endpoints
@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    with telemetry.create_span("login_for_access_token") as span:
        user = authenticate_user(db, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Incorrect username or password"
            )
        access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        return {"access_token": access_token, "token_type": "bearer"}

# Protected API endpoints
@app.get("/api/v1/sales/summary", response_model=List[SalesSummary])
async def get_sales_summary(
    start_date: str,
    end_date: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    with telemetry.create_span("get_sales_summary") as span:
        span.set_attribute("start_date", start_date)
        span.set_attribute("end_date", end_date)
        
        try:
            results = db.execute("""
                SELECT 
                    date_trunc('day', order_purchase_timestamp) as date,
                    COUNT(DISTINCT o.order_id) as total_orders,
                    SUM(oi.price) as total_revenue,
                    COUNT(DISTINCT o.customer_id) as unique_customers
                FROM ecommerce.orders o
                JOIN ecommerce.order_items oi ON o.order_id = oi.order_id
                WHERE order_purchase_timestamp BETWEEN :start_date AND :end_date
                GROUP BY date_trunc('day', order_purchase_timestamp)
                ORDER BY date
            """, {"start_date": start_date, "end_date": end_date})
            
            return [dict(r) for r in results]
        except Exception as e:
            telemetry.record_error("get_sales_summary", str(e))
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/customers/cohort", response_model=List[CustomerCohort])
async def get_customer_cohort(
    cohort_period: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    with telemetry.create_span("get_customer_cohort") as span:
        span.set_attribute("cohort_period", cohort_period)
        
        try:
            results = db.execute("""
                WITH cohort AS (
                    SELECT 
                        customer_id,
                        date_trunc(:period, MIN(order_purchase_timestamp)) as cohort_date,
                        date_trunc(:period, order_purchase_timestamp) as order_period
                    FROM ecommerce.orders
                    GROUP BY customer_id, date_trunc(:period, order_purchase_timestamp)
                )
                SELECT 
                    cohort_date,
                    order_period,
                    COUNT(DISTINCT customer_id) as active_customers
                FROM cohort
                GROUP BY cohort_date, order_period
                ORDER BY cohort_date, order_period
            """, {"period": cohort_period})
            
            return [dict(r) for r in results]
        except Exception as e:
            telemetry.record_error("get_customer_cohort", str(e))
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/products/performance", response_model=List[ProductPerformance])
async def get_product_performance(
    start_date: str,
    end_date: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    with telemetry.create_span("get_product_performance") as span:
        span.set_attribute("start_date", start_date)
        span.set_attribute("end_date", end_date)
        
        try:
            results = db.execute("""
                SELECT 
                    p.product_category_name,
                    COUNT(DISTINCT oi.order_id) as total_orders,
                    SUM(oi.price) as total_revenue,
                    AVG(r.review_score) as avg_rating
                FROM ecommerce.products p
                JOIN ecommerce.order_items oi ON p.product_id = oi.product_id
                JOIN ecommerce.orders o ON oi.order_id = o.order_id
                LEFT JOIN ecommerce.order_reviews r ON o.order_id = r.order_id
                WHERE o.order_purchase_timestamp BETWEEN :start_date AND :end_date
                GROUP BY p.product_category_name
                ORDER BY total_revenue DESC
            """, {"start_date": start_date, "end_date": end_date})
            
            return [dict(r) for r in results]
        except Exception as e:
            telemetry.record_error("get_product_performance", str(e))
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/sellers/analytics", response_model=List[SellerAnalytics])
async def get_seller_analytics(
    start_date: str,
    end_date: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    with telemetry.create_span("get_seller_analytics") as span:
        span.set_attribute("start_date", start_date)
        span.set_attribute("end_date", end_date)
        
        try:
            results = db.execute("""
                SELECT 
                    s.seller_id,
                    s.seller_city,
                    s.seller_state,
                    COUNT(DISTINCT oi.order_id) as total_orders,
                    SUM(oi.price) as total_revenue,
                    AVG(r.review_score) as avg_rating,
                    COUNT(DISTINCT p.product_category_name) as unique_categories
                FROM ecommerce.sellers s
                JOIN ecommerce.order_items oi ON s.seller_id = oi.seller_id
                JOIN ecommerce.orders o ON oi.order_id = o.order_id
                JOIN ecommerce.products p ON oi.product_id = p.product_id
                LEFT JOIN ecommerce.order_reviews r ON o.order_id = r.order_id
                WHERE o.order_purchase_timestamp BETWEEN :start_date AND :end_date
                GROUP BY s.seller_id, s.seller_city, s.seller_state
                ORDER BY total_revenue DESC
            """, {"start_date": start_date, "end_date": end_date})
            
            return [dict(r) for r in results]
        except Exception as e:
            telemetry.record_error("get_seller_analytics", str(e))
            raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 