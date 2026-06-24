import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '../api/client'

export function useAiModels() {
  return useQuery({
    queryKey: ['ai-models'],
    queryFn: async () => {
      const res = await api.fetchAiModels()
      return { models: res.data ?? [], source: (res as { source?: string }).source ?? 'unknown' }
    },
    staleTime: 0,
    refetchOnWindowFocus: true,
  })
}

export function useAiGenerate() {
  return useMutation({
    mutationFn: (payload: { prompt: string; model?: string; system_prompt?: string; platform?: string }) =>
      api.generateAiContent(payload),
  })
}
