from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from contextlib import contextmanager
from typing import Generator
import logging

from .config import Settings

settings = Settings()

# Create database engines
oltp_engine = create_engine(
    settings.OLTP_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    echo=settings.SQL_ECHO
)

olap_engine = create_engine(
    settings.OLAP_DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=60,
    pool_recycle=1800,
    echo=settings.SQL_ECHO
)

# Create session factories
OLTPSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=oltp_engine)
OLAPSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=olap_engine)

# Base class for SQLAlchemy models
Base = declarative_base()

# Database dependency for OLTP database
def get_db() -> Generator[Session, None, None]:
    db = OLTPSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Database dependency for OLAP database
def get_olap_db() -> Generator[Session, None, None]:
    db = OLAPSessionLocal()
    try:
        yield db
    finally:
        db.close()

class DatabaseUtils:
    @staticmethod
    @contextmanager
    def transaction(db: Session):
        """Context manager for database transactions with automatic rollback on error."""
        try:
            yield
            db.commit()
        except Exception as e:
            db.rollback()
            logging.error(f"Transaction failed: {str(e)}")
            raise

    @staticmethod
    async def check_oltp_health() -> bool:
        """Check OLTP database health."""
        try:
            with OLTPSessionLocal() as session:
                session.execute("SELECT 1")
            return True
        except Exception as e:
            logging.error(f"OLTP database health check failed: {str(e)}")
            return False

    @staticmethod
    async def check_olap_health() -> bool:
        """Check OLAP database health."""
        try:
            with OLAPSessionLocal() as session:
                session.execute("SELECT 1")
            return True
        except Exception as e:
            logging.error(f"OLAP database health check failed: {str(e)}")
            return False

    @staticmethod
    def execute_query(db: Session, query: str, params: dict = None) -> list:
        """Execute a query and return results as a list of dictionaries."""
        try:
            result = db.execute(query, params or {})
            return [dict(row) for row in result]
        except Exception as e:
            logging.error(f"Query execution failed: {str(e)}")
            raise

    @staticmethod
    def paginate_query(query: str, page: int = 1, page_size: int = 100) -> str:
        """Add pagination to a query."""
        offset = (page - 1) * page_size
        return f"{query} LIMIT {page_size} OFFSET {offset}"

    @staticmethod
    def add_date_filter(query: str, date_column: str, start_date: str = None, end_date: str = None) -> tuple:
        """Add date range filter to a query."""
        params = {}
        if start_date or end_date:
            where_clause = []
            if start_date:
                where_clause.append(f"{date_column} >= :start_date")
                params['start_date'] = start_date
            if end_date:
                where_clause.append(f"{date_column} <= :end_date")
                params['end_date'] = end_date
            
            if "WHERE" in query:
                query = f"{query} AND {' AND '.join(where_clause)}"
            else:
                query = f"{query} WHERE {' AND '.join(where_clause)}"
        
        return query, params 