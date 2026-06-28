# Kubernetes 部署

使用 Helm Chart 在 Kubernetes 集群中部署 ai-fixer。

> **重要**：ai-fixer 只负责应用本身，PostgreSQL 和 Redis 作为独立的基础设施服务，请提前准备好连接信息。

## 前置要求

- Kubernetes 1.24+
- Helm 3.0+
- kubectl 已配置
- PostgreSQL 14+ 已部署（外部服务）
- Redis 6.0+ 已部署（外部服务）

## 快速部署

### 1. 克隆项目

```bash
git clone https://github.com/FLM210/ai-fixer.git
cd ai-fixer/deploy/helm/k8s-fixer
```

### 2. 创建命名空间

```bash
kubectl create namespace ai-fixer
```

### 3. 创建 Secret

```bash
kubectl create secret generic ai-fixer-secrets \
  --from-literal=database-url='postgresql+asyncpg://user:password@your-postgres-host:5432/fixer' \
  --from-literal=redis-url='redis://your-redis-host:6379/0' \
  --from-literal=llm-api-key='sk-xxxxxxxx' \
  -n ai-fixer
```

### 4. 配置 values.yaml

```bash
cp values.yaml my-values.yaml
```

编辑 `my-values.yaml`：

```yaml
# 镜像配置
image:
  repository: hahtangtang/ai-fixer
  tag: latest

# 副本数
replicaCount: 1

# 服务配置
service:
  type: ClusterIP
  port: 8080

# 环境变量
env:
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: ai-fixer-secrets
        key: database-url
  - name: REDIS_URL
    valueFrom:
      secretKeyRef:
        name: ai-fixer-secrets
        key: redis-url
  - name: LLM_API_KEY
    valueFrom:
      secretKeyRef:
        name: ai-fixer-secrets
        key: llm-api-key

# 配置
config:
  LLM_PROVIDER: "anthropic"
  LLM_MODEL: "claude-3-5-sonnet-20241022"
  LOG_LEVEL: "info"

# 不需要创建 Secret（已手动创建）
secrets:
  create: false
```

### 5. 部署

```bash
helm install ai-fixer . -n ai-fixer -f my-values.yaml
```

### 6. 验证部署

```bash
# 查看 Pod 状态
kubectl get pods -n ai-fixer

# 查看服务
kubectl get svc -n ai-fixer

# 查看日志
kubectl logs -f deployment/ai-fixer -n ai-fixer
```

## 详细配置

### values.yaml 完整配置

```yaml
# 镜像配置
image:
  repository: hahtangtang/ai-fixer
  tag: latest
  pullPolicy: IfNotPresent

# 副本数
replicaCount: 1

# 服务配置
service:
  type: ClusterIP
  port: 8080

# Ingress 配置
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: ai-fixer.your-domain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: ai-fixer-tls
      hosts:
        - ai-fixer.your-domain.com

# 环境变量
env:
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: ai-fixer-secrets
        key: database-url
  - name: REDIS_URL
    valueFrom:
      secretKeyRef:
        name: ai-fixer-secrets
        key: redis-url
  - name: LLM_API_KEY
    valueFrom:
      secretKeyRef:
        name: ai-fixer-secrets
        key: llm-api-key

# 配置
config:
  LLM_PROVIDER: "anthropic"
  LLM_MODEL: "claude-3-5-sonnet-20241022"
  LOG_LEVEL: "info"

# 资源限制
resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 2000m
    memory: 2Gi

# 健康检查
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5

# 自动扩缩容
autoscaling:
  enabled: true
  minReplicas: 1
  maxReplicas: 5
  targetCPUUtilizationPercentage: 80

# RBAC
rbac:
  create: true

# ServiceAccount
serviceAccount:
  create: true
  name: ai-fixer
```

### 数据库迁移 Job

Helm Chart 包含数据库迁移 Job（首次部署或升级时运行）：

```yaml
# templates/migrate-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "ai-fixer.fullname" . }}-migrate
spec:
  template:
    spec:
      containers:
        - name: migrate
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          command: ["alembic", "upgrade", "head"]
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: ai-fixer-secrets
                  key: database-url
      restartPolicy: OnFailure
```

