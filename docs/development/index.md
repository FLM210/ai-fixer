# 开发指南

本地开发环境配置和开发流程。

## 环境要求

- Python 3.11+
- Node.js 18+（前端开发）
- Docker
- Git
- PostgreSQL 14+（已部署）
- Redis 6.0+（已部署）

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/FLM210/ai-fixer.git
cd ai-fixer
```

### 2. 安装依赖

```bash
make install
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置数据库和 Redis 连接：

```bash
DATABASE_URL=postgresql+asyncpg://user:password@your-postgres-host:5432/fixer
REDIS_URL=redis://your-redis-host:6379/0
```

### 4. 执行数据库迁移

```bash
make migrate
```

### 5. 启动后端

```bash
make run
```

### 6. 启动前端（可选）

```bash
make dev-ui
```

## 开发命令

### 代码质量

```bash
make lint       # 代码检查（ruff）
make fmt        # 代码格式化
make type       # 类型检查（mypy）
```

### 测试

```bash
make test       # 运行所有测试
pytest tests/path/to/test_file.py::test_name -v  # 运行单个测试
```

### 数据库

```bash
make migrate              # 执行迁移
make migrate-create       # 创建迁移文件
make migrate-rollback     # 回滚迁移
```

### 前端

```bash
make build-ui   # 构建前端
make dev-ui     # 启动开发服务器
```

## 项目结构

```
ai-fixer/
├── app/
│   ├── api/                    # API 路由
│   ├── config/                 # 配置管理
│   │   ├── settings.py         # Pydantic Settings
│   │   └── dynamic.py          # 动态配置
│   ├── engine/                 # 执行策略引擎
│   │   └── policy.py
│   ├── graph/                  # LangGraph 工作流
│   │   ├── state.py            # GraphState
│   │   └── nodes.py            # 工作流节点
│   ├── k8s/                    # Kubernetes 客户端
│   │   └── client.py
│   ├── knowledge/              # 知识库
│   ├── lark/                   # 飞书集成
│   │   ├── client.py           # LarkClient
│   │   ├── alert_detector.py   # 告警检测
│   │   ├── card_renderer.py    # 卡片渲染
│   │   └── workflow_manager.py # 工作流管理
│   ├── llm/                    # LLM 客户端
│   │   ├── base.py             # LLMClient ABC
│   │   ├── anthropic.py        # Anthropic 实现
│   │   └── openai.py           # OpenAI 实现
│   ├── memory/                 # 向量记忆
│   ├── models/                 # SQLAlchemy 模型
│   ├── observability/          # 日志和监控
│   ├── plugins/                # 插件系统
│   │   ├── base.py             # Plugin ABC
│   │   ├── registry.py         # 插件注册表
│   │   └── builtin/            # 内置插件
│   ├── telemetry/              # 可观测性
│   ├── utils/                  # 工具函数
│   └── main.py                 # FastAPI 应用
├── alembic/                    # 数据库迁移
├── deploy/                     # 部署配置
│   ├── helm/                   # Helm Chart
│   ├── grafana/                # Grafana Dashboard
│   └── docker-compose.prod.yml
├── docs/                       # 文档
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── api/                # API 调用
│   │   ├── components/         # 组件
│   │   ├── hooks/              # 自定义 Hooks
│   │   └── pages/              # 页面
│   └── package.json
├── tests/                      # 测试
├── custom_plugins/             # 自定义插件
├── Makefile
├── docker-compose.yml
└── pyproject.toml
```

## 开发流程

### 1. 创建功能分支

```bash
git checkout -b feature/my-feature
```

### 2. 开发功能

编写代码和测试。

### 3. 运行测试

```bash
make test
```

### 4. 代码检查

```bash
make lint
make type
```

### 5. 提交代码

```bash
git add .
git commit -m "feat: 添加新功能"
```

### 6. 推送并创建 PR

```bash
git push origin feature/my-feature
```

## 添加新功能

### 添加新 API 端点

1. 创建路由文件：

```python
# app/api/my_feature.py
from fastapi import APIRouter, Depends

router = APIRouter()

@router.get("/api/my-feature")
async def get_my_feature():
    return {"message": "Hello"}
```

2. 注册路由：

```python
# app/main.py
from app.api.my_feature import router as my_feature_router

app.include_router(my_feature_router)
```

3. 添加测试：

```python
# tests/api/test_my_feature.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_my_feature(client: AsyncClient):
    response = await client.get("/api/my-feature")
    assert response.status_code == 200
```

### 添加新插件

详见 [插件开发](/guide/plugins)

### 添加新数据库模型

1. 创建模型：

```python
# app/models/my_model.py
from sqlalchemy import Column, Integer, String
from app.models.base import Base

class MyModel(Base):
    __tablename__ = "my_model"
    __table_args__ = {"schema": "fixer"}

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
```

2. 创建迁移：

```bash
make migrate-create
```

3. 编辑迁移文件并执行：

```bash
make migrate
```

## 测试

### 测试结构

```
tests/
├── conftest.py               # 测试配置
├── api/                      # API 测试
├── graph/                    # 工作流测试
├── plugins/                  # 插件测试
└── integration/              # 集成测试
```

### 运行测试

```bash
# 运行所有测试
make test

# 运行特定测试
pytest tests/plugins/test_my_plugin.py -v

# 运行带覆盖率
pytest --cov=app --cov-report=term-missing
```

### 编写测试

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_my_function():
    # 准备
    mock_client = AsyncMock()
    mock_client.fetch_data.return_value = {"result": "ok"}

    # 执行
    with patch("app.my_module.client", mock_client):
        result = await my_function()

    # 验证
    assert result["success"] is True
    mock_client.fetch_data.assert_called_once()
```

### Mock 工具

- **HTTP Mock**：`respx`
- **K8s Mock**：`FakeK8sClient`
- **LLM Mock**：自定义 mock

## 调试

### 日志

使用 `structlog` 结构化日志：

```python
import structlog

logger = structlog.get_logger()

async def my_function():
    logger.info("my_function.start", param="value")
    try:
        result = await do_something()
        logger.info("my_function.success", result=result)
    except Exception as e:
        logger.error("my_function.failed", error=str(e))
```

### 断点调试

```python
# 使用 Python 调试器
import pdb; pdb.set_trace()

# 或使用 VS Code 调试器
# 在 .vscode/launch.json 中配置
```

### 查看数据库

```bash
# 连接数据库
docker-compose exec postgres psql -U fixer -d fixer

# 查看表
\dt fixer.*

# 查询数据
SELECT * FROM fixer.incidents LIMIT 10;
```

## 代码风格

### Python

- Python 3.11+
- 全部 async/await
- Ruff 规则：E/F/W/I/B/UP/ASYNC/SIM/RUF
- 行宽 100
- 类型注解严格（mypy strict mode）

### TypeScript

- TypeScript 严格模式
- ESLint + Prettier
- 函数式组件 + Hooks

## 下一步

- [架构设计](/development/architecture) - 深入了解架构
- [插件开发](/development/plugin-dev) - 开发自定义插件
- [贡献指南](/development/contributing) - 贡献代码
