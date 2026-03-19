import { useQuery } from '@tanstack/react-query'
import { apiClient } from './client'
import type { DashboardSnapshot } from '@/types'

// Fallback: try static JSON if API is down (dev without backend)
async function fetchDashboard(): Promise<DashboardSnapshot> {
  try {
    return await apiClient.getDashboard()
  } catch {
    const mod = await import('../generated/incubator-dashboard.json')
    return mod.default as unknown as DashboardSnapshot
  }
}

export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: fetchDashboard,
    staleTime: 30_000,
    refetchInterval: 60_000,
  })
}

export function useAlerts() {
  return useQuery({
    queryKey: ['alerts'],
    queryFn: apiClient.getAlerts,
    staleTime: 15_000,
    refetchInterval: 30_000,
    retry: 1,
  })
}

export function useStatus() {
  return useQuery({
    queryKey: ['status'],
    queryFn: apiClient.getStatus,
    staleTime: 30_000,
    refetchInterval: 60_000,
    retry: 1,
  })
}
