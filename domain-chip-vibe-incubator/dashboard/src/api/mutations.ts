import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from './client'

function useInvalidatingMutation<T>(
  mutationFn: (body: T) => Promise<Record<string, unknown>>,
) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['dashboard'] })
      qc.invalidateQueries({ queryKey: ['status'] })
      qc.invalidateQueries({ queryKey: ['alerts'] })
    },
  })
}

export function useAdmissionsReview() {
  return useInvalidatingMutation(apiClient.postAdmissionsReview)
}

export function useBuildRequest() {
  return useInvalidatingMutation(apiClient.postBuildRequest)
}

export function useWeeklyUpdate() {
  return useInvalidatingMutation(apiClient.postWeeklyUpdate)
}

export function useKpiSnapshot() {
  return useInvalidatingMutation(apiClient.postKpiSnapshot)
}

export function useGovernancePropose() {
  return useInvalidatingMutation(apiClient.postGovernancePropose)
}

export function useGovernanceVote() {
  return useInvalidatingMutation(apiClient.postGovernanceVote)
}

export function useGovernanceTally() {
  return useInvalidatingMutation(apiClient.postGovernanceTally)
}

export function useVentureExit() {
  return useInvalidatingMutation(apiClient.postVentureExit)
}
