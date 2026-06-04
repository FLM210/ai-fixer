import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  getIncidents,
  getIncident,
  type IncidentSummary,
  type IncidentDetail,
} from '@/api/incidents';

function severityColor(s: string | null) {
  if (s === 'p0' || s === 'p1') return 'destructive' as const;
  if (s === 'p2') return 'secondary' as const;
  return 'outline' as const;
}

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<IncidentSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [selected, setSelected] = useState<IncidentDetail | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const data = await getIncidents(
        page,
        20,
        statusFilter || undefined,
        severityFilter || undefined
      );
      setIncidents(data.items);
      setTotal(data.total);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [page, statusFilter, severityFilter]);

  const openDetail = async (id: string) => {
    try {
      const detail = await getIncident(id);
      setSelected(detail);
    } catch (err) {
      console.error(err);
    }
  };

  const totalPages = Math.ceil(total / 20);

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Incidents</h2>

      {/* 筛选栏 */}
      <div className="flex gap-3">
        <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v ?? ''); setPage(1); }}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="状态筛选" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部状态</SelectItem>
            <SelectItem value="new">new</SelectItem>
            <SelectItem value="diagnosing">diagnosing</SelectItem>
            <SelectItem value="awaiting_approval">awaiting_approval</SelectItem>
            <SelectItem value="executing">executing</SelectItem>
            <SelectItem value="resolved">resolved</SelectItem>
            <SelectItem value="escalated">escalated</SelectItem>
          </SelectContent>
        </Select>
        <Select value={severityFilter} onValueChange={(v) => { setSeverityFilter(v ?? ''); setPage(1); }}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="严重程度" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部</SelectItem>
            <SelectItem value="p0">P0</SelectItem>
            <SelectItem value="p1">P1</SelectItem>
            <SelectItem value="p2">P2</SelectItem>
            <SelectItem value="p3">P3</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* 表格 */}
      <div className="border rounded-md">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>严重程度</TableHead>
              <TableHead>分类</TableHead>
              <TableHead>服务</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>置信度</TableHead>
              <TableHead>Proposals</TableHead>
              <TableHead>创建时间</TableHead>
              <TableHead>操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8">
                  加载中...
                </TableCell>
              </TableRow>
            ) : incidents.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                  暂无数据
                </TableCell>
              </TableRow>
            ) : (
              incidents.map((inc) => (
                <TableRow key={inc.id}>
                  <TableCell>
                    <Badge variant={severityColor(inc.severity)}>
                      {inc.severity ?? '?'}
                    </Badge>
                  </TableCell>
                  <TableCell>{inc.category ?? '-'}</TableCell>
                  <TableCell>{inc.service ?? '-'}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{inc.status}</Badge>
                  </TableCell>
                  <TableCell>
                    {inc.confidence != null ? `${(inc.confidence * 100).toFixed(0)}%` : '-'}
                  </TableCell>
                  <TableCell>{inc.proposal_count}</TableCell>
                  <TableCell className="text-xs">
                    {new Date(inc.created_at).toLocaleString('zh-CN')}
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm" onClick={() => openDetail(inc.id)}>
                      详情
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* 分页 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            共 {total} 条，第 {page}/{totalPages} 页
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              上一页
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              下一页
            </Button>
          </div>
        </div>
      )}

      {/* 详情弹窗 */}
      <Dialog open={!!selected} onOpenChange={() => setSelected(null)}>
        <DialogContent className="incident-detail-dialog w-[calc(100vw-2rem)] max-w-4xl">
          <DialogHeader>
            <DialogTitle>Incident 详情</DialogTitle>
          </DialogHeader>
          {selected && (
            <div className="incident-detail-body space-y-4 pr-2">
              <div className="grid min-w-0 grid-cols-1 gap-2 text-sm sm:grid-cols-2">
                <div><strong>ID:</strong> {selected.id.slice(0, 8)}...</div>
                <div><strong>状态:</strong> {selected.status}</div>
                <div><strong>分类:</strong> {selected.category ?? '-'}</div>
                <div><strong>严重程度:</strong> {selected.severity ?? '-'}</div>
                <div><strong>服务:</strong> {selected.service ?? '-'}</div>
                <div><strong>命名空间:</strong> {selected.namespace ?? '-'}</div>
                <div><strong>LLM Tokens:</strong> {selected.llm_cost_tokens ?? 0}</div>
                <div><strong>解决方式:</strong> {selected.resolution_type ?? '-'}</div>
              </div>

              {selected.diagnosis && (
                <div>
                  <h4 className="font-semibold mb-1">诊断</h4>
                  <div className="incident-markdown text-sm prose prose-sm max-w-none dark:prose-invert">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{selected.diagnosis.root_cause ?? '无'}</ReactMarkdown>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    置信度: {selected.diagnosis.confidence != null
                      ? `${(selected.diagnosis.confidence * 100).toFixed(0)}%`
                      : '未知'}
                  </p>
                </div>
              )}

              {selected.proposals.length > 0 && (
                <div>
                  <h4 className="font-semibold mb-1">修复提案</h4>
                  {selected.proposals.map((p) => (
                    <div key={p.id} className="min-w-0 border rounded p-2 mb-2 text-sm">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="outline">{p.plugin_name}</Badge>
                        <Badge variant={p.risk_level === 'critical' ? 'destructive' : 'secondary'}>
                          {p.risk_level ?? '?'}
                        </Badge>
                      </div>
                      <p className="whitespace-pre-wrap break-words">{p.description ?? '无描述'}</p>
                    </div>
                  ))}
                </div>
              )}

              {selected.executions.length > 0 && (
                <div>
                  <h4 className="font-semibold mb-1">执行结果</h4>
                  {selected.executions.map((e) => (
                    <div key={e.id} className="min-w-0 border rounded p-2 mb-2 text-sm">
                      <div className="flex items-center gap-2">
                        <Badge variant={e.status === 'success' ? 'default' : 'destructive'}>
                          {e.status}
                        </Badge>
                        {e.error && <span className="text-red-500 text-xs whitespace-pre-wrap break-words">{e.error}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {selected.llm_turns.length > 0 && (
                <div>
                  <h4 className="font-semibold mb-2">LLM 对话详情</h4>
                  {['triage', 'diagnose', 'propose'].map(phase => {
                    const phaseTurns = selected.llm_turns.filter(t => t.phase === phase);
                    if (phaseTurns.length === 0) return null;
                    return (
                      <div key={phase} className="mb-4">
                        <h5 className="text-sm font-medium text-muted-foreground mb-2 uppercase">{phase}</h5>
                        <div className="space-y-2">
                          {phaseTurns.map((turn) => (
                            <div key={turn.id} className="min-w-0 border rounded p-3 text-sm">
                              <div className="flex items-center gap-2 mb-2">
                                <Badge variant={
                                  turn.role === 'user' ? 'default' :
                                  turn.role === 'assistant' ? 'secondary' :
                                  turn.role === 'tool' ? 'outline' : 'outline'
                                }>
                                  {turn.role}
                                </Badge>
                                {turn.tool_name && (
                                  <Badge variant="outline" className="text-xs">
                                    🔧 {turn.tool_name}
                                  </Badge>
                                )}
                                <span className="text-xs text-muted-foreground ml-auto">
                                  #{turn.turn_index}
                                </span>
                              </div>
                              <div className="incident-markdown text-xs bg-muted p-2 rounded max-h-60 overflow-y-auto overflow-x-hidden prose prose-xs max-w-none dark:prose-invert">
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>{turn.content}</ReactMarkdown>
                              </div>
                              {turn.tool_input && (
                                <details className="mt-2">
                                  <summary className="text-xs text-muted-foreground cursor-pointer">工具输入</summary>
                                  <pre className="text-xs bg-muted p-2 rounded mt-1 max-h-40 overflow-auto whitespace-pre-wrap break-words">
                                    {JSON.stringify(turn.tool_input, null, 2)}
                                  </pre>
                                </details>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
