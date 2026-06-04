import { useState, useEffect, useCallback } from 'react';
import { getConfig, updateConfig, type ConfigGroup } from '@/api/config';

export function useConfig() {
  const [groups, setGroups] = useState<ConfigGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchConfig = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getConfig();
      setGroups(data.groups);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载配置失败');
    } finally {
      setLoading(false);
    }
  }, []);

  const saveConfig = useCallback(async (configs: Record<string, unknown>) => {
    try {
      setSaving(true);
      setError(null);
      const result = await updateConfig(configs);
      await fetchConfig(); // 刷新
      return result.message;
    } catch (err) {
      const msg = err instanceof Error ? err.message : '保存配置失败';
      setError(msg);
      throw new Error(msg);
    } finally {
      setSaving(false);
    }
  }, [fetchConfig]);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  return { groups, loading, saving, error, fetchConfig, saveConfig };
}
