from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

# Dimension Tables
class DimDate(Base):
    __tablename__ = 'dim_date'

    date_id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime)
    day = Column(Integer)
    month = Column(Integer)
    year = Column(Integer)
    quarter = Column(Integer)
    day_of_week = Column(Integer)
    is_weekend = Column(Integer)
    is_holiday = Column(Integer)

class DimCustomer(Base):
    __tablename__ = 'dim_customer'

    customer_id = Column(String(32), primary_key=True)
    customer_unique_id = Column(String(32), index=True)
    customer_city = Column(String(100))
    customer_state = Column(String(2))
    customer_zip_code_prefix = Column(String(5))
    
    # Derived attributes
    customer_city_size = Column(String(20))  # Small, Medium, Large based on population
    customer_region = Column(String(20))      # North, South, etc.

class DimSeller(Base):
    __tablename__ = 'dim_seller'

    seller_id = Column(String(32), primary_key=True)
    seller_city = Column(String(100))
    seller_state = Column(String(2))
    seller_zip_code_prefix = Column(String(5))
    
    # Derived attributes
    seller_region = Column(String(20))
    seller_city_size = Column(String(20))

class DimProduct(Base):
    __tablename__ = 'dim_product'

    product_id = Column(String(32), primary_key=True)
    product_category_name = Column(String(100))
    product_category_name_english = Column(String(100))
    product_weight_g = Column(Float)
    product_length_cm = Column(Float)
    product_height_cm = Column(Float)
    product_width_cm = Column(Float)
    
    # Derived attributes
    product_volume_cm3 = Column(Float)
    product_size_category = Column(String(20))  # Small, Medium, Large
    product_weight_category = Column(String(20))  # Light, Medium, Heavy

# Fact Tables
class FactSales(Base):
    __tablename__ = 'fact_sales'

    sale_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(32))
    order_item_id = Column(Integer)
    customer_id = Column(String(32), ForeignKey('dim_customer.customer_id'))
    seller_id = Column(String(32), ForeignKey('dim_seller.seller_id'))
    product_id = Column(String(32), ForeignKey('dim_product.product_id'))
    order_date_id = Column(Integer, ForeignKey('dim_date.date_id'))
    delivery_date_id = Column(Integer, ForeignKey('dim_date.date_id'))
    
    # Measures
    price = Column(Float)
    freight_value = Column(Float)
    total_amount = Column(Float)  # price + freight_value
    
    # Performance metrics
    delivery_delay_days = Column(Integer)  # Actual - Estimated delivery date
    shipping_days = Column(Integer)        # Delivery - Purchase date

class FactCustomerSatisfaction(Base):
    __tablename__ = 'fact_customer_satisfaction'

    satisfaction_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(32))
    customer_id = Column(String(32), ForeignKey('dim_customer.customer_id'))
    review_date_id = Column(Integer, ForeignKey('dim_date.date_id'))
    
    # Measures
    review_score = Column(Integer)
    has_review_comment = Column(Integer)  # 0 or 1
    review_response_time_hours = Column(Float)

class FactSellerPerformance(Base):
    __tablename__ = 'fact_seller_performance'

    performance_id = Column(Integer, primary_key=True, autoincrement=True)
    seller_id = Column(String(32), ForeignKey('dim_seller.seller_id'))
    date_id = Column(Integer, ForeignKey('dim_date.date_id'))
    
    # Daily aggregated measures
    total_orders = Column(Integer)
    total_items_sold = Column(Integer)
    total_revenue = Column(Float)
    average_delivery_delay = Column(Float)
    customer_satisfaction_score = Column(Float) 