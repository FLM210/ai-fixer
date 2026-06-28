# 测试

了解 ai-fixer 的测试策略和工具。

## 测试结构

```
tests/
├── conftest.py               # 测试配置和 fixtures
├── api/                      # API 端点测试
│   ├── test_incidents.py
│   ├── test_config.py
│   └── test_plugins.py
├── graph/                    # LangGraph 工作流测试
│   ├── test_workflow.py
│   └── test_nodes.py
├── plugins/                  # 插件测试
│   ├── test_k8s_plugins.py
│   ├── test_db_plugins.py
│   └── test_monitoring_plugins.py
├── llm/                      # LLM 客户端测试
│   └── test_clients.py
├── lark/                     # 飞书集成测试
│   ├── test_alert_detector.py
│   └── test_card_renderer.py
└── integration/              # 集成测试
    └── test_e2e.py
```

## 运行测试

### 运行所有测试

```bash
make test
```

### 运行特定测试

```bash
# 运行单个文件
pytest tests/plugins/test_k8s_plugins.py -v

# 运行单个测试
pytest tests/plugins/test_k8s_plugins.py::test_list_pods -v

# 运行匹配模式的测试
pytest tests/ -k "test_list" -v
```

### 运行带覆盖率

```bash
pytest --cov=app --cov-report=term-missing

# 生成 HTML 报告
pytest --cov=app --cov-report=html
# 报告在 htmlcov/ 目录
```

### 运行特定标记的测试

```bash
# 运行单元测试
pytest -m unit -v

# 运行集成测试
pytest -m integration -v

# 跳过慢测试
pytest -m "not slow" -v
```

## 编写测试

### 基本测试结构

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_my_function():
    # 准备（Arrange）
    input_data = {"key": "value"}
    expected = {"success": True}

    # 执行（Act）
    result = await my_function(input_data)

    # 验证（Assert）
    assert result == expected
```

### 使用 Fixtures

```python
# conftest.py
import pytest
from app.models import Incident

@pytest.fixture
def sample_incident():
    """创建示例 Incident"""
    return Incident(
        id="INC-20240115-001",
        title="Test Incident",
        status="pending",
    )

@pytest.fixture
async def db_session():
    """数据库会话"""
    async with async_session_maker() as session:
        yield session
        await session.rollback()

# test_my_feature.py
@pytest.mark.asyncio
async def test_with_fixture(sample_incident, db_session):
    db_session.add(sample_incident)
    await db_session.commit()

    result = await db_session.get(Incident, sample_incident.id)
    assert result is not None
```

### Mock 外部服务

```python
@pytest.mark.asyncio
async def test_llm_call():
    # Mock LLM 客户端
    mock_llm = AsyncMock()
    mock_llm.chat.return_value = {
        "content": "诊断结果",
        "tool_calls": []
    }

    # 使用 mock
    with patch("app.llm.client", mock_llm):
        result = await diagnose("test alert")

    # 验证 mock 被调用
    mock_llm.chat.assert_called_once()
    assert result["conclusion"] == "诊断结果"
```

### 测试插件

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_list_pods_plugin():
    # Mock K8s 客户端
    mock_k8s = AsyncMock()
    mock_k8s.list_pods.return_value = [
        {"name": "pod-1", "status": "Running"},
        {"name": "pod-2", "status": "Running"},
    ]

    # 创建插件实例
    from app.plugins.builtin.k8s import ListPodsPlugin
    plugin = ListPodsPlugin(client=mock_k8s)

    # 执行插件
    result = await plugin.execute(namespace="default")

    # 验证
    assert result["success"] is True
    assert len(result["data"]) == 2
    mock_k8s.list_pods.assert_called_once_with(namespace="default")
```

### 测试 API 端点

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_incidents(client: AsyncClient):
    response = await client.get("/api/incidents")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "items" in data["data"]

