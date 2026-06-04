import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_healthz_returns_ok_shape(client: TestClient) -> None:
    resp = client.get("/healthz")
    # DB 不可达时返回 503,可达时 200,本测试只断言 schema
    assert resp.status_code in (200, 503)
    body = resp.json()
    assert "status" in body
    assert "checks" in body
    assert "db" in body["checks"]
    assert "llm" in body["checks"]


def test_metrics_returns_prometheus(client: TestClient) -> None:
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    # Phase 3: 已替换为真实 Prometheus 指标
    assert "http_requests_total" in resp.text
    assert "fixer_incidents_active" in resp.text


def test_root_returns_service_info(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "ai-fixer"
