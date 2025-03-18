from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.elasticsearch import ElasticsearchInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.pymongo import PymongoInstrumentor
from opentelemetry.instrumentation.kafka import KafkaInstrumentor
import logging
from typing import Optional
import os

class TelemetryManager:
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.resource = Resource.create({"service.name": service_name})
        self.setup_logging()
        self.setup_tracing()
        self.setup_metrics()
        self.setup_instrumentations()
        
    def setup_logging(self):
        """로깅 설정"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s [trace_id=%(otelTraceID)s span_id=%(otelSpanID)s]'
        )
        self.logger = logging.getLogger(self.service_name)
        
    def setup_tracing(self):
        """분산 추적 설정"""
        trace.set_tracer_provider(TracerProvider(resource=self.resource))
        
        otlp_exporter = OTLPSpanExporter(
            endpoint=os.getenv("OTLP_ENDPOINT", "http://localhost:4317")
        )
        
        span_processor = BatchSpanProcessor(otlp_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)
        
        self.tracer = trace.get_tracer(__name__)
        
    def setup_metrics(self):
        """메트릭 설정"""
        reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(
                endpoint=os.getenv("OTLP_ENDPOINT", "http://localhost:4317")
            )
        )
        
        metrics.set_meter_provider(MeterProvider(resource=self.resource, metric_readers=[reader]))
        self.meter = metrics.get_meter(__name__)
        
        # 기본 메트릭 생성
        self.setup_default_metrics()
        
    def setup_default_metrics(self):
        """기본 메트릭 정의"""
        # 요청 카운터
        self.request_counter = self.meter.create_counter(
            name="request_counter",
            description="Counts the number of requests",
            unit="1"
        )
        
        # 응답 시간 히스토그램
        self.response_time = self.meter.create_histogram(
            name="response_time",
            description="Response time in seconds",
            unit="s"
        )
        
        # 에러율 게이지
        self.error_rate = self.meter.create_up_down_counter(
            name="error_rate",
            description="Current error rate",
            unit="1"
        )
        
        # 활성 사용자 수
        self.active_users = self.meter.create_up_down_counter(
            name="active_users",
            description="Number of active users",
            unit="1"
        )
        
    def setup_instrumentations(self):
        """자동 계측 설정"""
        RequestsInstrumentor().instrument()
        FlaskInstrumentor().instrument()
        Psycopg2Instrumentor().instrument()
        ElasticsearchInstrumentor().instrument()
        RedisInstrumentor().instrument()
        PymongoInstrumentor().instrument()
        KafkaInstrumentor().instrument()
        
    def create_span(self, name: str, context: Optional[dict] = None) -> trace.Span:
        """새로운 추적 스팬 생성"""
        if context:
            carrier = {}
            TraceContextTextMapPropagator().inject(carrier, context)
            context = TraceContextTextMapPropagator().extract(carrier=carrier)
            
        return self.tracer.start_span(name, context=context)
    
    def record_request(self, endpoint: str, method: str):
        """요청 메트릭 기록"""
        self.request_counter.add(
            1,
            {"endpoint": endpoint, "method": method}
        )
        
    def record_response_time(self, duration: float, endpoint: str):
        """응답 시간 메트릭 기록"""
        self.response_time.record(
            duration,
            {"endpoint": endpoint}
        )
        
    def record_error(self, error_type: str):
        """에러 메트릭 기록"""
        self.error_rate.add(1, {"error_type": error_type})
        
    def record_user_activity(self, user_id: str, action: str):
        """사용자 활동 메트릭 기록"""
        self.active_users.add(
            1,
            {"user_id": user_id, "action": action}
        )
        
    def log_with_context(self, level: str, message: str, span: Optional[trace.Span] = None, **kwargs):
        """컨텍스트 정보가 포함된 로그 기록"""
        if span:
            context = {
                "trace_id": format(span.get_span_context().trace_id, "032x"),
                "span_id": format(span.get_span_context().span_id, "016x")
            }
            kwargs.update(context)
            
        log_method = getattr(self.logger, level.lower())
        log_method(message, extra=kwargs)

# 사용 예시
if __name__ == "__main__":
    telemetry = TelemetryManager("ecommerce-analytics")
    
    # 추적 예시
    with telemetry.create_span("process_order") as span:
        span.set_attribute("order_id", "12345")
        telemetry.log_with_context("info", "Processing order", span, order_id="12345")
        
        # 중첩된 스팬
        with telemetry.create_span("validate_payment") as child_span:
            child_span.set_attribute("payment_method", "credit_card")
            telemetry.log_with_context("info", "Validating payment", child_span)
            
    # 메트릭 기록 예시
    telemetry.record_request("/api/orders", "POST")
    telemetry.record_response_time(0.5, "/api/orders")
    telemetry.record_user_activity("user123", "place_order") 