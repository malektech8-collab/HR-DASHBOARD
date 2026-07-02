import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

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

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<any> {
  const token = localStorage.getItem('auth_token');
  const headers = new Headers(options.headers || {});
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem('auth_token');
    }
    const text = await response.text();
    throw new Error(text || `Request failed with status ${response.status}`);
  }
  return response.json();
}

export function useGovernanceStatus() {
  return useQuery<GovernanceStatusData>({
    queryKey: ['governanceStatus'],
    queryFn: () => fetchWithAuth(`${API_BASE_URL}/api/governance/status`),
    retry: false,
  });
}

export function useLoginMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ username, password }: Record<string, string>) => {
      const params = new URLSearchParams();
      params.append('username', username);
      params.append('password', password);

      const res = await fetch(`${API_BASE_URL}/api/governance/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: params,
      });

      if (!res.ok) {
        throw new Error('Authentication failed. Please verify credentials.');
      }

      const data = await res.json();
      localStorage.setItem('auth_token', data.access_token);
      return data;
    },
    onSuccess: () => {
      // Invalidate status query to fetch newly authorized state
      queryClient.invalidateQueries({ queryKey: ['governanceStatus'] });
    },
  });
}
