import json

import pytest

from app.lark.cards import CardRenderer


class TestCardRenderer:
    @pytest.fixture
    def renderer(self):
        return CardRenderer()

    def test_render_diagnosis_approval(self, renderer):
        result = renderer.render_diagnosis_approval(
            incident_id="INC-001",
            severity="P0",
            service="payment-svc",
            diagnosis_summary="OOMKill detected",
            confidence=0.85,
            proposals=[
                {"plugin": "restart_pod", "description": "Restart affected pod"},
                {"plugin": "scale_up", "description": "Scale deployment replicas"},
            ],
        )
        data = json.loads(result)
        assert data["type"] == "template"
        assert data["data"]["template_id"] == "diagnosis_approval"
        variables = data["data"]["template_variable"]
        assert variables["incident_id"] == "INC-001"
        assert variables["severity"] == "P0"
        assert variables["service"] == "payment-svc"
        assert variables["diagnosis_summary"] == "OOMKill detected"
        assert variables["confidence"] == 0.85
        assert len(variables["proposals"]) == 2
        assert variables["proposals"][0]["plugin"] == "restart_pod"

    def test_render_execution_result(self, renderer):
        result = renderer.render_execution_result(
            incident_id="INC-002",
            results=[
                {"plugin": "restart_pod", "status": "success"},
                {"plugin": "scale_up", "status": "failed", "error": "quota exceeded"},
            ],
        )
        data = json.loads(result)
        assert data["data"]["template_id"] == "execution_result"
        variables = data["data"]["template_variable"]
        assert variables["incident_id"] == "INC-002"
        assert len(variables["results"]) == 2

    def test_render_no_action(self, renderer):
        result = renderer.render_no_action(
            incident_id="INC-003",
            reason="Confidence too low",
        )
        data = json.loads(result)
        assert data["data"]["template_id"] == "no_action"
        variables = data["data"]["template_variable"]
        assert variables["incident_id"] == "INC-003"
        assert variables["reason"] == "Confidence too low"

    def test_render_escalate(self, renderer):
        result = renderer.render_escalate(
            incident_id="INC-004",
            reason="Auto-fix failed, escalating to on-call",
        )
        data = json.loads(result)
        assert data["data"]["template_id"] == "escalate"
        variables = data["data"]["template_variable"]
        assert variables["incident_id"] == "INC-004"
        assert variables["reason"] == "Auto-fix failed, escalating to on-call"
