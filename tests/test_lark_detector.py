import pytest

from app.lark.detector import AlertDetector


class TestAlertDetector:
    @pytest.fixture
    def detector(self):
        return AlertDetector(alert_bot_ids=["bot_001", "bot_002"])

    def test_is_alert_with_matching_bot_and_keyword(self, detector):
        assert detector.is_alert("[告警] Pod crash", "bot_001") is True

    def test_is_alert_with_alert_firing(self, detector):
        assert detector.is_alert("Alert Firing: High CPU", "bot_002") is True

    def test_is_alert_with_p0_fault(self, detector):
        assert detector.is_alert("P0 故障: DB down", "bot_001") is True

    def test_is_alert_with_p2_fault(self, detector):
        assert detector.is_alert("P2 故障: latency spike", "bot_002") is True

    def test_ignore_recovery_message(self, detector):
        assert detector.is_alert("[告警] 服务已恢复", "bot_001") is False

    def test_ignore_manual_processing(self, detector):
        assert detector.is_alert("[告警] 人工处理中", "bot_001") is False

    def test_ignore_non_bot_sender(self, detector):
        assert detector.is_alert("[告警] Pod crash", "user_123") is False

    def test_ignore_normal_message(self, detector):
        assert detector.is_alert("正常消息内容", "bot_001") is False

    def test_empty_text(self, detector):
        assert detector.is_alert("", "bot_001") is False
