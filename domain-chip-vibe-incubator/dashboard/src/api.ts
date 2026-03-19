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

export const api = {
  health: () => request<{ status: string }>('GET', '/health'),
  status: () => request<Record<string, unknown>>('GET', '/status'),
  dashboard: () => request<Record<string, unknown>>('GET', '/dashboard'),
  admissionsReview: (body: { application_id: string; decision: string; note?: string }) =>
    request<Record<string, unknown>>('POST', '/admissions-review', body),
  buildRequest: (body: { venture_id: string; request_id: string; status: string; title?: string; kind?: string; priority?: string }) =>
    request<Record<string, unknown>>('POST', '/build-request', body),
  weeklyUpdate: (body: { venture_id: string; note?: string; stage?: string }) =>
    request<Record<string, unknown>>('POST', '/weekly-update', body),
  kpiSnapshot: (body: { venture_id: string; [key: string]: unknown }) =>
    request<Record<string, unknown>>('POST', '/kpi-snapshot', body),
}
