import pytest
from unittest.mock import Mock, patch, MagicMock
from src.observability.telemetry import TelemetryManager
import logging
from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode
from opentelemetry.metrics import Counter, Histogram

from api.telemetry import (
    setup_telemetry,
    create_span,
    record_metric,
    log_event,
    instrument_function,
    track_dependency,
    track_request,
    track_exception
)

@pytest.fixture
def mock_tracer():
    """Create a mock tracer for testing."""
    with patch('opentelemetry.trace.get_tracer') as mock:
        tracer = MagicMock()
        mock.return_value = tracer
        yield tracer

@pytest.fixture
def mock_meter():
    """Create a mock meter for testing."""
    with patch('opentelemetry.metrics.get_meter') as mock:
        meter = MagicMock()
        mock.return_value = meter
        yield meter

@pytest.fixture
def telemetry_manager(mock_tracer, mock_meter):
    with patch('opentelemetry.trace.set_tracer_provider'), \
         patch('opentelemetry.metrics.set_meter_provider'), \
         patch('opentelemetry.instrumentation.flask.FlaskInstrumentor'), \
         patch('opentelemetry.instrumentation.psycopg2.Psycopg2Instrumentor'), \
         patch('opentelemetry.instrumentation.elasticsearch.ElasticsearchInstrumentor'), \
         patch('opentelemetry.instrumentation.redis.RedisInstrumentor'), \
         patch('opentelemetry.instrumentation.pymongo.PymongoInstrumentor'), \
         patch('opentelemetry.instrumentation.kafka.KafkaInstrumentor'):
        manager = TelemetryManager("test_service")
        return manager

def test_setup_logging(telemetry_manager):
    """로깅 설정 테스트"""
    with patch('logging.getLogger') as mock_get_logger:
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        telemetry_manager.setup_logging()
        
        # 로거 설정 검증
        mock_get_logger.assert_called_once_with('test_service')
        assert mock_logger.setLevel.called
        assert mock_logger.addHandler.called

def test_setup_tracing(telemetry_manager):
    """분산 추적 설정 테스트"""
    with patch('opentelemetry.trace.set_tracer_provider') as mock_set_provider, \
         patch('opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter') as mock_exporter:
        
        telemetry_manager.setup_tracing()
        
        # 추적 설정 검증
        mock_set_provider.assert_called_once()
        mock_exporter.assert_called_once()

def test_setup_metrics(telemetry_manager, mock_meter):
    """메트릭 설정 테스트"""
    telemetry_manager.setup_metrics()
    
    # 메트릭 카운터 생성 검증
    assert mock_meter.create_counter.call_count >= 4  # requests, errors, active_users, response_times

def test_create_span(telemetry_manager, mock_tracer):
    """스팬 생성 테스트"""
    # Mock span context
    mock_span = MagicMock()
    mock_tracer.start_span.return_value = mock_span
    mock_span.__enter__.return_value = mock_span
    
    # 스팬 생성 및 검증
    with telemetry_manager.create_span("test_operation") as span:
        assert span == mock_span
        mock_tracer.start_span.assert_called_once_with("test_operation")

def test_record_request(telemetry_manager):
    """요청 기록 테스트"""
    with patch.object(telemetry_manager, 'request_counter') as mock_counter:
        telemetry_manager.record_request("GET", "/test")
        
        # 요청 카운터 증가 검증
        mock_counter.add.assert_called_once_with(1, {"method": "GET", "path": "/test"})

def test_record_response_time(telemetry_manager):
    """응답 시간 기록 테스트"""
    with patch.object(telemetry_manager, 'response_time_histogram') as mock_histogram:
        telemetry_manager.record_response_time(100, "GET", "/test")
        
        # 응답 시간 기록 검증
        mock_histogram.record.assert_called_once_with(100, {"method": "GET", "path": "/test"})

def test_record_error(telemetry_manager):
    """에러 기록 테스트"""
    with patch.object(telemetry_manager, 'error_counter') as mock_counter:
        error = ValueError("Test error")
        telemetry_manager.record_error(error, "test_operation")
        
        # 에러 카운터 증가 검증
        mock_counter.add.assert_called_once_with(1, {
            "error_type": "ValueError",
            "operation": "test_operation"
        })

