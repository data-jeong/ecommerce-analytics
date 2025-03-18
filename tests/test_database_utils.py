import pytest
from unittest.mock import Mock, patch, MagicMock
from src.utils.database import DatabaseUtils
import pandas as pd
from datetime import datetime, timedelta

@pytest.fixture
def mock_oltp_engine():
    with patch('sqlalchemy.create_engine') as mock:
        mock_engine = Mock()
        mock.return_value = mock_engine
        yield mock_engine

@pytest.fixture
def mock_olap_engine():
    with patch('sqlalchemy.create_engine') as mock:
        mock_engine = Mock()
        mock.return_value = mock_engine
        yield mock_engine

@pytest.fixture
def mock_mongo_client():
    with patch('pymongo.MongoClient') as mock:
        mock_client = Mock()
        mock.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_redis_client():
    with patch('redis.Redis') as mock:
        mock_client = Mock()
        mock.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_elasticsearch_client():
    with patch('elasticsearch.Elasticsearch') as mock:
        mock_client = Mock()
        mock.return_value = mock_client
        yield mock_client

@pytest.fixture
def database_utils(mock_oltp_engine, mock_olap_engine, mock_mongo_client, 
                  mock_redis_client, mock_elasticsearch_client):
    with patch.dict('os.environ', {
        'OLTP_DATABASE_URL': 'postgresql://user:pass@localhost:5432/oltp',
        'OLAP_DATABASE_URL': 'postgresql://user:pass@localhost:5432/olap'
    }):
        utils = DatabaseUtils()
        return utils

def test_oltp_session_context(database_utils):
    """OLTP 세션 컨텍스트 매니저 테스트"""
    mock_session = MagicMock()
    database_utils.oltp_session_factory = Mock(return_value=mock_session)
    
    with database_utils.oltp_session() as session:
        assert session == mock_session
    
    mock_session.close.assert_called_once()

def test_olap_session_context(database_utils):
    """OLAP 세션 컨텍스트 매니저 테스트"""
    mock_session = MagicMock()
    database_utils.olap_session_factory = Mock(return_value=mock_session)
    
    with database_utils.olap_session() as session:
        assert session == mock_session
    
    mock_session.close.assert_called_once()

def test_execute_oltp_query(database_utils):
    """OLTP 쿼리 실행 테스트"""
    test_query = "SELECT * FROM users"
    test_params = {"user_id": 1}
    
    mock_result = pd.DataFrame({'id': [1], 'name': ['Test User']})
    mock_session = MagicMock()
    mock_session.execute.return_value.fetchall.return_value = [(1, 'Test User')]
    database_utils.oltp_session_factory = Mock(return_value=mock_session)
    
    result = database_utils.execute_oltp_query(test_query, test_params)
    
    assert isinstance(result, pd.DataFrame)
    mock_session.execute.assert_called_once_with(test_query, test_params)
    mock_session.close.assert_called_once()

def test_execute_olap_query(database_utils):
    """OLAP 쿼리 실행 테스트"""
    test_query = "SELECT * FROM sales_mart"
    test_params = {"date": "2024-01-01"}
    
    mock_result = pd.DataFrame({'date': ['2024-01-01'], 'total_sales': [1000]})
    mock_session = MagicMock()
    mock_session.execute.return_value.fetchall.return_value = [('2024-01-01', 1000)]
    database_utils.olap_session_factory = Mock(return_value=mock_session)
    
    result = database_utils.execute_olap_query(test_query, test_params)
    
    assert isinstance(result, pd.DataFrame)
    mock_session.execute.assert_called_once_with(test_query, test_params)
    mock_session.close.assert_called_once()

