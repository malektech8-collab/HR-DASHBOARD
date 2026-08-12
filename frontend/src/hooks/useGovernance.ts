import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { getJson, login } from '../lib/http';

export interface GovernanceStatusData {
  current_gate: string;
  current_status: string;
  evidence_status: string;
  synthetic_validation_status: string;
  decision_recommendation: string;
  real_data_execution_approved: boolean;
  real_authorization_evidence_approved: boolean;
  load_scheduling_approved: boolean;
  go_no_go_meeting_held: boolean;
  stop_criteria_count: number;
  last_completed_milestone: string;
  milestone_3i_status: string;
  milestone_3j_status: string;
  milestone_3k_status: string;
}

// One HTTP client for the whole app: lib/http.ts. This file used to own
// the only fetchWithAuth in the frontend while api.ts had none, which is
// why P0-2's authenticated routes were unreachable from any page.

export function useGovernanceStatus() {
  return useQuery<GovernanceStatusData>({
    queryKey: ['governanceStatus'],
    queryFn: () => getJson<GovernanceStatusData>('/api/governance/status'),
    retry: false,
  });
}

export function useLoginMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ username, password }: Record<string, string>) => {
      await login(username, password);
    },
    onSuccess: () => {
      // Invalidate status query to fetch newly authorized state
      queryClient.invalidateQueries({ queryKey: ['governanceStatus'] });
    },
  });
}
