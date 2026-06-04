import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { getStatus, type SystemStatus } from '@/api/status';
import { getIncidents, type IncidentSummary } from '@/api/incidents';
import { useSSE } from '@/hooks/useSSE';

function StatusCard({ label, status }: { label: string; status: string }) {
  const ok = status === 'ok';
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm text-muted-foreground">{label}</CardTitle>
      </CardHeader>
      <CardContent>
        <Badge variant={ok ? 'default' : 'destructive'}>
          {ok ? '正常' : '异常'}
        </Badge>
      </CardContent>
    </Card>
  );
}

function severityColor(s: string | null) {
  if (s === 'p0' || s === 'p1') return 'destructive' as const;
  if (s === 'p2') return 'secondary' as const;
  return 'outline' as const;
}

export default function Dashboard() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [recentIncidents, setRecentIncidents] = useState<IncidentSummary[]>([]);
  const { connected } = useSSE();

  useEffect(() => {
    getStatus().then(setStatus).catch(console.error);
    getIncidents(1, 10).then((r) => setRecentIncidents(r.items)).catch(console.error);
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">仪表盘</h2>
        <Badge variant={connected ? 'default' : 'secondary'}>
          {connected ? '🟢 SSE 已连接' : '🔴 未连接'}
        </Badge>
      </div>

      {/* 状态卡片 */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">活跃 Incidents</CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-3xl font-bold">{status?.active_incidents ?? '-'}</span>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">总 Incidents</CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-3xl font-bold">{status?.total_incidents ?? '-'}</span>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">插件数量</CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-3xl font-bold">{status?.plugin_count ?? '-'}</span>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">LLM</CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-sm font-medium">
              {status ? `${status.llm_provider} / ${status.llm_model}` : '-'}
            </span>
          </CardContent>
        </Card>
      </div>

      {/* 健康状态 */}
      <div className="grid grid-cols-2 gap-4">
        <StatusCard label="数据库" status={status?.health.db ?? 'unknown'} />
        <StatusCard label="Redis" status={status?.health.redis ?? 'unknown'} />
      </div>

      {/* 最近 Incidents */}
      <Card>
        <CardHeader>
          <CardTitle>最近 Incidents</CardTitle>
        </CardHeader>
        <CardContent>
          {recentIncidents.length === 0 ? (
            <p className="text-muted-foreground text-sm">暂无数据</p>
          ) : (
            <div className="space-y-2">
              {recentIncidents.map((inc) => (
                <div
                  key={inc.id}
                  className="flex items-center justify-between border-b py-2 last:border-0"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <Badge variant={severityColor(inc.severity)}>
                        {inc.severity ?? '?'}
                      </Badge>
                      <span className="text-sm font-medium">
                        {inc.category ?? 'unknown'}
                      </span>
                      {inc.service && (
                        <span className="text-xs text-muted-foreground">
                          {inc.service}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {inc.summary?.slice(0, 80) ?? '无摘要'}
                    </p>
                  </div>
                  <div className="text-right space-y-1">
                    <Badge variant="outline">{inc.status}</Badge>
                    <p className="text-xs text-muted-foreground">
                      {new Date(inc.created_at).toLocaleString('zh-CN')}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
