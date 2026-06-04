import client from './client';

export interface HealthCheck {
  db: string;
  redis: string;
}

export interface SystemStatus {
  version: string;
  uptime_healthy: boolean;
  health: HealthCheck;
  active_incidents: number;
  total_incidents: number;
  plugin_count: number;
  dynamic_config_loaded: boolean;
  llm_provider: string;
  llm_model: string;
}

export async function getStatus(): Promise<SystemStatus> {
  const { data } = await client.get('/status');
  return data;
}