def test_record_user_activity(telemetry_manager):
    """사용자 활동 기록 테스트"""
    with patch.object(telemetry_manager, 'active_users_counter') as mock_counter:
        telemetry_manager.record_user_activity("user123", "login")
        
        # 사용자 활동 카운터 증가 검증
        mock_counter.add.assert_called_once_with(1, {
            "user_id": "user123",
            "activity_type": "login"
        })

def test_log_with_context(telemetry_manager, mock_tracer):
    """컨텍스트 로깅 테스트"""
    # Mock current span
    mock_span = MagicMock()
    mock_span.get_span_context.return_value = MagicMock(
        trace_id=123,
        span_id=456
    )
    mock_tracer.start_span.return_value = mock_span
    
    with patch('logging.getLogger') as mock_get_logger:
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        # 컨텍스트와 함께 로깅
        with telemetry_manager.create_span("test_operation"):
            telemetry_manager.log_with_context("Test message", logging.INFO)
        
        # 로깅 검증
        mock_logger.log.assert_called_once()
        args = mock_logger.log.call_args[0]
        assert args[0] == logging.INFO
        assert "Test message" in args[1]
        assert "trace_id=123" in args[1]
        assert "span_id=456" in args[1]

def test_error_handling_in_span(telemetry_manager, mock_tracer):
    """스팬 내 에러 처리 테스트"""
    # Mock span
    mock_span = MagicMock()
    mock_tracer.start_span.return_value = mock_span
    
    # 에러 발생 시뮬레이션
    with pytest.raises(ValueError):
        with telemetry_manager.create_span("test_operation"):
            raise ValueError("Test error")
    
    # 스팬 상태 설정 검증
    mock_span.set_status.assert_called_once_with(Status(StatusCode.ERROR))

def test_automatic_instrumentation(telemetry_manager):
    """자동 계측 테스트"""
    with patch('opentelemetry.instrumentation.flask.FlaskInstrumentor') as mock_flask, \
         patch('opentelemetry.instrumentation.psycopg2.Psycopg2Instrumentor') as mock_psycopg2, \
         patch('opentelemetry.instrumentation.elasticsearch.ElasticsearchInstrumentor') as mock_es, \
         patch('opentelemetry.instrumentation.redis.RedisInstrumentor') as mock_redis, \
         patch('opentelemetry.instrumentation.pymongo.PymongoInstrumentor') as mock_mongo, \
         patch('opentelemetry.instrumentation.kafka.KafkaInstrumentor') as mock_kafka:
        
        telemetry_manager = TelemetryManager("test_service")
        
        # 각 계측기 초기화 검증
        mock_flask.instrument.assert_called_once()
        mock_psycopg2.instrument.assert_called_once()
        mock_es.instrument.assert_called_once()
        mock_redis.instrument.assert_called_once()
        mock_mongo.instrument.assert_called_once()
        mock_kafka.instrument.assert_called_once()

def test_metrics_labels(telemetry_manager):
    """메트릭 레이블 테스트"""
    with patch.object(telemetry_manager, 'request_counter') as mock_counter:
        # 다양한 레이블로 요청 기록
        telemetry_manager.record_request("GET", "/api/v1/users")
        telemetry_manager.record_request("POST", "/api/v1/orders")
        
        # 레이블 검증
        calls = mock_counter.add.call_args_list
        assert len(calls) == 2
        assert calls[0][1]["method"] == "GET"
        assert calls[0][1]["path"] == "/api/v1/users"
        assert calls[1][1]["method"] == "POST"
        assert calls[1][1]["path"] == "/api/v1/orders"

def test_setup_telemetry():
    """Test telemetry setup."""
    with patch('opentelemetry.sdk.trace.TracerProvider') as mock_provider:
        with patch('opentelemetry.sdk.metrics.MeterProvider') as mock_meter_provider:
            setup_telemetry(
                service_name="test-service",
                environment="test"
            )
            
            # Verify providers were initialized
            mock_provider.assert_called_once()
            mock_meter_provider.assert_called_once()

