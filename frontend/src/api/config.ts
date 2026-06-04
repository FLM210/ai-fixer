import client from './client';

export interface ConfigItem {
  value: unknown;
  type: string;
  description: string;
  source: string;
  is_secret: boolean;
}

export interface ConfigGroup {
  name: string;
  label: string;
  items: Record<string, ConfigItem>;
}

export interface ConfigResponse {
  groups: ConfigGroup[];
}

export interface ConfigUpdateResponse {
  updated_keys: string[];
  message: string;
}

export async function getConfig(): Promise<ConfigResponse> {
  const { data } = await client.get('/config');
  return data;
}

export async function updateConfig(
  configs: Record<string, unknown>,
  updatedBy = 'api'
): Promise<ConfigUpdateResponse> {
  const { data } = await client.put('/config', {
    configs,
    updated_by: updatedBy,
  });
  return data;
}
