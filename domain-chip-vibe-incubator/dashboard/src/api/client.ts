import type {
  AlertsResponse,
  DashboardSnapshot,
  StatusResponse,
} from '@/types'

const BASE = '/api'

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.error ?? `API ${res.status}`)
  }
  return res.json()
}

export const apiClient = {
  // Read
  getDashboard: () => request<DashboardSnapshot>('GET', '/dashboard'),
  getAlerts: () => request<AlertsResponse>('GET', '/alerts'),
  getStatus: () => request<StatusResponse>('GET', '/status'),

  // Write — admissions
  postAdmissionsReview: (body: { application_id: string; decision: string; note?: string }) =>
    request<Record<string, unknown>>('POST', '/admissions-review', body),

  // Write — operations
  postBuildRequest: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>('POST', '/build-request', body),
  postWeeklyUpdate: (body: { venture_id: string; stage?: string; note?: string }) =>
    request<Record<string, unknown>>('POST', '/weekly-update', body),
  postKpiSnapshot: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>('POST', '/kpi-snapshot', body),

  // Write — governance
  postGovernancePropose: (body: {
    proposal_id: string; proposal_type: string; venture_id?: string; description: string; note?: string
  }) => request<Record<string, unknown>>('POST', '/governance-propose', body),
  postGovernanceVote: (body: { proposal_id: string; decision: string; weight?: number; note?: string }) =>
    request<Record<string, unknown>>('POST', '/governance-vote', body),
  postGovernanceTally: (body: { quorum?: number }) =>
    request<Record<string, unknown>>('POST', '/governance-tally', body),

  // Write — exit
  postVentureExit: (body: {
    venture_id: string; reason: string; outcome: string; lesson: string;
    failure_mode?: string; reusable_assets?: string
  }) => request<Record<string, unknown>>('POST', '/venture-exit', body),
}