def test_create_span(mock_tracer):
    """Test span creation and management."""
    # Test successful span
    with create_span("test_operation") as span:
        assert span is not None
        mock_tracer.start_span.assert_called_once_with("test_operation")
    
    # Verify span is ended
    mock_tracer.start_span.return_value.end.assert_called_once()
    
    # Test span with attributes
    attributes = {"key": "value"}
    with create_span("test_operation", attributes=attributes) as span:
        assert span is not None
        span.set_attribute.assert_called_with("key", "value")

def test_record_metric(mock_meter):
    """Test metric recording."""
    # Test counter
    counter = MagicMock(spec=Counter)
    mock_meter.create_counter.return_value = counter
    
    record_metric("test_counter", 1)
    counter.add.assert_called_once_with(1)
    
    # Test histogram
    histogram = MagicMock(spec=Histogram)
    mock_meter.create_histogram.return_value = histogram
    
    record_metric("test_histogram", 100, metric_type="histogram")
    histogram.record.assert_called_once_with(100)

def test_log_event(caplog):
    """Test event logging."""
    with caplog.at_level(logging.INFO):
        log_event("test_event", {"key": "value"})
        
        assert "test_event" in caplog.text
        assert "key" in caplog.text
        assert "value" in caplog.text

@patch('api.telemetry.create_span')
def test_instrument_function(mock_create_span):
    """Test function instrumentation."""
    # Test successful execution
    @instrument_function
    def test_func():
        return "success"
    
    result = test_func()
    assert result == "success"
    mock_create_span.assert_called_once()
    
    # Test exception handling
    @instrument_function
    def error_func():
        raise ValueError("test error")
    
    with pytest.raises(ValueError):
        error_func()
    
    # Verify span recorded error
    mock_create_span.return_value.__enter__.return_value.record_exception.assert_called_once()
    mock_create_span.return_value.__enter__.return_value.set_status.assert_called_with(
        Status(StatusCode.ERROR)
    )

@patch('api.telemetry.create_span')
def test_track_dependency(mock_create_span):
    """Test dependency tracking."""
    # Test successful dependency call
    with track_dependency(
        "test_dependency",
        "test_operation",
        {"target": "test.com"}
    ) as span:
        assert span is not None
    
    # Verify span attributes
    span = mock_create_span.return_value.__enter__.return_value
    span.set_attribute.assert_any_call("dependency.name", "test_dependency")
    span.set_attribute.assert_any_call("dependency.operation", "test_operation")
    span.set_attribute.assert_any_call("target", "test.com")

@patch('api.telemetry.create_span')
def test_track_request(mock_create_span):
    """Test request tracking."""
    # Test successful request
    with track_request(
        "GET",
        "/test/path",
        {"user_id": "123"}
    ) as span:
        assert span is not None
    
    # Verify span attributes
    span = mock_create_span.return_value.__enter__.return_value
    span.set_attribute.assert_any_call("http.method", "GET")
    span.set_attribute.assert_any_call("http.path", "/test/path")
    span.set_attribute.assert_any_call("user_id", "123")

@patch('api.telemetry.create_span')
def test_track_exception(mock_create_span):
    """Test exception tracking."""
    try:
        raise ValueError("test error")
    except ValueError as e:
        track_exception(e, {"context": "test"})
    
    # Verify exception was recorded
    span = mock_create_span.return_value.__enter__.return_value
    span.record_exception.assert_called_once()
    span.set_status.assert_called_with(Status(StatusCode.ERROR))
    span.set_attribute.assert_called_with("context", "test")

def test_integration():
    """Test integration of telemetry components."""
    with patch('opentelemetry.trace.get_tracer') as mock_tracer:
        with patch('opentelemetry.metrics.get_meter') as mock_meter:
            # Setup mock tracer and meter
            tracer = MagicMock()
            meter = MagicMock()
            mock_tracer.return_value = tracer
            mock_meter.return_value = meter
            
            # Test instrumented function with metrics
            @instrument_function
            def test_operation():
                record_metric("test_counter", 1)
                with create_span("sub_operation"):
                    return "success"
            
            result = test_operation()
            assert result == "success"
            
            # Verify spans were created
            tracer.start_span.assert_called()
            
            # Verify metrics were recorded
            meter.create_counter.assert_called()
            meter.create_counter.return_value.add.assert_called_with(1) 