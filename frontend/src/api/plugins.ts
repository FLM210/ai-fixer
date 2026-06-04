import client from './client';

export interface PluginInfo {
  name: string;
  category: string;
  resource_type: string;
  risk_level: string;
  timeout_seconds: number;
  description: string;
  enabled: boolean;
  source: string; // "builtin" | "custom"
  input_schema: Record<string, unknown>;
}

export async function getPlugins(): Promise<PluginInfo[]> {
  const { data } = await client.get('/plugins');
  return data;
}

export async function togglePlugin(
  name: string,
  enabled: boolean
): Promise<{ ok: boolean; message: string }> {
  const { data } = await client.put(`/plugins/${name}/toggle`, { enabled });
  return data;
}

export async function reloadPlugins(): Promise<{
  plugins: string[];
  count: number;
  message: string;
}> {
  const { data } = await client.post('/plugins/reload');
  return data;
}

export async function uploadPlugin(file: File): Promise<{
  ok: boolean;
  message: string;
  total_plugins: number;
}> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await client.post('/plugins/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function deleteCustomPlugin(name: string): Promise<{
  ok: boolean;
  message: string;
}> {
  const { data } = await client.delete(`/plugins/custom/${name}`);
  return data;
}

export async function listCustomPlugins(): Promise<
  { filename: string; path: string; size: number }[]
> {
  const { data } = await client.get('/plugins/custom/list');
  return data;
}
