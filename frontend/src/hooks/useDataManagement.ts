import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchTemplates, triggerRefresh } from '../lib/api';
import type { TemplateInfo, RefreshReport } from '../lib/api';

export function useTemplatesQuery() {
  return useQuery<TemplateInfo[]>({
    queryKey: ['templates'],
    queryFn: fetchTemplates,
    staleTime: 5 * 60 * 1000, // 5 minutes cache
  });
}

// useUploadMutation() WAS HERE (TD-005). It posted a single file to
// /api/data/upload, which wrote straight to data/silver. The staged flow that
// replaced it needs three calls and a preview between them, so it lives in
// hooks/useUploads.ts rather than being reshaped into one mutation.

export function useRefreshMutation() {
  const queryClient = useQueryClient();
  return useMutation<RefreshReport, Error>({
    mutationFn: triggerRefresh,
    onSuccess: (data) => {
      if (data.status === 'success') {
        // Invalidate all query caches in the system to refresh the dashboard metrics
        queryClient.invalidateQueries();
      }
    },
  });
}
