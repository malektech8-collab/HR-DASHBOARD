import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchTemplates, uploadFile, triggerRefresh } from '../lib/api';
import type { TemplateInfo, RefreshReport } from '../lib/api';

export function useTemplatesQuery() {
  return useQuery<TemplateInfo[]>({
    queryKey: ['templates'],
    queryFn: fetchTemplates,
    staleTime: 5 * 60 * 1000, // 5 minutes cache
  });
}

export function useUploadMutation() {
  return useMutation({
    mutationFn: (file: File) => uploadFile(file),
  });
}

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
