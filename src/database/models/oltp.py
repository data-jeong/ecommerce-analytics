from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()

class OrderStatus(enum.Enum):
    CREATED = "created"
    APPROVED = "approved"
    INVOICED = "invoiced"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELED = "canceled"

class PaymentType(enum.Enum):
    CREDIT_CARD = "credit_card"
    BOLETO = "boleto"
    VOUCHER = "voucher"
    DEBIT_CARD = "debit_card"

class Customer(Base):
    __tablename__ = 'customers'

    customer_id = Column(String(32), primary_key=True)
    customer_unique_id = Column(String(32), index=True)
    customer_zip_code = Column(String(10))
    customer_city = Column(String(100))
    customer_state = Column(String(2))

    orders = relationship("Order", back_populates="customer")

class Seller(Base):
    __tablename__ = 'sellers'

    seller_id = Column(String(32), primary_key=True)
    seller_zip_code = Column(String(10))
    seller_city = Column(String(100))
    seller_state = Column(String(2))

    items = relationship("OrderItem", back_populates="seller")

class Product(Base):
    __tablename__ = 'products'

    product_id = Column(String(32), primary_key=True)
    product_category_name = Column(String(100))
    product_name_length = Column(Integer)
    product_description_length = Column(Integer)
    product_photos_qty = Column(Integer)
    product_weight_g = Column(Float)
    product_length_cm = Column(Float)
    product_height_cm = Column(Float)
    product_width_cm = Column(Float)

    items = relationship("OrderItem", back_populates="product")

class Order(Base):
    __tablename__ = 'orders'

    order_id = Column(String(32), primary_key=True)
    customer_id = Column(String(32), ForeignKey('customers.customer_id'))
    order_status = Column(Enum(OrderStatus))
    order_purchase_timestamp = Column(DateTime)
    order_approved_at = Column(DateTime)
    order_delivered_carrier_date = Column(DateTime)
    order_delivered_customer_date = Column(DateTime)
    order_estimated_delivery_date = Column(DateTime)

    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")
    payments = relationship("OrderPayment", back_populates="order")
    reviews = relationship("OrderReview", back_populates="order")

class OrderItem(Base):
    __tablename__ = 'order_items'

    order_id = Column(String(32), ForeignKey('orders.order_id'), primary_key=True)
    order_item_id = Column(Integer, primary_key=True)
    product_id = Column(String(32), ForeignKey('products.product_id'))
    seller_id = Column(String(32), ForeignKey('sellers.seller_id'))
    shipping_limit_date = Column(DateTime)
    price = Column(Float)
    freight_value = Column(Float)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="items")
    seller = relationship("Seller", back_populates="items")

class OrderPayment(Base):
    __tablename__ = 'order_payments'

    order_id = Column(String(32), ForeignKey('orders.order_id'), primary_key=True)
    payment_sequential = Column(Integer, primary_key=True)
    payment_type = Column(Enum(PaymentType))
    payment_installments = Column(Integer)
    payment_value = Column(Float)

    order = relationship("Order", back_populates="payments")

class OrderReview(Base):
    __tablename__ = 'order_reviews'

    review_id = Column(String(32), primary_key=True)
    order_id = Column(String(32), ForeignKey('orders.order_id'))
    review_score = Column(Integer)
    review_comment_title = Column(String(100))
    review_comment_message = Column(String(1000))
    review_creation_date = Column(DateTime)
    review_answer_timestamp = Column(DateTime)

    order = relationship("Order", back_populates="reviews") 