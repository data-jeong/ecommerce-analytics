from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode
from opentelemetry.metrics import Counter, Histogram
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from contextlib import contextmanager
import redis
import logging
import time
from typing import Optional, Dict, Any, Generator
from datetime import datetime, timedelta

from .config import Settings

settings = Settings()

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TelemetryManager:
    def __init__(self, service_name: str):
        self.service_name = service_name
        
        # Initialize tracing
        resource = Resource.create({"service.name": service_name})
        tracer_provider = TracerProvider(resource=resource)
        otlp_span_exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
        span_processor = BatchSpanProcessor(otlp_span_exporter)
        tracer_provider.add_span_processor(span_processor)
        trace.set_tracer_provider(tracer_provider)
        self.tracer = trace.get_tracer(__name__)
        
        # Initialize metrics
        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
        )
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        metrics.set_meter_provider(meter_provider)
        self.meter = metrics.get_meter(__name__)
        
        # Create metrics
        self.request_counter = self.meter.create_counter(
            name="api_requests_total",
            description="Total number of API requests",
            unit="1"
        )
        
        self.error_counter = self.meter.create_counter(
            name="api_errors_total",
            description="Total number of API errors",
            unit="1"
        )
        
        self.request_duration = self.meter.create_histogram(
            name="api_request_duration_seconds",
            description="API request duration in seconds",
            unit="s"
        )

    @contextmanager
    def create_span(self, name: str, attributes: Dict[str, Any] = None) -> Generator:
        """Create a new span with the given name and attributes."""
        with self.tracer.start_as_current_span(name) as span:
            start_time = time.time()
            try:
                if attributes:
                    span.set_attributes(attributes)
                yield span
                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
            finally:
                duration = time.time() - start_time
                self.request_duration.record(duration, {"operation": name})

    def record_request(self, endpoint: str, method: str):
        """Record an API request."""
        self.request_counter.add(1, {"endpoint": endpoint, "method": method})

    def record_error(self, operation: str, error_message: str):
        """Record an error."""
        self.error_counter.add(1, {"operation": operation})
        logger.error(f"Error in {operation}: {error_message}")

class CacheManager:
    def __init__(self):
        self.redis = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )
        self.default_ttl = settings.CACHE_TTL

    def generate_key(self, prefix: str, *args) -> str:
        """Generate a cache key from prefix and arguments."""
        return f"{prefix}:{':'.join(str(arg) for arg in args)}"

    def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        try:
            return self.redis.get(key)
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            return None

    def set(self, key: str, value: str, ttl: int = None) -> bool:
        """Set value in cache with optional TTL."""
        try:
            return self.redis.set(
                key,
                value,
                ex=ttl if ttl is not None else self.default_ttl
            )
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
            return False

    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            return bool(self.redis.delete(key))
        except Exception as e:
            logger.error(f"Cache delete error: {str(e)}")
            return False

class RateLimiter:
    def __init__(self):
        self.redis = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )
        self.window = settings.RATE_LIMIT_WINDOW
        self.max_requests = settings.RATE_LIMIT_MAX_REQUESTS

    def is_rate_limited(self, key: str) -> bool:
        """Check if the key is rate limited."""
        try:
            current = self.redis.get(key)
            if current is None:
                self.redis.set(key, 1, ex=self.window)
                return False
            
            count = int(current)
            if count >= self.max_requests:
                return True
            
            self.redis.incr(key)
            return False
        except Exception as e:
            logger.error(f"Rate limit error: {str(e)}")
            return False

class DateTimeUtils:
    @staticmethod
    def parse_date(date_str: str) -> datetime:
        """Parse date string to datetime object."""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            try:
                return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                raise ValueError("Invalid date format. Use YYYY-MM-DD or YYYY-MM-DDThh:mm:ss")

    @staticmethod
    def format_date(date: datetime) -> str:
        """Format datetime object to string."""
        return date.strftime("%Y-%m-%d")

    @staticmethod
    def get_date_range(start_date: str, end_date: str) -> tuple:
        """Get start and end dates as datetime objects."""
        start = DateTimeUtils.parse_date(start_date)
        end = DateTimeUtils.parse_date(end_date)
        if end < start:
            raise ValueError("End date must be after start date")
        return start, end

    @staticmethod
    def get_previous_period(date: datetime, period: str) -> datetime:
        """Get start of previous period."""
        if period == "day":
            return date - timedelta(days=1)
        elif period == "week":
            return date - timedelta(weeks=1)
        elif period == "month":
            if date.month == 1:
                return date.replace(year=date.year - 1, month=12)
            return date.replace(month=date.month - 1)
        elif period == "year":
            return date.replace(year=date.year - 1)
        else:
            raise ValueError("Invalid period. Use day, week, month, or year") 