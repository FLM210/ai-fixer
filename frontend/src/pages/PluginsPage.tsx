import { useEffect, useRef, useState } from 'react';
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
import { Switch } from '@/components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import {
  getPlugins,
  togglePlugin,
  reloadPlugins,
  uploadPlugin,
  deleteCustomPlugin,
  type PluginInfo,
} from '@/api/plugins';
import { toast } from 'sonner';

function riskColor(r: string) {
  if (r === 'critical') return 'destructive' as const;
  if (r === 'high') return 'secondary' as const;
  return 'outline' as const;
}

export default function PluginsPage() {
  const [plugins, setPlugins] = useState<PluginInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [reloading, setReloading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<PluginInfo | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchPlugins = async () => {
    try {
      setPlugins(await getPlugins());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlugins();
  }, []);

  const handleToggle = async (name: string, enabled: boolean) => {
    try {
      const result = await togglePlugin(name, enabled);
      if (result.ok) {
        setPlugins((prev) =>
          prev.map((p) => (p.name === name ? { ...p, enabled } : p))
        );
        toast.success(result.message);
      } else {
        toast.error(result.message);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '操作失败');
    }
  };

  const handleReload = async () => {
    setReloading(true);
    try {
      const result = await reloadPlugins();
      toast.success(result.message);
      await fetchPlugins();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '重载失败');
    } finally {
      setReloading(false);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      const result = await uploadPlugin(file);
      toast.success(result.message);
      await fetchPlugins();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '上传失败');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      const result = await deleteCustomPlugin(deleteTarget.name);
      toast.success(result.message);
      setDeleteTarget(null);
      await fetchPlugins();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '删除失败');
    }
  };

  const builtinCount = plugins.filter((p) => p.source === 'builtin').length;
  const customCount = plugins.filter((p) => p.source === 'custom').length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">插件</h2>
          <p className="text-sm text-muted-foreground">
            共 {plugins.length} 个插件（内置 {builtinCount}，自定义 {customCount}）
          </p>
        </div>
        <div className="flex gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".py"
            className="hidden"
            onChange={handleUpload}
          />
          <Button
            variant="outline"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? '上传中...' : '📤 上传插件'}
          </Button>
          <Button onClick={handleReload} disabled={reloading} variant="outline">
            {reloading ? '重载中...' : '🔄 热重载'}
          </Button>
        </div>
      </div>

      <div className="border rounded-md">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-16">启用</TableHead>
              <TableHead>名称</TableHead>
              <TableHead>描述</TableHead>
              <TableHead>类型</TableHead>
              <TableHead>来源</TableHead>
              <TableHead>风险</TableHead>
              <TableHead>超时</TableHead>
              <TableHead className="w-20">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8">
                  加载中...
                </TableCell>
              </TableRow>
            ) : plugins.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={8}
                  className="text-center py-8 text-muted-foreground"
                >
                  暂无插件
                </TableCell>
              </TableRow>
            ) : (
              plugins.map((p) => (
                <TableRow
                  key={p.name}
                  className={p.enabled ? '' : 'opacity-50'}
                >
                  <TableCell>
                    <Switch
                      checked={p.enabled}
                      onCheckedChange={(checked) =>
                        handleToggle(p.name, checked)
                      }
                    />
                  </TableCell>
                  <TableCell className="font-medium font-mono text-sm">
                    {p.name}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground max-w-xs truncate">
                    {p.description}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{p.category}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        p.source === 'custom' ? 'default' : 'secondary'
                      }
                    >
                      {p.source === 'custom' ? '自定义' : '内置'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={riskColor(p.risk_level)}>
                      {p.risk_level}
                    </Badge>
                  </TableCell>
                  <TableCell>{p.timeout_seconds}s</TableCell>
                  <TableCell>
                    {p.source === 'custom' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-red-500 hover:text-red-700"
                        onClick={() => setDeleteTarget(p)}
                      >
                        删除
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* 删除确认弹窗 */}
      <Dialog
        open={!!deleteTarget}
        onOpenChange={() => setDeleteTarget(null)}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>确认删除插件</DialogTitle>
            <DialogDescription>
              确定要删除自定义插件 <strong>{deleteTarget?.name}</strong> 吗？
              此操作会删除插件文件，不可恢复。
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2 mt-4">
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              确认删除
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
