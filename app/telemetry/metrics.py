import time

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
)

INCIDENT_COUNT = Counter(
    "fixer_incidents_total",
    "Total incidents processed",
    ["status", "severity"],
)

PLUGIN_EXECUTION_COUNT = Counter(
    "fixer_plugin_executions_total",
    "Total plugin executions",
    ["plugin_name", "status"],
)

PLUGIN_DURATION = Histogram(
    "fixer_plugin_duration_seconds",
    "Plugin execution duration",
    ["plugin_name"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
)

INCIDENTS_ACTIVE = Gauge(
    "fixer_incidents_active",
    "Currently active incidents",
)


async def metrics_endpoint(request: Request) -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def setup_metrics(app: FastAPI) -> None:
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(duration)
        return response

    app.add_route("/metrics", metrics_endpoint)
