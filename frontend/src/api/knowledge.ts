import client from './client';

export interface KnowledgeEntry {
  id: string;
  title: string;
  content: string;
  category: string | null;
  tags: string[];
  source_type: string;
  source_incident_id: string | null;
  status: string;
  created_by: string | null;
  current_revision: number;
  use_count: number;
  last_used_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeListResponse {
  items: KnowledgeEntry[];
  total: number;
  page: number;
  page_size: number;
}

export interface KnowledgeStats {
  total: number;
  published: number;
  review: number;
  archived: number;
  categories: Record<string, number>;
}

export interface KnowledgeRevision {
  id: string;
  entry_id: string;
  revision_number: number;
  title: string;
  content: string;
  category: string | null;
  tags: string[];
  change_summary: string | null;
  created_by: string | null;
  created_at: string;
}

export async function getKnowledgeList(
  page = 1, pageSize = 20, status?: string, category?: string, keyword?: string
): Promise<KnowledgeListResponse> {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (status) params.status = status;
  if (category) params.category = category;
  if (keyword) params.keyword = keyword;
  const { data } = await client.get('/knowledge', { params });
  return data;
}

export async function getKnowledge(id: string): Promise<KnowledgeEntry> {
  const { data } = await client.get(`/knowledge/${id}`);
  return data;
}

export async function createKnowledge(entry: {
  title: string; content: string; category?: string; tags?: string[];
  source_type?: string; source_incident_id?: string; status?: string;
}): Promise<KnowledgeEntry> {
  const { data } = await client.post('/knowledge', entry);
  return data;
}

export async function updateKnowledge(id: string, entry: {
  title?: string; content?: string; category?: string; tags?: string[];
  status?: string; change_summary?: string;
}): Promise<KnowledgeEntry> {
  const { data } = await client.put(`/knowledge/${id}`, entry);
  return data;
}

export async function deleteKnowledge(id: string): Promise<void> {
  await client.delete(`/knowledge/${id}`);
}

export async function getKnowledgeStats(): Promise<KnowledgeStats> {
  const { data } = await client.get('/knowledge/stats');
  return data;
}

export async function getKnowledgeRevisions(id: string): Promise<KnowledgeRevision[]> {
  const { data } = await client.get(`/knowledge/${id}/revisions`);
  return data;
}

export async function rollbackKnowledge(id: string, revisionNumber: number): Promise<KnowledgeEntry> {
  const { data } = await client.post(`/knowledge/${id}/rollback/${revisionNumber}`);
  return data;
}

export async function checkStaleEntries(): Promise<{ marked_count: number; marked_ids: string[] }> {
  const { data } = await client.post('/knowledge/check-stale');
  return data;
}
