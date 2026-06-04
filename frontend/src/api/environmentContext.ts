import client from './client';

export interface EnvironmentContextData {
  content: string;
  updated_at: string | null;
  updated_by: string | null;
}

export async function getEnvironmentContext(): Promise<EnvironmentContextData> {
  const { data } = await client.get('/environment-context');
  return data;
}

export async function updateEnvironmentContext(
  content: string,
  updatedBy = 'user'
): Promise<EnvironmentContextData> {
  const { data } = await client.put('/environment-context', {
    content,
    updated_by: updatedBy,
  });
  return data;
}
