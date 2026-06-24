import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, type AccountGroup } from '../api/client'

export function useAccountGroups() {
  return useQuery<AccountGroup[]>({
    queryKey: ['account-groups'],
    queryFn: async () => {
      const res = await api.getAccountGroups()
      return res.data ?? []
    },
  })
}

export function useCreateAccountGroup() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => api.createAccountGroup(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['account-groups'] })
    },
  })
}

export function useDeleteAccountGroup() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (groupId: number) => api.deleteAccountGroup(groupId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['account-groups'] })
    },
  })
}

export function useRenameAccountGroup() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ groupId, name }: { groupId: number; name: string }) =>
      api.renameAccountGroup(groupId, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['account-groups'] })
    },
  })
}

export function useAuthorizeAccountGroup() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ groupId, platform, headless }: { groupId: number; platform: string; headless?: boolean }) =>
      api.authorizeAccountGroup(groupId, platform, headless),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['account-groups'] })
    },
  })
}

export function useConfirmAuthorizeAccountGroup() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ groupId, platform }: { groupId: number; platform: string }) =>
      api.confirmAuthorizeAccountGroup(groupId, platform),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['account-groups'] })
    },
  })
}

export function useRemoveAuthorization() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ groupId, platform }: { groupId: number; platform: string }) =>
      api.removeAuthorization(groupId, platform),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['account-groups'] })
    },
  })
}

export function useReorderAccountGroups() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (groupIds: number[]) => api.reorderAccountGroups(groupIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['account-groups'] })
    },
  })
}

export function useReorderAuthorizations() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ groupId, authIds }: { groupId: number; authIds: number[] }) =>
      api.reorderAuthorizations(groupId, authIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['account-groups'] })
    },
  })
}