def test_get_mongo_logs(database_utils, mock_mongo_client):
    """MongoDB 로그 조회 테스트"""
    collection = "error_logs"
    start_time = datetime.now() - timedelta(hours=1)
    end_time = datetime.now()
    
    # Mock find 결과 설정
    mock_cursor = MagicMock()
    mock_cursor.__iter__.return_value = [
        {"timestamp": datetime.now(), "level": "ERROR", "message": "Test error"}
    ]
    mock_mongo_client['ecommerce_logs'][collection].find.return_value = mock_cursor
    
    logs = database_utils.get_mongo_logs(collection, start_time, end_time)
    
    assert isinstance(logs, list)
    assert len(logs) > 0
    assert "level" in logs[0]
    assert "message" in logs[0]

def test_get_redis_cache(database_utils, mock_redis_client):
    """Redis 캐시 조회 테스트"""
    key = "test_key"
    mock_redis_client.get.return_value = b'{"value": 100}'
    
    result = database_utils.get_redis_cache(key)
    
    assert result == {"value": 100}
    mock_redis_client.get.assert_called_once_with(key)

def test_set_redis_cache(database_utils, mock_redis_client):
    """Redis 캐시 설정 테스트"""
    key = "test_key"
    value = {"value": 100}
    expiry = 3600
    
    database_utils.set_redis_cache(key, value, expiry)
    
    mock_redis_client.setex.assert_called_once()

def test_search_elasticsearch(database_utils, mock_elasticsearch_client):
    """Elasticsearch 검색 테스트"""
    index = "test_index"
    query = {"match": {"field": "value"}}
    
    mock_elasticsearch_client.search.return_value = {
        "hits": {
            "hits": [
                {
                    "_source": {
                        "field": "value",
                        "timestamp": datetime.now().isoformat()
                    }
                }
            ]
        }
    }
    
    results = database_utils.search_elasticsearch(index, query)
    
    assert isinstance(results, list)
    assert len(results) > 0
    mock_elasticsearch_client.search.assert_called_once_with(index=index, body=query)

def test_get_common_analytics_queries(database_utils):
    """공통 분석 쿼리 테스트"""
    queries = database_utils.get_common_analytics_queries()
    
    assert isinstance(queries, dict)
    assert "daily_sales" in queries
    assert "product_performance" in queries
    assert "customer_cohorts" in queries
    assert "seller_performance" in queries

def test_get_monitoring_queries(database_utils):
    """모니터링 쿼리 테스트"""
    queries = database_utils.get_monitoring_queries()
    
    assert isinstance(queries, dict)
    assert "system_health" in queries
    assert "error_distribution" in queries
    assert "slow_queries" in queries

def test_error_handling_oltp(database_utils):
    """OLTP 에러 처리 테스트"""
    test_query = "SELECT * FROM non_existent_table"
    mock_session = MagicMock()
    mock_session.execute.side_effect = Exception("Database error")
    database_utils.oltp_session_factory = Mock(return_value=mock_session)
    
    with pytest.raises(Exception) as exc_info:
        database_utils.execute_oltp_query(test_query)
    
    assert str(exc_info.value) == "Database error"
    mock_session.close.assert_called_once()

def test_error_handling_redis(database_utils, mock_redis_client):
    """Redis 에러 처리 테스트"""
    key = "test_key"
    mock_redis_client.get.side_effect = Exception("Redis error")
    
    with pytest.raises(Exception) as exc_info:
        database_utils.get_redis_cache(key)
    
    assert str(exc_info.value) == "Redis error"

def test_connection_retry(database_utils):
    """연결 재시도 테스트"""
    with patch('time.sleep'):  # sleep 시간 건너뛰기
        test_query = "SELECT 1"
        mock_session = MagicMock()
        mock_session.execute.side_effect = [
            Exception("Connection lost"),  # 첫 번째 시도 실패
            Exception("Connection lost"),  # 두 번째 시도 실패
            MagicMock()  # 세 번째 시도 성공
        ]
        database_utils.oltp_session_factory = Mock(return_value=mock_session)
        
        database_utils.execute_oltp_query(test_query)
        
        assert mock_session.execute.call_count == 3 