@pytest.mark.asyncio
async def test_create_incident(client: AsyncClient):
    payload = {
        "title": "Test Incident",
        "description": "Test description",
    }

    response = await client.post("/api/incidents", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["title"] == "Test Incident"
```

### 测试工作流

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_workflow_triage():
    # Mock 依赖
    mock_llm = AsyncMock()
    mock_db = AsyncMock()

    # 创建工作流状态
    state = {
        "alert": {
            "message": "Test alert",
            "sender_id": "bot_123",
        },
        "incident_id": "INC-20240115-001",
    }

    # 执行 triage 节点
    from app.graph.nodes import triage
    result = await triage(state)

    # 验证
    assert result["category"] == "kubernetes"
    assert result["skip"] is False
```

## Mock 工具

### HTTP Mock (respx)

```python
import respx
import httpx

@pytest.mark.asyncio
async def test_external_api():
    with respx.mock:
        respx.get("https://api.example.com/data").mock(
            return_value=httpx.Response(200, json={"result": "ok"})
        )

        result = await fetch_data()
        assert result == {"result": "ok"}
```

### K8s Mock (FakeK8sClient)

```python
from app.k8s.client import FakeK8sClient

@pytest.mark.asyncio
async def test_k8s_operation():
    # 使用 fake 客户端
    client = FakeK8sClient()

    # 预设数据
    client.pods = [
        {"name": "pod-1", "status": "Running"},
    ]

    # 执行操作
    result = await client.list_pods(namespace="default")

    # 验证
    assert len(result) == 1
    assert result[0]["name"] == "pod-1"
```

### LLM Mock

```python
from unittest.mock import AsyncMock

@pytest.fixture
def mock_llm():
    client = AsyncMock()
    client.chat.return_value = {
        "content": "诊断结果",
        "tool_calls": [
            {
                "name": "list_pods",
                "parameters": {"namespace": "default"},
            }
        ],
    }
    return client

@pytest.mark.asyncio
async def test_diagnosis(mock_llm):
    with patch("app.llm.client", mock_llm):
        result = await diagnose("test alert")

    assert result["conclusion"] == "诊断结果"
```

## 测试配置

### conftest.py

```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.base import async_session_maker

@pytest.fixture
async def client():
    """HTTP 客户端"""
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c

@pytest.fixture
async def db():
    """数据库会话"""
    async with async_session_maker() as session:
        yield session
        await session.rollback()

@pytest.fixture(autouse=True)
def _registry_snapshot():
    """每个测试用例自动隔离全局插件注册表"""
    from app.plugins.registry import global_registry
    snapshot = global_registry.snapshot()
    yield
    global_registry.restore(snapshot)
```

### pytest.ini

```ini
[pytest]
asyncio_mode = "auto"
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    unit: 单元测试
    integration: 集成测试
    slow: 慢测试
```

## 测试最佳实践

### 1. 测试命名

```python
# 好的命名
def test_list_pods_returns_all_pods_in_namespace():
    ...

def test_diagnose_returns_high_confidence_for_oomkilled():
    ...

# 不好的命名
def test_1():
    ...

def test_pods():
    ...
```

### 2. 测试隔离

```python
# 每个测试独立，不依赖执行顺序
@pytest.mark.asyncio
async def test_create_incident():
    incident = await create_incident({"title": "Test"})
    assert incident.id is not None

@pytest.mark.asyncio
async def test_get_incident():
    # 不依赖上面的测试
    incident = await create_incident({"title": "Test"})
    result = await get_incident(incident.id)
    assert result is not None
```

### 3. 测试覆盖率

```bash
# 查看覆盖率报告
pytest --cov=app --cov-report=term-missing

# 目标：核心模块 > 80%
```

### 4. 测试速度

```python
# 使用 mock 避免真实网络请求
@pytest.mark.asyncio
async def test_with_mock():
    with patch("app.external.api_call", new_callable=AsyncMock) as mock:
        mock.return_value = {"result": "ok"}
        result = await my_function()
        assert result["success"] is True
```

## 集成测试

### 端到端测试

```python
# tests/integration/test_e2e.py
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_alert_flow(client, db):
    """测试完整的告警处理流程"""

    # 1. 发送告警
    response = await client.post("/api/alert", json={
        "message": "[告警] Pod CrashLoopBackOff",
        "sender_id": "test_bot",
    })
    assert response.status_code == 200
    incident_id = response.json()["data"]["incident_id"]

    # 2. 等待诊断完成
    # ...

    # 3. 确认诊断
    # ...

    # 4. 确认方案
    # ...

    # 5. 验证执行结果
    incident = await get_incident(incident_id)
    assert incident.status == "resolved"
```

### CI 测试

GitHub Actions 自动运行测试：

```yaml
# .github/workflows/ci.yml
- name: Test
  run: uv run pytest --cov=app --cov-report=term-missing
```

## 故障排查

### 测试失败

```bash
# 查看详细输出
pytest -v --tb=long

# 查看 print 输出
pytest -s

# 进入调试器
pytest --pdb
```

### 数据库测试问题

```bash
# 清理测试数据库
docker-compose exec postgres psql -U fixer -c "DROP DATABASE IF EXISTS fixer_test;"

# 重新创建
docker-compose exec postgres psql -U fixer -c "CREATE DATABASE fixer_test;"
```

### Mock 问题

```bash
# 检查 mock 是否正确设置
pytest -v --tb=short -k "test_my_function"
```

## 下一步

- [贡献指南](/development/contributing) - 贡献测试用例
- [插件开发](/development/plugin-dev) - 插件测试
- [架构设计](/development/architecture) - 测试架构
