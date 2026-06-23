from app.telemetry.metrics import REQUEST_COUNT, setup_metrics


def test_setup_metrics_returns_app() -> None:
    from fastapi import FastAPI

    app = FastAPI()
    setup_metrics(app)
    # 验证 /metrics 端点已注册
    routes = [r.path for r in app.routes]
    assert "/metrics" in routes


def test_metrics_exporter_returns_data() -> None:
    from fastapi import FastAPI

    app = FastAPI()
    setup_metrics(app)
    # 手动递增一个 counter 验证输出
    REQUEST_COUNT.labels(method="GET", endpoint="/test", status_code="200").inc()
    # generate_latest 能正常返回 bytes
    from prometheus_client import generate_latest

    output = generate_latest()
    assert b"http_requests_total" in output
    assert b"fixer_incidents_active" in output
    assert b"fixer_plugin_duration_seconds" in output
