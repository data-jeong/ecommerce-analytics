import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from src.logging.log_analyzer import LogAnalyzer
import pandas as pd
import json

@pytest.fixture
def mock_elasticsearch():
    with patch('elasticsearch.Elasticsearch') as mock:
        yield mock.return_value

@pytest.fixture
def log_analyzer(mock_elasticsearch):
    analyzer = LogAnalyzer()
    return analyzer

def test_query_logs(log_analyzer, mock_elasticsearch):
    """로그 쿼리 테스트"""
    # 테스트 데이터 설정
    test_index = "test_logs"
    start_time = datetime.now() - timedelta(hours=1)
    end_time = datetime.now()
    
    # Mock 응답 설정
    mock_response = {
        'hits': {
            'hits': [
                {
                    '_source': {
                        'timestamp': datetime.now().isoformat(),
                        'level': 'ERROR',
                        'message': 'Test error message',
                        'service': 'test_service'
                    }
                }
            ]
        }
    }
    mock_elasticsearch.search.return_value = mock_response
    
    # 로그 쿼리 실행
    logs = log_analyzer.query_logs(test_index, start_time, end_time)
    
    # 검증
    assert len(logs) == 1
    assert 'level' in logs[0]
    assert 'message' in logs[0]
    mock_elasticsearch.search.assert_called_once()

def test_analyze_error_patterns(log_analyzer):
    """에러 패턴 분석 테스트"""
    # 테스트 로그 데이터
    test_logs = [
        {
            'timestamp': datetime.now().isoformat(),
            'level': 'ERROR',
            'message': 'Connection timeout',
            'service': 'api'
        },
        {
            'timestamp': datetime.now().isoformat(),
            'level': 'ERROR',
            'message': 'Connection timeout',
            'service': 'api'
        },
        {
            'timestamp': datetime.now().isoformat(),
            'level': 'ERROR',
            'message': 'Invalid input',
            'service': 'web'
        }
    ]
    
    # 분석 실행
    error_patterns = log_analyzer.analyze_error_patterns(test_logs)
    
    # 검증
    assert isinstance(error_patterns, pd.DataFrame)
    assert len(error_patterns) == 2  # 두 가지 유형의 에러
    assert error_patterns.iloc[0]['count'] == 2  # 첫 번째 에러는 2번 발생
    assert error_patterns.iloc[1]['count'] == 1  # 두 번째 에러는 1번 발생

def test_analyze_performance_metrics(log_analyzer):
    """성능 메트릭 분석 테스트"""
    # 테스트 로그 데이터
    test_logs = [
        {
            'timestamp': datetime.now().isoformat(),
            'response_time': 100,
            'memory_usage': 512,
            'cpu_usage': 45
        },
        {
            'timestamp': datetime.now().isoformat(),
            'response_time': 150,
            'memory_usage': 600,
            'cpu_usage': 55
        }
    ]
    
    # 분석 실행
    metrics = log_analyzer.analyze_performance_metrics(test_logs)
    
    # 검증
    assert isinstance(metrics, dict)
    assert 'avg_response_time' in metrics
    assert 'max_response_time' in metrics
    assert 'avg_memory_usage' in metrics
    assert 'avg_cpu_usage' in metrics
    assert metrics['avg_response_time'] == 125  # (100 + 150) / 2

def test_analyze_user_activity(log_analyzer):
    """사용자 활동 분석 테스트"""
    # 테스트 로그 데이터
    test_logs = [
        {
            'timestamp': datetime.now().isoformat(),
            'user_id': 'user1',
            'session_id': 'session1',
            'event': 'login'
        },
        {
            'timestamp': datetime.now().isoformat(),
            'user_id': 'user1',
            'session_id': 'session1',
            'event': 'purchase'
        },
        {
            'timestamp': datetime.now().isoformat(),
            'user_id': 'user2',
            'session_id': 'session2',
            'event': 'login'
        }
    ]
    
    # 분석 실행
    activity = log_analyzer.analyze_user_activity(test_logs)
    
    # 검증
    assert isinstance(activity, dict)
    assert activity['unique_users'] == 2
    assert activity['total_events'] == 3
    assert activity['unique_sessions'] == 2

