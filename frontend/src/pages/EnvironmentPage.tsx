import React, { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { getEnvironmentContext, updateEnvironmentContext } from '@/api/environmentContext';
import { toast } from 'sonner';

const PLACEHOLDER = `# 生产环境信息示例

## 服务列表
- payment-service: 支付核心服务，3 副本，namespace=production
- order-service: 订单服务，5 副本，namespace=production
- api-gateway: API 网关，2 副本，namespace=staging

## 基础设施
- K8s 集群: prod-cluster-1 (3 master + 10 worker)
- 数据库: PostgreSQL 14, RDS 实例 db.r6g.xlarge
- Redis: ElastiCache r6g.large, 3 节点集群

## 告警规则说明
- P0: 服务完全不可用，影响所有用户
- P1: 服务部分不可用，影响超过 30% 用户
- P2: 性能下降，响应时间超过 3 秒
- P3: 预警，资源使用率超过 80%

## 常见问题处理
- PodCrashLoopBackOff: 通常是 OOM，先检查内存限制
- HighCPUUsage: 检查是否有新版本发布或流量激增
- NodeNotReady: 检查节点磁盘、内存压力
`;

export default function EnvironmentPage() {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);

  useEffect(() => {
    getEnvironmentContext()
      .then((data) => {
        setContent(data.content);
        setUpdatedAt(data.updated_at);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const result = await updateEnvironmentContext(content);
      setUpdatedAt(result.updated_at);
      toast.success('环境上下文已保存');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '保存失败');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        加载中...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">环境上下文</h2>
          <p className="text-sm text-muted-foreground">
            配置生产环境信息，LLM 在诊断时会参考这些上下文
          </p>
        </div>
        <div className="flex items-center gap-3">
          {updatedAt && (
            <span className="text-xs text-muted-foreground">
              上次更新: {new Date(updatedAt).toLocaleString('zh-CN')}
            </span>
          )}
          <Button onClick={handleSave} disabled={saving}>
            {saving ? '保存中...' : '保存'}
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>环境描述</CardTitle>
          <CardDescription>
            填写你的生产环境信息，包括服务列表、基础设施、告警规则、常见问题处理方式等。
            LLM 会在分类和诊断时参考这些信息。
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea
            value={content}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setContent(e.target.value)}
            placeholder={PLACEHOLDER}
            className="min-h-[500px] font-mono text-sm resize-y"
          />
        </CardContent>
      </Card>
    </div>
  );
}
