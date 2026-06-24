import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from '@/components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  getKnowledgeList, createKnowledge, updateKnowledge, deleteKnowledge,
  getKnowledgeStats, getKnowledgeRevisions,
  type KnowledgeEntry, type KnowledgeStats, type KnowledgeRevision,
} from '@/api/knowledge';
import { toast } from 'sonner';

const CATEGORIES = ['k8s', 'postgres', 'redis', 'nginx', 'kafka', 'network', 'monitoring', 'other'];

const STATUS_LABELS: Record<string, string> = {
  published: '已发布', draft: '草稿', review: '待审核', archived: '已归档',
};

export default function KnowledgePage() {
  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterCategory, setFilterCategory] = useState('all');
  const [keyword, setKeyword] = useState('');

  const [showEditor, setShowEditor] = useState(false);
  const [editingEntry, setEditingEntry] = useState<KnowledgeEntry | null>(null);
  const [form, setForm] = useState({ title: '', content: '', category: '', tags: '' });

  const [showRevisions, setShowRevisions] = useState(false);
  const [revisions, setRevisions] = useState<KnowledgeRevision[]>([]);
  const [revisionsLoading, setRevisionsLoading] = useState(false);

  const [showDetail, setShowDetail] = useState<KnowledgeEntry | null>(null);

  const fetchData = async () => {
    try {
      const [listData, statsData] = await Promise.all([
        getKnowledgeList(page, 20,
          filterStatus === 'all' ? undefined : filterStatus,
          filterCategory === 'all' ? undefined : filterCategory,
          keyword || undefined),
        getKnowledgeStats(),
      ]);
      setEntries(listData.items);
      setTotal(listData.total);
      setStats(statsData);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, [page, filterStatus, filterCategory]);

  const handleSearch = () => { setPage(1); fetchData(); };

  const openCreate = () => {
    setEditingEntry(null);
    setForm({ title: '', content: '', category: '', tags: '' });
    setShowEditor(true);
  };

  const openEdit = (entry: KnowledgeEntry) => {
    setEditingEntry(entry);
    setForm({
      title: entry.title, content: entry.content,
      category: entry.category || '', tags: (entry.tags || []).join(', '),
    });
    setShowEditor(true);
  };

  const handleSave = async () => {
    if (!form.title || !form.content) { toast.error('标题和内容不能为空'); return; }
    const payload = {
      title: form.title, content: form.content,
      category: form.category || undefined,
      tags: form.tags ? form.tags.split(',').map(t => t.trim()).filter(Boolean) : [],
    };
    try {
      if (editingEntry) {
        await updateKnowledge(editingEntry.id, payload);
        toast.success('已更新');
      } else {
        await createKnowledge(payload);
        toast.success('已创建');
      }
      setShowEditor(false);
      fetchData();
    } catch (err) { toast.error(err instanceof Error ? err.message : '保存失败'); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('确定删除此知识条目？')) return;
    try { await deleteKnowledge(id); toast.success('已删除'); fetchData(); }
    catch { toast.error('删除失败'); }
  };

  const handleShowRevisions = async (entry: KnowledgeEntry) => {
    setRevisionsLoading(true); setShowRevisions(true);
    try { setRevisions(await getKnowledgeRevisions(entry.id)); }
    catch { toast.error('获取版本历史失败'); }
    finally { setRevisionsLoading(false); }
  };

  const totalPages = Math.ceil(total / 20);

  if (loading) return <div className="flex items-center justify-center h-64 text-muted-foreground">加载中...</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">知识库</h2>
          <p className="text-sm text-muted-foreground">
            共 {stats?.total || 0} 条 · 已发布 {stats?.published || 0} · 待审核 {stats?.review || 0}
          </p>
        </div>
        <Button onClick={openCreate}>+ 添加知识</Button>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <Select value={filterStatus} onValueChange={(v) => { setFilterStatus(v ?? 'all'); setPage(1); }}>
          <SelectTrigger className="w-32"><SelectValue placeholder="状态" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            <SelectItem value="published">已发布</SelectItem>
            <SelectItem value="review">待审核</SelectItem>
            <SelectItem value="draft">草稿</SelectItem>
            <SelectItem value="archived">已归档</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filterCategory} onValueChange={(v) => { setFilterCategory(v ?? 'all'); setPage(1); }}>
          <SelectTrigger className="w-32"><SelectValue placeholder="分类" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部分类</SelectItem>
            {CATEGORIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
          </SelectContent>
        </Select>
        <Input placeholder="搜索关键词..." value={keyword}
          onChange={e => setKeyword(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSearch()} className="w-64" />
        <Button variant="outline" onClick={handleSearch}>搜索</Button>
      </div>

      <div className="border rounded-md">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>标题</TableHead>
              <TableHead>分类</TableHead>
              <TableHead>标签</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>来源</TableHead>
              <TableHead className="text-right">引用</TableHead>
              <TableHead>版本</TableHead>
              <TableHead>更新时间</TableHead>
              <TableHead className="w-36">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {entries.length === 0 ? (
              <TableRow><TableCell colSpan={9} className="text-center py-8 text-muted-foreground">暂无知识条目，点击「添加知识」开始</TableCell></TableRow>
            ) : entries.map(entry => (
              <TableRow key={entry.id}>
                <TableCell>
                  <button className="font-medium text-left hover:underline cursor-pointer" onClick={() => setShowDetail(entry)}>
                    {entry.title}
                  </button>
                </TableCell>
                <TableCell><Badge variant="outline">{entry.category || '未分类'}</Badge></TableCell>
                <TableCell>
                  <div className="flex gap-1 flex-wrap max-w-40">
                    {(entry.tags || []).slice(0, 3).map(tag => <Badge key={tag} variant="secondary" className="text-xs">{tag}</Badge>)}
                  </div>
                </TableCell>
                <TableCell>
                  <Badge variant={entry.status === 'published' ? 'default' : entry.status === 'review' ? 'secondary' : 'outline'}>
                    {STATUS_LABELS[entry.status] || entry.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">{entry.source_type}</TableCell>
                <TableCell className="text-right">{entry.use_count}</TableCell>
                <TableCell className="text-xs">v{entry.current_revision}</TableCell>
                <TableCell className="text-xs text-muted-foreground">{new Date(entry.updated_at).toLocaleString('zh-CN')}</TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="sm" onClick={() => openEdit(entry)}>编辑</Button>
                    <Button variant="ghost" size="sm" onClick={() => handleShowRevisions(entry)}>历史</Button>
                    <Button variant="ghost" size="sm" className="text-red-500 hover:text-red-700" onClick={() => handleDelete(entry.id)}>删除</Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>共 {total} 条</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>上一页</Button>
            <span className="flex items-center px-2">{page} / {totalPages}</span>
            <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>下一页</Button>
          </div>
        </div>
      )}

      {/* 创建/编辑弹窗 */}
      <Dialog open={showEditor} onOpenChange={setShowEditor}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingEntry ? '编辑知识' : '添加知识'}</DialogTitle>
            <DialogDescription>{editingEntry ? '修改后将自动创建新版本' : '添加修复手册或经验知识，指导后续诊断'}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Input placeholder="标题" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} />
            <div className="flex gap-2">
              <Select value={form.category} onValueChange={v => setForm({ ...form, category: v ?? '' })}>
                <SelectTrigger className="w-48"><SelectValue placeholder="选择分类" /></SelectTrigger>
                <SelectContent>{CATEGORIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
              </Select>
              <Input placeholder="标签，逗号分隔" value={form.tags} onChange={e => setForm({ ...form, tags: e.target.value })} className="flex-1" />
            </div>
            <Textarea placeholder={"内容（支持 Markdown）\n\n## 症状\n描述告警现象\n\n## 根因\n常见原因分析\n\n## 修复步骤\n1. 检查...\n2. 执行..."} value={form.content} onChange={e => setForm({ ...form, content: e.target.value })} className="min-h-[400px] font-mono text-sm resize-y" />
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowEditor(false)}>取消</Button>
              <Button onClick={handleSave}>{editingEntry ? '保存' : '创建'}</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* 版本历史弹窗 */}
      <Dialog open={showRevisions} onOpenChange={setShowRevisions}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader><DialogTitle>版本历史</DialogTitle></DialogHeader>
          {revisionsLoading ? <div className="py-8 text-center text-muted-foreground">加载中...</div>
          : revisions.length === 0 ? <div className="py-8 text-center text-muted-foreground">暂无版本记录</div>
          : <div className="space-y-3">
              {revisions.map(rev => (
                <div key={rev.id} className="border rounded-md p-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">v{rev.revision_number}</Badge>
                      {rev.change_summary && <span className="text-sm text-muted-foreground">{rev.change_summary}</span>}
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {new Date(rev.created_at).toLocaleString('zh-CN')}
                      {rev.created_by && ` · ${rev.created_by}`}
                    </span>
                  </div>
                  <div className="prose prose-sm max-w-none dark:prose-invert">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {rev.content.length > 300 ? rev.content.slice(0, 300) + '...' : rev.content}
                    </ReactMarkdown>
                  </div>
                </div>
              ))}
            </div>}
        </DialogContent>
      </Dialog>

      {/* 详情预览弹窗 */}
      <Dialog open={!!showDetail} onOpenChange={() => setShowDetail(null)}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{showDetail?.title}</DialogTitle>
            <DialogDescription className="flex items-center gap-2">
              <Badge variant="outline">{showDetail?.category || '未分类'}</Badge>
              {(showDetail?.tags || []).map(tag => <Badge key={tag} variant="secondary" className="text-xs">{tag}</Badge>)}
            </DialogDescription>
          </DialogHeader>
          <div className="prose prose-sm max-w-none dark:prose-invert">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{showDetail?.content || ''}</ReactMarkdown>
          </div>
          <div className="flex justify-end gap-2 mt-4 pt-4 border-t">
            <Button variant="outline" onClick={() => { setShowDetail(null); if (showDetail) openEdit(showDetail); }}>编辑</Button>
            <Button variant="outline" onClick={() => setShowDetail(null)}>关闭</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