def test_analyze_system_health(log_analyzer):
    """시스템 상태 분석 테스트"""
    # 테스트 로그 데이터
    test_logs = [
        {
            'timestamp': datetime.now().isoformat(),
            'level': 'ERROR',
            'response_time': 100
        },
        {
            'timestamp': datetime.now().isoformat(),
            'level': 'INFO',
            'response_time': 150
        },
        {
            'timestamp': datetime.now().isoformat(),
            'level': 'INFO',
            'response_time': 200
        }
    ]
    
    # 분석 실행
    health = log_analyzer.analyze_system_health(test_logs)
    
    # 검증
    assert isinstance(health, dict)
    assert health['error_rate'] == pytest.approx(0.333, rel=1e-3)  # 1/3
    assert health['avg_response_time'] == 150  # (100 + 150 + 200) / 3

def test_generate_daily_report(log_analyzer, tmp_path):
    """일일 리포트 생성 테스트"""
    # 테스트 설정
    test_date = datetime.now() - timedelta(days=1)
    
    with patch.object(log_analyzer, 'query_logs') as mock_query, \
         patch.object(log_analyzer, 'analyze_error_patterns') as mock_errors, \
         patch.object(log_analyzer, 'analyze_performance_metrics') as mock_performance, \
         patch.object(log_analyzer, 'analyze_user_activity') as mock_activity, \
         patch.object(log_analyzer, 'analyze_system_health') as mock_health:
        
        # Mock 반환값 설정
        mock_query.return_value = []
        mock_errors.return_value = pd.DataFrame()
        mock_performance.return_value = {'avg_response_time': 100}
        mock_activity.return_value = {'unique_users': 10}
        mock_health.return_value = {'error_rate': 0.1}
        
        # 리포트 생성
        report = log_analyzer.generate_daily_report(test_date)
        
        # 검증
        assert isinstance(report, dict)
        assert 'date' in report
        assert 'error_patterns' in report
        assert 'performance_metrics' in report
        assert 'user_activity' in report
        assert 'system_health' in report

def test_analyze_trends(log_analyzer):
    """트렌드 분석 테스트"""
    # 테스트 설정
    days = 7
    
    with patch.object(log_analyzer, 'generate_daily_report') as mock_report:
        # Mock 일일 리포트 설정
        mock_report.return_value = {
            'date': datetime.now().isoformat(),
            'system_health': {
                'error_rate': 0.1,
                'avg_response_time': 100
            }
        }
        
        # 트렌드 분석 실행
        trends = log_analyzer.analyze_trends(days)
        
        # 검증
        assert isinstance(trends, dict)
        assert 'error_rate_trend' in trends
        assert 'response_time_trend' in trends
        assert len(trends['error_rate_trend']) == days
        mock_report.call_count == days

def test_error_handling(log_analyzer, mock_elasticsearch):
    """에러 처리 테스트"""
    # Elasticsearch 에러 시뮬레이션
    mock_elasticsearch.search.side_effect = Exception("Connection failed")
    
    # 에러 발생 테스트
    with pytest.raises(Exception) as exc_info:
        log_analyzer.query_logs("test_index", datetime.now(), datetime.now())
    
    assert str(exc_info.value) == "Connection failed"

def test_date_range_validation(log_analyzer):
    """날짜 범위 유효성 검증 테스트"""
    # 잘못된 날짜 범위 테스트
    end_time = datetime.now()
    start_time = end_time + timedelta(days=1)  # 시작 시간이 종료 시간보다 늦음
    
    with pytest.raises(ValueError) as exc_info:
        log_analyzer.query_logs("test_index", start_time, end_time)
    
    assert "Invalid date range" in str(exc_info.value) 