手动运行迁移：

```bash
kubectl create job --from=cronjob/ai-fixer-migrate ai-fixer-migrate-manual -n ai-fixer
```

### 清理 CronJob

定期清理超时的工作流：

```yaml
# templates/cleanup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: {{ include "ai-fixer.fullname" . }}-cleanup
spec:
  schedule: "0 */1 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: cleanup
              image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
              command: ["python", "-m", "app.utils.cleanup"]
```

## RBAC 配置

### ServiceAccount

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ai-fixer
  namespace: ai-fixer
```

### ClusterRole

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: ai-fixer
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "endpoints", "events"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments", "replicasets"]
    verbs: ["get", "list", "watch", "update", "patch"]
  - apiGroups: [""]
    resources: ["pods/log"]
    verbs: ["get"]
```

### ClusterRoleBinding

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: ai-fixer
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: ai-fixer
subjects:
  - kind: ServiceAccount
    name: ai-fixer
    namespace: ai-fixer
```

## 监控配置

### ServiceMonitor

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: ai-fixer
  namespace: ai-fixer
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: ai-fixer
  endpoints:
    - port: http
      path: /metrics
      interval: 30s
```

### Grafana Dashboard

导入预置的 Dashboard：

```bash
# 获取 Dashboard JSON
cat deploy/grafana/k8s-fixer-overview.json

# 在 Grafana 中导入
# 1. 打开 Grafana
# 2. Dashboards → Import
# 3. 上传 JSON 文件
# 4. 选择 Prometheus 数据源
```

## 升级

### 更新配置

```bash
helm upgrade ai-fixer . -n ai-fixer -f my-values.yaml
```

### 更新镜像

```bash
helm upgrade ai-fixer . -n ai-fixer \
  --set image.tag=v1.1.0
```

### 运行数据库迁移

升级后可能需要运行数据库迁移：

```bash
kubectl create job --from=cronjob/ai-fixer-migrate ai-fixer-migrate-$(date +%s) -n ai-fixer
```

### 回滚

```bash
# 查看历史
helm history ai-fixer -n ai-fixer

# 回滚到指定版本
helm rollback ai-fixer 1 -n ai-fixer
```

## 卸载

```bash
helm uninstall ai-fixer -n ai-fixer
kubectl delete namespace ai-fixer
```

## 故障排查

### Pod 启动失败

```bash
# 查看 Pod 详情
kubectl describe pod -l app.kubernetes.io/name=ai-fixer -n ai-fixer

# 查看日志
kubectl logs -l app.kubernetes.io/name=ai-fixer -n ai-fixer

# 查看事件
kubectl get events -n ai-fixer --sort-by='.lastTimestamp'
```

### 数据库连接失败

```bash
# 检查 Secret
kubectl get secret ai-fixer-secrets -n ai-fixer -o yaml

# 测试连接
kubectl exec -it deployment/ai-fixer -n ai-fixer -- python -c "
from app.config.settings import settings
print(settings.DATABASE_URL)
"
```

### 内存不足

```bash
# 查看资源使用
kubectl top pods -n ai-fixer

# 调整资源限制
helm upgrade ai-fixer . -n ai-fixer \
  --set resources.limits.memory=4Gi
```

## 最佳实践

### 1. 使用命名空间隔离

```bash
kubectl create namespace ai-fixer
```

### 2. 配置资源限制

```yaml
resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 2000m
    memory: 2Gi
```

### 3. 启用自动扩缩容

```yaml
autoscaling:
  enabled: true
  minReplicas: 1
  maxReplicas: 5
```

### 4. 配置健康检查

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
readinessProbe:
  httpGet:
    path: /healthz
    port: 8080
```

### 5. 使用 Secret 管理敏感信息

```bash
kubectl create secret generic ai-fixer-secrets \
  --from-literal=database-url='postgresql+asyncpg://...' \
  --from-literal=redis-url='redis://...' \
  --from-literal=llm-api-key='sk-...' \
  -n ai-fixer
```

## 下一步

- [生产环境加固](/deployment/production) - 安全和监控配置
- [Docker 部署](/deployment/docker) - Docker 部署
- [开发指南](/development/) - 本地开发
