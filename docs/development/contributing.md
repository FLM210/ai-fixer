# 贡献指南

欢迎为 ai-fixer 贡献代码！

## 开发流程

### 1. Fork 项目

在 GitHub 上 Fork 项目到你的账号。

### 2. 克隆代码

```bash
git clone https://github.com/YOUR_USERNAME/ai-fixer.git
cd ai-fixer
```

### 3. 创建功能分支

```bash
git checkout -b feature/my-feature
```

### 4. 开发功能

编写代码和测试。

### 5. 运行测试

```bash
make test
make lint
make type
```

### 6. 提交代码

```bash
git add .
git commit -m "feat: 添加新功能"
```

### 7. 推送并创建 PR

```bash
git push origin feature/my-feature
```

在 GitHub 上创建 Pull Request。

## Commit 规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

### 类型

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `style` | 代码格式（不影响逻辑） |
| `refactor` | 重构（不是新功能也不是修复） |
| `perf` | 性能优化 |
| `test` | 测试相关 |
| `chore` | 构建/工具相关 |

### 示例

```bash
feat: 添加 Redis 缓存支持
fix: 修复 Pod 状态查询失败
docs: 更新部署文档
refactor: 重构插件注册逻辑
test: 添加 LLM 客户端测试
```

### 范围（可选）

```bash
feat(plugins): 添加自定义插件支持
fix(lark): 修复消息发送失败
docs(deployment): 更新 K8s 部署文档
```

## 代码风格

### Python

- Python 3.11+
- 全部 async/await
- Ruff 规则：E/F/W/I/B/UP/ASYNC/SIM/RUF
- 行宽 100
- 类型注解严格（mypy strict mode）

```bash
# 格式化代码
make fmt

# 检查代码
make lint

# 类型检查
make type
```

### TypeScript

- TypeScript 严格模式
- ESLint + Prettier
- 函数式组件 + Hooks

```bash
# 进入前端目录
cd frontend

# 检查代码
npm run lint

# 格式化
npm run format
```

## 提交 PR

### PR 标题

使用与 commit 相同的规范：

```
feat: 添加自定义插件支持
fix: 修复告警检测误判
```

### PR 描述

包含以下内容：

1. **变更说明**：做了什么，为什么做
2. **测试情况**：如何测试的
3. **相关 Issue**：关联的 Issue 编号

示例：

```markdown
## 变更说明

添加自定义插件支持，允许用户将自定义插件放入 `custom_plugins/` 目录自动加载。

## 测试情况

- [x] 添加单元测试
- [x] 手动测试自定义插件加载
- [x] 运行完整测试套件

## 相关 Issue

Closes #123
```

### 代码审查

- 至少需要一个 maintainer 审核通过
- 自动运行 CI 测试（lint、type check、test）
- 解决所有 review comments

## 贡献类型

### 1. Bug 修复

```bash
# 创建分支
git checkout -b fix/bug-description

# 修复并测试
# ...

# 提交
git commit -m "fix: 修复 XXX 问题"
```

### 2. 新功能

```bash
# 创建分支
git checkout -b feature/feature-name

# 开发并测试
# ...

# 提交
git commit -m "feat: 添加 XXX 功能"
```

### 3. 文档更新

```bash
# 创建分支
git checkout -b docs/update-docs

# 更新文档
# ...

# 提交
git commit -m "docs: 更新 XXX 文档"
```

### 4. 新插件

```bash
# 创建分支
git checkout -b feat/add-my-plugin

# 开发插件
# ...

# 提交
git commit -m "feat(plugins): 添加 XXX 插件"
```

## 开发环境

### 快速启动

```bash
# 克隆项目
git clone https://github.com/YOUR_USERNAME/ai-fixer.git
cd ai-fixer

# 安装依赖
make install

# 配置环境变量
cp .env.example .env
# 编辑 .env 配置数据库和 Redis 连接

# 执行迁移
make migrate

# 启动服务
make run
```

> **注意**：需要先准备好 PostgreSQL 和 Redis 服务，并在 `.env` 中配置连接信息。

### 运行测试

```bash
# 运行所有测试
make test

# 运行特定测试
pytest tests/path/to/test.py -v

# 运行带覆盖率
pytest --cov=app --cov-report=term-missing
```

## 常见贡献

### 添加新插件

1. 在 `app/plugins/builtin/` 创建新文件
2. 继承 `Plugin` ABC
3. 实现 `spec` 和 `execute`
4. 使用 `@register` 装饰器
5. 添加测试
6. 更新文档

示例：

```python
# app/plugins/builtin/my_plugin.py
from app.plugins.base import Plugin, PluginSpec, register
from app.plugins.registry import global_registry

@register(global_registry)
class MyPlugin(Plugin):
    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="my_plugin",
            description="我的插件",
            category="diagnostic",
            parameters={...},
        )

    async def execute(self, **kwargs) -> dict:
        return {"success": True, "data": {...}}
```

### 添加新 API 端点

1. 在 `app/api/` 创建路由文件
2. 定义端点
3. 注册路由
4. 添加测试
5. 更新文档

示例：

```python
# app/api/my_feature.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/api/my-feature")
async def get_my_feature():
    return {"message": "Hello"}
```

### 修复 Bug

1. 在 GitHub Issue 中描述问题
2. 创建修复分支
3. 编写测试复现问题
4. 修复代码
5. 验证测试通过
6. 提交 PR

## 社区

### 获取帮助

- **GitHub Issues**：报告 Bug 或提出功能请求
- **讨论区**：提问和讨论
- **文档**：查阅文档

### 行为准则

- 尊重他人
- 建设性反馈
- 包容性语言
- 专注于技术讨论

## 奖励

### 贡献者列表

所有贡献者都会被添加到 README 和文档中。

### 特别贡献

重大贡献者可能获得：
- 项目维护者权限
- 特别感谢
- 其他奖励

## 下一步

- [开发指南](/development/) - 开发环境配置
- [插件开发](/development/plugin-dev) - 开发自定义插件
- [测试](/development/testing) - 测试策略
