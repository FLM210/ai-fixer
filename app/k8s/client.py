from abc import ABC, abstractmethod
from typing import Any


class K8sClient(ABC):
    @abstractmethod
    async def describe_pod(self, namespace: str, name: str) -> dict[str, Any]:
        """返回 pod 的 status / containers / events 摘要。"""

    @abstractmethod
    async def get_pod_logs(
        self, namespace: str, name: str, *, container: str | None = None, tail_lines: int = 200
    ) -> str: ...

    @abstractmethod
    async def list_pods(
        self, namespace: str, *, label_selector: str | None = None
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def describe_node(self, node_name: str) -> dict[str, Any]: ...

    @abstractmethod
    async def get_events(
        self, namespace: str, *, field_selector: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def top_pods(self, namespace: str, *, sort_by: str = "cpu") -> list[dict[str, Any]]: ...

    @abstractmethod
    async def delete_pod(self, namespace: str, pod_name: str) -> dict[str, Any]: ...

    @abstractmethod
    async def scale_deployment(
        self, namespace: str, name: str, replicas: int
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def rollback_deployment(
        self, namespace: str, name: str, *, revision: int | None = None
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def cordon_node(self, node_name: str) -> dict[str, Any]: ...

    @abstractmethod
    async def delete_evicted_pods(self, namespace: str) -> dict[str, Any]: ...

    @abstractmethod
    async def exec_kubectl(self, command: str) -> dict[str, Any]:
        """执行原始 kubectl 命令,返回 stdout/stderr/exit_code。"""


class FakeK8sClient(K8sClient):
    """开发/测试用的 fake client,记录调用并返回固定 payload。"""

    def __init__(self, *, describe_pod_payload: dict[str, Any] | None = None) -> None:
        self._describe_payload = describe_pod_payload or {
            "phase": "Running",
            "containers": [{"name": "app", "ready": True, "restartCount": 0}],
            "events": [],
        }
        self.calls: list[dict[str, Any]] = []

    async def describe_pod(self, namespace: str, name: str) -> dict[str, Any]:
        self.calls.append({"action": "describe_pod", "namespace": namespace, "name": name})
        return self._describe_payload

    async def get_pod_logs(
        self, namespace: str, name: str, *, container: str | None = None, tail_lines: int = 200
    ) -> str:
        self.calls.append(
            {
                "action": "get_pod_logs",
                "namespace": namespace,
                "name": name,
                "container": container,
                "tail_lines": tail_lines,
            }
        )
        return "fake log line\n"

    async def list_pods(
        self, namespace: str, *, label_selector: str | None = None
    ) -> list[dict[str, Any]]:
        self.calls.append(
            {
                "action": "list_pods",
                "namespace": namespace,
                "label_selector": label_selector,
            }
        )
        return []

    async def describe_node(self, node_name: str) -> dict[str, Any]:
        self.calls.append({"action": "describe_node", "node_name": node_name})
        return {"node": node_name, "status": "Ready"}

    async def get_events(
        self, namespace: str, *, field_selector: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        self.calls.append(
            {
                "action": "get_events",
                "namespace": namespace,
                "field_selector": field_selector,
                "limit": limit,
            }
        )
        return []

    async def top_pods(self, namespace: str, *, sort_by: str = "cpu") -> list[dict[str, Any]]:
        self.calls.append({"action": "top_pods", "namespace": namespace, "sort_by": sort_by})
        return []

    async def delete_pod(self, namespace: str, pod_name: str) -> dict[str, Any]:
        self.calls.append({"action": "delete_pod", "namespace": namespace, "pod_name": pod_name})
        return {"status": "deleted"}

    async def scale_deployment(self, namespace: str, name: str, replicas: int) -> dict[str, Any]:
        self.calls.append(
            {
                "action": "scale_deployment",
                "namespace": namespace,
                "name": name,
                "replicas": replicas,
            }
        )
        return {"replicas": replicas}

    async def rollback_deployment(
        self, namespace: str, name: str, *, revision: int | None = None
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "action": "rollback_deployment",
                "namespace": namespace,
                "name": name,
                "revision": revision,
            }
        )
        return {"revision": revision or 1}

    async def cordon_node(self, node_name: str) -> dict[str, Any]:
        self.calls.append({"action": "cordon_node", "node_name": node_name})
        return {"cordoned": True}

    async def delete_evicted_pods(self, namespace: str) -> dict[str, Any]:
        self.calls.append({"action": "delete_evicted_pods", "namespace": namespace})
        return {"deleted_count": 0}

    async def exec_kubectl(self, command: str) -> dict[str, Any]:
        self.calls.append({"action": "exec_kubectl", "command": command})
        return {"stdout": "", "stderr": "", "exit_code": 0}
