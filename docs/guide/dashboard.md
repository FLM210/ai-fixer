# 管理后台

ai-fixer 提供 React 前端管理后台，用于配置管理、Incident 查看和插件管理。

## 访问地址

- 开发模式：http://localhost:5173
- 生产模式：http://localhost:8080（通过 FastAPI 托管）

## 功能模块

### 1. 仪表盘（Dashboard）

系统状态概览：

- 活跃 Incident 数量
- 最近告警统计
- 系统健康状态
- 插件状态

访问：http://localhost:5173/

### 2. Incident 管理

查看和管理告警处理记录：

- Incident 列表（分页、筛选）
- Incident 详情（诊断、方案、执行结果）
- LLM 对话历史
- 工具调用记录

访问：http://localhost:5173/incidents

#### Incident 状态

| 状态 | 说明 |
|------|------|
| `pending` | 等待处理 |
| `diagnosing` | 诊断中 |
| `awaiting_diagnosis_approval` | 等待诊断确认 |
| `proposing` | 生成方案中 |
| `awaiting_proposal_approval` | 等待方案确认 |
| `executing` | 执行中 |
| `resolved` | 已解决 |
| `escalated` | 已升级 |
| `failed` | 失败 |

### 3. 配置管理

动态配置系统参数：

#### LLM 配置

| 参数 | 说明 | 示例值 |
|------|------|--------|
| `LLM_PROVIDER` | LLM 提供商 | `anthropic` |
| `LLM_API_KEY` | API 密钥 | `sk-xxxxxxxx` |
| `LLM_MODEL` | 模型名称 | `claude-3-5-sonnet-20241022` |
| `LLM_BASE_URL` | 自定义端点 | `https://api.anthropic.com` |
| `LLM_TIMEOUT` | 超时时间（秒） | `300` |

#### 飞书配置

| 参数 | 说明 | 示例值 |
|------|------|--------|
| `LARK_APP_ID` | 应用 ID | `cli_xxxxxxxx` |
| `LARK_APP_SECRET` | 应用密钥 | `xxxxxxxx` |
| `ALERT_BOT_IDS` | 告警机器人 ID | `cli_xxx,cli_yyy` |

#### 安全围栏配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `ALLOWED_NAMESPACES` | 允许的命名空间 | `default,production` |
| `MAX_REPLICA_CHANGE` | 最大副本变更比例 | `0.5` |
| `FORBIDDEN_VERBS` | 禁止的命令 | `rm -rf,drop table` |
| `HOURLY_QUOTA` | 每小时配额 | `10` |

访问：http://localhost:5173/config

### 4. 插件管理

查看已注册的插件：

- 插件列表
- 插件详情（参数、描述）
- 插件状态

访问：http://localhost:5173/plugins

### 5. 知识库管理

管理运维知识条目：

- 知识条目列表
- 创建/编辑知识
- 版本历史
- 向量检索

访问：http://localhost:5173/knowledge

## 开发模式

### 启动开发服务器

```bash
make dev-ui
```

启动 Vite 开发服务器，支持热重载。

### 访问地址

- 前端：http://localhost:5173
- API 代理：自动代理 `/api` 到后端 8080

### 开发配置

编辑 `frontend/vite.config.ts`：

```typescript
export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
})
```

## 生产构建

### 构建静态文件

```bash
make build-ui
```

生成的文件在 `frontend/dist/` 目录。

### 托管方式

生产模式下，FastAPI 通过 `StaticFiles` 托管前端：

```python
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="frontend/dist", html=True))
```

## 技术栈

- **框架**：React 19
- **构建工具**：Vite 8
- **语言**：TypeScript
- **样式**：Tailwind CSS 4
- **组件库**：shadcn/ui
- **路由**：React Router
- **HTTP 客户端**：Axios
- **状态管理**：React Hooks

## 自定义开发

### 添加新页面

1. 创建页面组件：

```typescript
// frontend/src/pages/MyPage.tsx
export default function MyPage() {
  return (
    <div>
      <h1>My Page</h1>
    </div>
  )
}
```

2. 添加路由：

```typescript
// frontend/src/App.tsx
import MyPage from './pages/MyPage'

// 在路由配置中添加
<Route path="/my-page" element={<MyPage />} />
```

3. 添加侧边栏菜单：

```typescript
// frontend/src/components/Layout.tsx
{
  title: 'My Page',
  path: '/my-page',
  icon: SomeIcon,
}
```

### 添加 API 调用

1. 创建 API 模块：

```typescript
// frontend/src/api/my-api.ts
import axios from 'axios'

export async function getMyData() {
  const response = await axios.get('/api/my-data')
  return response.data
}
```

2. 使用自定义 Hook：

```typescript
// frontend/src/hooks/useMyData.ts
import { useState, useEffect } from 'react'
import { getMyData } from '../api/my-api'

export function useMyData() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getMyData().then(setData).finally(() => setLoading(false))
  }, [])

  return { data, loading }
}
```

### 添加新组件

使用 shadcn/ui 组件：

```typescript
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export function MyComponent() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>My Component</CardTitle>
      </CardHeader>
      <CardContent>
        <Button>Click me</Button>
      </CardContent>
    </Card>
  )
}
```

## 故障排查

### 页面无法访问

```bash
# 检查前端服务是否运行
docker-compose ps

# 检查端口是否占用
lsof -i :5173

# 查看日志
docker-compose logs app
```

### API 请求失败

```bash
# 检查后端服务
curl http://localhost:8080/health

# 检查代理配置
# 查看 vite.config.ts 中的 proxy 配置
```

### 样式问题

```bash
# 清除缓存
rm -rf frontend/node_modules/.vite

# 重新构建
make build-ui
```

## 下一步

- [告警处理](/guide/alerts) - 了解告警处理流程
- [配置管理](/guide/configuration) - 详细配置说明
- [API 文档](/api/) - 后端 API 接口
