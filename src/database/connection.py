from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database URLs
OLTP_DATABASE_URL = os.getenv(
    "OLTP_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/ecommerce_oltp"
)
OLAP_DATABASE_URL = os.getenv(
    "OLAP_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/ecommerce_olap"
)

class DatabaseConnection:
    def __init__(self, database_url):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def get_session(self):
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()
            
    def create_tables(self, base):
        base.metadata.create_all(bind=self.engine)

# Create database connections
oltp_db = DatabaseConnection(OLTP_DATABASE_URL)
olap_db = DatabaseConnection(OLAP_DATABASE_URL)

def get_oltp_session():
    return next(oltp_db.get_session())

def get_olap_session():
    return next(olap_db.get_session()) 