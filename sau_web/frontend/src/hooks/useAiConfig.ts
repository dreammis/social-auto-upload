import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'

export function useAiConfig() {
  return useQuery({
    queryKey: ['ai-config'],
    queryFn: async () => {
      const res = await api.getAiConfig()
      return res.data
    },
    staleTime: 30_000,
    refetchOnWindowFocus: true,
    refetchOnMount: true,
    retry: 2,
  })
}

export function useAiKeys() {
  return useQuery({
    queryKey: ['ai-keys'],
    queryFn: async () => {
      const res = await api.listAiKeys()
      return res.data
    },
    staleTime: 15_000,
    refetchOnWindowFocus: true,
    retry: 2,
  })
}

export function useSetAiConfig() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (apiKey: string) => api.setAiConfig(apiKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-config'] })
      queryClient.invalidateQueries({ queryKey: ['ai-keys'] })
    },
  })
}

export function useDeleteAiConfig() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (keyId?: number) => api.deleteAiConfig(keyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-config'] })
      queryClient.invalidateQueries({ queryKey: ['ai-keys'] })
    },
  })
}
