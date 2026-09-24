"""Prometheus metrics exposed at /metrics."""

from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter("http_requests_total", "HTTP requests", ["method", "route", "status"])
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency", ["method", "route"]
)
