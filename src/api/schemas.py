from pydantic import BaseModel, UUID4, EmailStr, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

class User(BaseModel):
    id: UUID4
    email: EmailStr
    full_name: str
    is_active: bool = True
    is_superuser: bool = False

class CustomerLTV(BaseModel):
    customer_id: UUID4
    total_spent: Decimal = Field(..., description="Total amount spent by the customer")
    total_orders: int = Field(..., description="Total number of orders placed")
    avg_order_value: Decimal = Field(..., description="Average order value")
    annual_value: Decimal = Field(..., description="Projected annual value")
    customer_segment: str = Field(..., description="Customer segment classification")
    days_since_last_purchase: int = Field(..., description="Days since last purchase")

class ProductRecommendation(BaseModel):
    recommended_product_id: UUID4
    product_category_name: str
    co_purchase_count: int = Field(..., description="Number of times products were purchased together")
    avg_price: Decimal = Field(..., description="Average price of the recommended product")
    avg_rating: float = Field(..., ge=0, le=5, description="Average rating of the recommended product")

class CustomerSegment(BaseModel):
    segment: str = Field(..., description="Segment name (e.g., VIP, Loyal, Regular, etc.)")
    customer_count: int = Field(..., description="Number of customers in the segment")
    avg_frequency: float = Field(..., description="Average purchase frequency")
    avg_order_value: Decimal = Field(..., description="Average order value")
    avg_total_spent: Decimal = Field(..., description="Average total spent per customer")
    avg_customer_age_days: float = Field(..., description="Average customer age in days")

class MarketBasketInsight(BaseModel):
    category1: str = Field(..., description="First product category")
    category2: str = Field(..., description="Second product category")
    support: float = Field(..., ge=0, le=1, description="Support metric (frequency of pair)")
    confidence_1_2: float = Field(..., ge=0, le=1, description="Confidence of category1 -> category2")
    confidence_2_1: float = Field(..., ge=0, le=1, description="Confidence of category2 -> category1")
    pair_count: int = Field(..., description="Number of times the pair appears together")

class SalesForecast(BaseModel):
    date: str = Field(..., description="Forecast date (YYYY-MM-DD)")
    forecasted_revenue: float = Field(..., description="Forecasted revenue")
    confidence_lower: float = Field(..., description="Lower bound of confidence interval")
    confidence_upper: float = Field(..., description="Upper bound of confidence interval")

# Response Models
class AnalyticsResponse(BaseModel):
    status: str = "success"
    message: Optional[str] = None
    data: Optional[dict] = None
    error: Optional[str] = None

class ErrorResponse(BaseModel):
    status: str = "error"
    error: str
    detail: Optional[str] = None 