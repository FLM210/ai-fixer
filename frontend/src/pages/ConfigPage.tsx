import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { useConfig } from '@/hooks/useConfig';
import type { ConfigItem } from '@/api/config';
import { toast } from 'sonner';

function SecretInput({
  id,
  value,
  onChange,
}: {
  id: string;
  value: string;
  onChange: (v: string) => void;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="flex items-center gap-1 flex-1">
      <Input
        id={id}
        type={visible ? 'text' : 'password'}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="font-mono text-sm"
        placeholder="留空则不修改"
      />
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={() => setVisible(!visible)}
        className="px-2 text-xs shrink-0"
      >
        {visible ? '隐藏' : '显示'}
      </Button>
    </div>
  );
}

function ConfigField({
  itemKey,
  item,
  value,
  onChange,
}: {
  itemKey: string;
  item: ConfigItem;
  value: unknown;
  onChange: (key: string, value: unknown) => void;
}) {
  if (item.type === 'bool') {
    return (
      <Switch
        id={itemKey}
        checked={value as boolean}
        onCheckedChange={(checked) => onChange(itemKey, checked)}
      />
    );
  }

  if (item.is_secret) {
    return (
      <SecretInput
        id={itemKey}
        value={String(value ?? '')}
        onChange={(v) => onChange(itemKey, v)}
      />
    );
  }

  return (
    <Input
      id={itemKey}
      value={String(value ?? '')}
      onChange={(e) => {
        const v = e.target.value;
        if (item.type === 'int') onChange(itemKey, parseInt(v, 10) || 0);
        else if (item.type === 'float') onChange(itemKey, parseFloat(v) || 0);
        else onChange(itemKey, v);
      }}
      className="font-mono text-sm"
    />
  );
}

export default function ConfigPage() {
  const { groups, loading, saving, saveConfig } = useConfig();
  const [edits, setEdits] = useState<Record<string, unknown>>({});

  const handleChange = (key: string, value: unknown) => {
    setEdits((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    if (Object.keys(edits).length === 0) {
      toast.info('没有需要保存的修改');
      return;
    }
    // 过滤掉密钥字段中未实际修改的值（仍是脱敏的 ****）
    const cleaned: Record<string, unknown> = {};
    for (const [key, val] of Object.entries(edits)) {
      if (typeof val === 'string' && /^\*+$/.test(val)) continue;
      cleaned[key] = val;
    }
    if (Object.keys(cleaned).length === 0) {
      toast.info('没有需要保存的修改');
      return;
    }
    try {
      const msg = await saveConfig(cleaned);
      toast.success(msg);
      setEdits({});
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '保存失败');
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">配置管理</h2>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">
            {Object.keys(edits).length > 0 && `已修改 ${Object.keys(edits).length} 项`}
          </span>
          <Button onClick={handleSave} disabled={saving || Object.keys(edits).length === 0}>
            {saving ? '保存中...' : '保存修改'}
          </Button>
        </div>
      </div>

      {groups.map((group) => (
        <Card key={group.name}>
          <CardHeader>
            <CardTitle>{group.label}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
              {Object.entries(group.items).map(([key, item]) => {
                const displayValue =
                  key in edits ? edits[key] : item.value;
                return (
                  <div key={key} className="space-y-1.5">
                    <div className="flex items-center gap-2">
                      <Label htmlFor={key} className="text-sm font-medium">
                        {item.description || key}
                      </Label>
                      {item.is_secret && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700">
                          密钥
                        </span>
                      )}
                      {item.source === 'database' && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">
                          DB
                        </span>
                      )}
                    </div>
                    <ConfigField
                      itemKey={key}
                      item={item}
                      value={displayValue}
                      onChange={handleChange}
                    />
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
