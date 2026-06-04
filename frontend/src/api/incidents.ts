import client from './client';

export interface IncidentSummary {
  id: string;
  fingerprint: string;
  status: string;
  category: string | null;
  severity: string | null;
  service: string | null;
  namespace: string | null;
  summary: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  resolution_type: string | null;
  confidence: number | null;
  proposal_count: number;
}

export interface IncidentListResponse {
  items: IncidentSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface DiagnosisDetail {
  root_cause: string | null;
  confidence: number | null;
  evidence: unknown[] | null;
  created_at: string;
}

export interface ProposalDetail {
  id: string;
  plugin_name: string;
  risk_level: string | null;
  description: string | null;
  expected_outcome: string | null;
  args: Record<string, unknown> | null;
  source: string | null;
}

export interface ExecutionDetail {
  id: string;
  proposal_id: string;
  status: string;
  approved_by: string | null;
  output: Record<string, unknown> | null;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface LLMTurnDetail {
  id: string;
  phase: string;
  turn_index: number;
  role: string;
  content: string;
  tool_name: string | null;
  tool_input: Record<string, unknown> | null;
  created_at: string;
}

export interface IncidentDetail {
  id: string;
  fingerprint: string;
  status: string;
  category: string | null;
  severity: string | null;
  service: string | null;
  namespace: string | null;
  summary: string | null;
  raw_alert: Record<string, unknown>;
  chat_id: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  resolution_type: string | null;
  llm_cost_tokens: number | null;
  diagnosis: DiagnosisDetail | null;
  proposals: ProposalDetail[];
  executions: ExecutionDetail[];
  llm_turns: LLMTurnDetail[];
}

export async function getIncidents(
  page = 1,
  pageSize = 20,
  status?: string,
  severity?: string
): Promise<IncidentListResponse> {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (status) params.status = status;
  if (severity) params.severity = severity;
  const { data } = await client.get('/incidents', { params });
  return data;
}

export async function getIncident(id: string): Promise<IncidentDetail> {
  const { data } = await client.get(`/incidents/${id}`);
  return data;
}
