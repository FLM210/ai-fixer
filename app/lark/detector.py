import re


class AlertDetector:
    def __init__(self, alert_bot_ids: list[str] | None = None) -> None:
        self.alert_bot_ids = alert_bot_ids or []
        # 匹配告警格式
        self.alert_pattern = re.compile(
            r"🔴\s*Firing|Firing:|Alert\s*Firing|\[告警\]|P[0-3]\s*故障|告警详情|"
            r"PodStatus|CrashLoopBackOff|OOMKilled|NodeNotReady|MemoryPressure|"
            r"DiskPressure|CPUThrottling|HighMemoryUsage|HighCPUUsage"
        )
        self.ignore_pattern = re.compile(r"✅\s*Resolved|已恢复|人工处理中|Resolved:")

    def is_alert(self, text: str, sender_id: str = "") -> bool:
        # 如果配置了 alert_bot_ids，只处理来自指定 bot 的消息
        if self.alert_bot_ids and sender_id and sender_id not in self.alert_bot_ids:
            return False
        # 忽略恢复消息
        if self.ignore_pattern.search(text):
            return False
        return bool(self.alert_pattern.search(text))
