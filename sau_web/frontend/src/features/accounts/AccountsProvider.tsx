import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
} from 'react'
import { createContext, useContext } from 'react'
import { arrayMove } from '@dnd-kit/helpers'
import { useToast } from '@/components/ui/toast'
import { api, PLATFORMS, type AccountGroup } from '@/api/client'
import {
  useAccountGroups,
  useCreateAccountGroup,
  useDeleteAccountGroup,
  useRemoveAuthorization,
  useReorderAccountGroups,
  useReorderAuthorizations,
  useRenameAccountGroup,
} from '@/hooks/useAccountGroups'

// ── Drag-end id prefixes — discriminates group vs auth drags under one
//    single-root DragDropProvider.
const GROUP_ID_PREFIX = 'group:'
const AUTH_ID_PREFIX = 'auth:'

// ── Group-name validation (mirrors backend `_validate_group_name`) ────────
const _FORBIDDEN_NAME_RE = /[/\\:*?"<>|\x00-\x1F\x7F]/
const _NAME_MAX_LEN = 64

export type GroupNameValidation =
  | { ok: true; cleaned: string }
  | { ok: false; message: string }

export function validateGroupName(value: unknown): GroupNameValidation {
  if (typeof value !== 'string') return { ok: false, message: '分组名不能为空' }
  const cleaned = value.trim()
  if (!cleaned) return { ok: false, message: '分组名不能为空' }
  if (cleaned.length > _NAME_MAX_LEN) {
    return { ok: false, message: `分组名长度不能超过 ${_NAME_MAX_LEN} 个字符` }
  }
  if (_FORBIDDEN_NAME_RE.test(cleaned)) {
    return { ok: false, message: '分组名包含不允许的字符（/\\:*?"<>|）' }
  }
  return { ok: true, cleaned }
}

// ── Drag-end event shape used by GroupGridArea + SortableAuthorizationItem. ──
type DragEndEvent = {
  operation: {
    target: { id: string | number } | null
    source: { id: string | number } | null
  }
}

// ── State context (values that change on render / server updates) ────────
// NOTE: React Query useMutation objects are intentionally NOT passed
// through context — they return new object identities on every render,
// which destabilises useMemo deps and triggers "Maximum update depth
// exceeded".  Instead we expose only the primitive isPending flags that
// consumers need for loading spinners / button-disabled state.
export type AccountsState = {
  groups: AccountGroup[]
  isLoading: boolean
  refetch: () => void

  isCreatePending: boolean
  isRenamePending: boolean
  isReorderInFlight: boolean

  localGroups: AccountGroup[]
  filteredGroups: AccountGroup[]

  searchQuery: string
  validityFilter: 'all' | 'valid' | 'invalid'
  viewMode: 'grid' | 'list'
  selectedIds: Set<number>

  newGroupName: string
  createDialogOpen: boolean
  batchDeleteOpen: boolean
  authorizeDialogOpen: boolean
  renameDialogOpen: boolean
  renameDialogGroupId: number | null
  renameDialogCurrentName: string
  selectedGroupId: number | null
  selectedPlatform: string
  loginModalOpen: boolean

  isCheckingStatus: boolean
}

// ── Dispatch context ─────────────────────────────────────────────────────
export type AccountsDispatch = {
  setSearchQuery: (q: string) => void
  setValidityFilter: Dispatch<SetStateAction<'all' | 'valid' | 'invalid'>>
  setViewMode: Dispatch<SetStateAction<'grid' | 'list'>>
  setSelectedIds: Dispatch<SetStateAction<Set<number>>>
  setNewGroupName: (n: string) => void
  setCreateDialogOpen: (o: boolean) => void
  setBatchDeleteOpen: (o: boolean) => void
  setAuthorizeDialogOpen: (o: boolean) => void
  setSelectedPlatform: (p: string) => void
  setLoginModalOpen: (o: boolean) => void
  setRenameDialogOpen: (o: boolean) => void

  handleDragStart: () => void
  handleDragEnd: (event: DragEndEvent) => void

  handleSelectGroup: (id: number, checked: boolean) => void
  handleSelectAll: () => void
  handleBatchDelete: () => Promise<void>
  handleCreateGroup: () => Promise<void>
  handleDeleteGroup: (groupId: number, name: string) => Promise<void>
  handleStartRename: (groupId: number, currentName: string) => void
  handleRename: (groupId: number, newName: string) => Promise<void>
  handleStartAuthorize: (groupId: number) => void
  handleAuthorize: () => void
  handleRemoveAuth: (groupId: number, platform: string) => Promise<void>
  handleClearSearch: () => void
  handleCheckAllStatus: () => Promise<void>

  getPlatformLabel: (value: string) => string
}

const AccountsStateCtx = createContext<AccountsState | null>(null)
const AccountsDispatchCtx = createContext<AccountsDispatch | null>(null)

const _EMPTY_GROUPS: AccountGroup[] = []

export function AccountsProvider({ children }: { children: ReactNode }) {
  const { addToast } = useToast()

  // ── server ──
  const { data: groups = _EMPTY_GROUPS, isLoading, refetch } = useAccountGroups()
  const createGroup = useCreateAccountGroup()
  const deleteGroup = useDeleteAccountGroup()
  const renameGroup = useRenameAccountGroup()
  const removeAuth = useRemoveAuthorization()
  const reorderGroups = useReorderAccountGroups()
  const reorderAuths = useReorderAuthorizations()

  // ── local/dialog UI state ──
  const [newGroupName, setNewGroupName] = useState('')
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [authorizeDialogOpen, setAuthorizeDialogOpen] = useState(false)
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null)
  const [selectedPlatform, setSelectedPlatform] = useState('')
  const [loginModalOpen, setLoginModalOpen] = useState(false)
  const [renameDialogOpen, setRenameDialogOpen] = useState(false)
  const [renameDialogGroupId, setRenameDialogGroupId] = useState<number | null>(null)
  const [renameDialogCurrentName, setRenameDialogCurrentName] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [validityFilter, setValidityFilter] = useState<'all' | 'valid' | 'invalid'>('all')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [batchDeleteOpen, setBatchDeleteOpen] = useState(false)
  const [isCheckingStatus, setIsCheckingStatus] = useState(false)

  // ── optimistic local copy of server data; drag guard prevents mid-drag clobbers ──
  const isDraggingRef = useRef(false)
  const [localGroups, setLocalGroups] = useState<AccountGroup[]>(groups)
  useEffect(() => {
    if (!isDraggingRef.current) {
      setLocalGroups(groups)
    }
  }, [groups])

  // ── ref-mirrors so dispatch handlers can read latest state WITHOUT
  //    capturing the state in useCallback deps (keeps dispatch identity
  //    stable across state updates). Same trick mirrored for the
  //    react-query mutation objects — their identity changes whenever
  //    isPending toggles, so handlers must NOT close over them directly.
  const localGroupsRef = useRef(localGroups)
  useEffect(() => {
    localGroupsRef.current = localGroups
  }, [localGroups])
  const filteredGroupsRef = useRef<AccountGroup[]>([])
  const selectedIdsRef = useRef(selectedIds)
  useEffect(() => {
    selectedIdsRef.current = selectedIds
  }, [selectedIds])
  const groupsRef = useRef(groups)
  useEffect(() => {
    groupsRef.current = groups
  }, [groups])
  const newGroupNameRef = useRef(newGroupName)
  useEffect(() => {
    newGroupNameRef.current = newGroupName
  }, [newGroupName])
  const selectedGroupIdRef = useRef(selectedGroupId)
  useEffect(() => {
    selectedGroupIdRef.current = selectedGroupId
  }, [selectedGroupId])
  const selectedPlatformRef = useRef(selectedPlatform)
  useEffect(() => {
    selectedPlatformRef.current = selectedPlatform
  }, [selectedPlatform])

  // mutation refs — capture the live mutate functions on every render so
  // stable handlers can call them without keeping mutation objects in deps.
  const createMutateAsyncRef = useRef(createGroup.mutateAsync)
  useEffect(() => {
    createMutateAsyncRef.current = createGroup.mutateAsync
  }, [createGroup.mutateAsync])
  const deleteMutateAsyncRef = useRef(deleteGroup.mutateAsync)
  useEffect(() => {
    deleteMutateAsyncRef.current = deleteGroup.mutateAsync
  }, [deleteGroup.mutateAsync])
  const renameMutateAsyncRef = useRef(renameGroup.mutateAsync)
  useEffect(() => {
    renameMutateAsyncRef.current = renameGroup.mutateAsync
  }, [renameGroup.mutateAsync])
  const removeAuthMutateAsyncRef = useRef(removeAuth.mutateAsync)
  useEffect(() => {
    removeAuthMutateAsyncRef.current = removeAuth.mutateAsync
  }, [removeAuth.mutateAsync])
  const reorderMutateRef = useRef(reorderGroups.mutate)
  useEffect(() => {
    reorderMutateRef.current = reorderGroups.mutate
  }, [reorderGroups.mutate])
  const reorderAuthsMutateRef = useRef(reorderAuths.mutate)
  useEffect(() => {
    reorderAuthsMutateRef.current = reorderAuths.mutate
  }, [reorderAuths.mutate])
  const refetchRef = useRef(refetch)
  useEffect(() => {
    refetchRef.current = refetch
  }, [refetch])

  const isReorderInFlight = reorderGroups.isPending || reorderAuths.isPending

  // ── stable platform-label helper (MUST be defined before filteredGroups
  //     useMemo to avoid Temporal Dead Zone access).
  const getPlatformLabel = useCallback(
    (value: string) => PLATFORMS.find((p) => p.value === value)?.label ?? value,
    [],
  )

  // Belt-and-braces: validityFilter is held in a useState typed as the
  // narrow union 'all' | 'valid' | 'invalid', but if a future migration
  // widens the type or an older saved value is replayed, we want a safe
  // fallback rather than a silent miss.
  const safeValidityFilter: 'all' | 'valid' | 'invalid' =
    validityFilter === 'valid' || validityFilter === 'invalid'
      ? validityFilter
      : 'all'

  // ── derived: filteredGroups ───────────────────────────────────────
  // Pipeline: localGroups → safeValidityFilter → searchQuery trim+match.
  // Validity filter runs first so an empty group with zero auths is hidden
  // from both 有效 and 失效 views (only groups with at least one all-valid
  // auth qualify for 有效; only groups containing an invalid auth qualify
  // for 失效 — empty groups have neither and so live only in 全部).
  // Magic-string 有效/失效 search-keyword matching was removed; the toolbar
  // exposes this as a segmented control so the contract is explicit.
  const filteredGroups = useMemo(() => {
    let result = localGroups
    if (safeValidityFilter === 'valid') {
      result = result.filter(
        (g) => g.authorizations.length > 0 && g.authorizations.every((a) => a.valid),
      )
    } else if (safeValidityFilter === 'invalid') {
      result = result.filter((g) => g.authorizations.some((a) => !a.valid))
    }

    const query = searchQuery.trim().toLowerCase()
    if (!query) return result
    return result.filter((group) => {
      const nameMatch = group.name.toLowerCase().includes(query)
      const platformMatch = group.authorizations.some(
        (auth) =>
          auth.platform.toLowerCase().includes(query) ||
          getPlatformLabel(auth.platform).toLowerCase().includes(query),
      )
      return nameMatch || platformMatch
    })
  }, [localGroups, searchQuery, safeValidityFilter, getPlatformLabel])
  useEffect(() => {
    filteredGroupsRef.current = filteredGroups
  }, [filteredGroups])

  // ── dnd handlers ──
  // Optimistic mutate-first-then-callback. The onError path fires a
  // refetch; the server→local useEffect then clobbers any stuck optimistic
  // order. stable deps (`[]` or just `addToast`) keep identity stable.
  const handleDragStart = useCallback(() => {
    isDraggingRef.current = true
  }, [])

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      isDraggingRef.current = false
      const { target, source } = event.operation
      if (!target || !source) return

      const sourceId = String(source.id)
      const targetId = String(target.id)
      const snapshot = localGroupsRef.current

      // Group reorder branch: `group:<id>` on both sides.
      if (
        sourceId.startsWith(GROUP_ID_PREFIX) &&
        targetId.startsWith(GROUP_ID_PREFIX)
      ) {
        const sourceGroupId = Number(sourceId.slice(GROUP_ID_PREFIX.length))
        const targetGroupId = Number(targetId.slice(GROUP_ID_PREFIX.length))
        const sourceIndex = snapshot.findIndex((g) => g.id === sourceGroupId)
        const targetIndex = snapshot.findIndex((g) => g.id === targetGroupId)
        if (
          sourceIndex === -1 ||
          targetIndex === -1 ||
          sourceIndex === targetIndex
        ) {
          return
        }
        const newGroups = arrayMove(snapshot, sourceIndex, targetIndex)
        setLocalGroups(newGroups)
        reorderMutateRef.current(newGroups.map((g) => g.id), {
          onError: () => {
            addToast('保存顺序失败，正在恢复…', 'error')
            refetchRef.current()
          },
        })
        return
      }

      // Auth reorder branch: `auth:<groupId>:<authId>` on both sides.
      // Cross-group drags are silently ignored — auths are tied to a group.
      if (
        sourceId.startsWith(AUTH_ID_PREFIX) &&
        targetId.startsWith(AUTH_ID_PREFIX)
      ) {
        const [, srcGroupRaw, srcAuthRaw] = sourceId.split(':')
        const [, tgtGroupRaw, tgtAuthRaw] = targetId.split(':')
        const sourceGroupId = Number(srcGroupRaw)
        const targetGroupId = Number(tgtGroupRaw)
        if (sourceGroupId !== targetGroupId) return
        const sourceAuthId = Number(srcAuthRaw)
        const targetAuthId = Number(tgtAuthRaw)
        const groupIdx = snapshot.findIndex((g) => g.id === sourceGroupId)
        if (groupIdx === -1) return
        const authList = snapshot[groupIdx].authorizations
        const sourceIndex = authList.findIndex((a) => a.id === sourceAuthId)
        const targetIndex = authList.findIndex((a) => a.id === targetAuthId)
        if (
          sourceIndex === -1 ||
          targetIndex === -1 ||
          sourceIndex === targetIndex
        ) {
          return
        }
        const newAuths = arrayMove(authList, sourceIndex, targetIndex)
        setLocalGroups((prev) =>
          prev.map((g) =>
            g.id === sourceGroupId ? { ...g, authorizations: newAuths } : g,
          ),
        )
        reorderAuthsMutateRef.current(
          { groupId: sourceGroupId, authIds: newAuths.map((a) => a.id) },
          {
            onError: () => {
              addToast('保存顺序失败，正在恢复…', 'error')
              refetchRef.current()
            },
          },
        )
      }
    },
    [addToast],
  )

  // ── selection handlers (refs only — stable identity) ──
  const handleSelectGroup = useCallback((id: number, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (checked) next.add(id)
      else next.delete(id)
      return next
    })
  }, [])

  const handleSelectAll = useCallback(() => {
    const filtered = filteredGroupsRef.current
    const current = selectedIdsRef.current
    if (current.size === filtered.length && filtered.length > 0) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(filtered.map((g) => g.id)))
    }
  }, [])

  // ── batch / create / delete / rename / remove-auth handlers — all
  //    stable; they read mutate fns via refs and capture `addToast`
  //    only by reference. addToast identity is stable (useToast wraps
  //    it in useCallback per toast.tsx line 46).
  const handleBatchDelete = useCallback(async () => {
    const ids = Array.from(selectedIdsRef.current)
    const count = ids.length
    const settled = await Promise.allSettled(
      ids.map((id) => deleteMutateAsyncRef.current(id)),
    )
    const failed = settled.filter((r) => {
      if (r.status === 'rejected') return true
      return r.value?.success === false
    })
    const succeeded = count - failed.length

    setSelectedIds(new Set())
    setBatchDeleteOpen(false)

    if (failed.length === 0) {
      addToast(`已删除 ${count} 个分组`, 'success')
    } else if (succeeded === 0) {
      addToast(`${failed.length} 个分组删除失败`, 'error')
    } else {
      addToast(
        `成功删除 ${succeeded}/${count} 个分组，${failed.length} 个失败`,
        'warning',
      )
    }
  }, [addToast])

  const handleCreateGroup = useCallback(async () => {
    const trimmed = newGroupNameRef.current.trim()
    if (!trimmed) {
      addToast('请输入账号分组名称', 'warning')
      return
    }
    try {
      const result = await createMutateAsyncRef.current(trimmed)
      if (result.success) {
        addToast(`分组 "${trimmed}" 创建成功`, 'success')
        setNewGroupName('')
        setCreateDialogOpen(false)
      } else {
        addToast(result.message || '创建失败', 'error')
      }
    } catch {
      addToast('创建请求失败', 'error')
    }
  }, [addToast])

  const handleDeleteGroup = useCallback(
    async (groupId: number, name: string) => {
      try {
        const result = await deleteMutateAsyncRef.current(groupId)
        if (result.success) {
          addToast(`分组 "${name}" 已删除`, 'success')
        } else {
          addToast(result.message || '删除失败', 'error')
        }
      } catch {
        addToast('删除请求失败', 'error')
      }
    },
    [addToast],
  )

  const handleStartRename = useCallback((groupId: number, currentName: string) => {
    setRenameDialogGroupId(groupId)
    setRenameDialogCurrentName(currentName)
    setRenameDialogOpen(true)
  }, [])

  const handleRename = useCallback(
    async (groupId: number, newName: string) => {
      const v = validateGroupName(newName)
      if (!v.ok) {
        addToast(v.message, 'warning')
        return
      }
      try {
        const result = await renameMutateAsyncRef.current({
          groupId,
          name: v.cleaned,
        })
        if (result.success) {
          addToast(`分组已重命名为 "${v.cleaned}"`, 'success')
          setRenameDialogOpen(false)
          setRenameDialogGroupId(null)
          setRenameDialogCurrentName('')
        } else {
          addToast(result.message || '重命名失败', 'error')
        }
      } catch {
        addToast('重命名请求失败', 'error')
      }
    },
    [addToast],
  )

  const handleStartAuthorize = useCallback((groupId: number) => {
    setSelectedGroupId(groupId)
    setSelectedPlatform('')
    setAuthorizeDialogOpen(true)
  }, [])

  // Note: refs declared above the handleAuthorize definition so the
  // hook-order lint/eslint rule is satisfied (see selectedGroupIdRef /
  // selectedPlatformRef at the top of the file).
  const handleAuthorize = useCallback(() => {
    const gid = selectedGroupIdRef.current
    const platform = selectedPlatformRef.current
    if (!gid || !platform) {
      addToast('请选择平台', 'warning')
      return
    }
    setAuthorizeDialogOpen(false)
    setLoginModalOpen(true)
  }, [addToast])

  const handleRemoveAuth = useCallback(
    async (groupId: number, platform: string) => {
      try {
        const result = await removeAuthMutateAsyncRef.current({
          groupId,
          platform,
        })
        if (result.success) {
          addToast(`已移除 ${platform} 授权`, 'success')
        } else {
          addToast(result.message || '移除失败', 'error')
        }
      } catch {
        addToast('移除请求失败', 'error')
      }
    },
    [addToast],
  )

  const handleClearSearch = useCallback(() => setSearchQuery(''), [])

  const handleCheckAllStatus = useCallback(async () => {
    if (groupsRef.current.length === 0) return
    setIsCheckingStatus(true)
    try {
      const res = await api.checkAllAccounts()
      if (res.success && res.data) {
        const total = res.data.length
        const valid = res.data.filter((d) => d.quick?.valid === true).length
        const invalid = total - valid
        if (total === 0) {
          addToast('当前没有可检测的授权账号', 'info')
        } else if (invalid === 0) {
          addToast(`已检测 ${total} 个授权，全部有效`, 'success')
        } else {
          addToast(
            `已检测 ${total} 个授权：${valid} 个有效，${invalid} 个失效，请重新登录`,
            'warning',
          )
        }
        refetchRef.current()
      } else {
        addToast('检测请求失败', 'error')
      }
    } catch {
      addToast('检测请求失败，请检查后端连接', 'error')
    } finally {
      setIsCheckingStatus(false)
    }
  }, [addToast])

  // ── dispatch object — stable identity when handlers above don't churn ──
  const dispatch = useMemo<AccountsDispatch>(
    () => ({
      setSearchQuery,
      setValidityFilter,
      setViewMode,
      setSelectedIds,
      setNewGroupName,
      setCreateDialogOpen,
      setBatchDeleteOpen,
      setAuthorizeDialogOpen,
      setSelectedPlatform,
      setLoginModalOpen,
      setRenameDialogOpen,
      handleDragStart,
      handleDragEnd,
      handleSelectGroup,
      handleSelectAll,
      handleBatchDelete,
      handleCreateGroup,
      handleDeleteGroup,
      handleStartRename,
      handleRename,
      handleStartAuthorize,
      handleAuthorize,
      handleRemoveAuth,
      handleClearSearch,
      handleCheckAllStatus,
      getPlatformLabel,
    }),
    [
      handleDragStart,
      handleDragEnd,
      handleSelectGroup,
      handleSelectAll,
      handleBatchDelete,
      handleCreateGroup,
      handleDeleteGroup,
      handleStartRename,
      handleRename,
      handleStartAuthorize,
      handleAuthorize,
      handleRemoveAuth,
      handleClearSearch,
      handleCheckAllStatus,
      getPlatformLabel,
    ],
  )

  const state = useMemo<AccountsState>(
    () => ({
      groups,
      isLoading,
      refetch,
      isCreatePending: createGroup.isPending,
      isRenamePending: renameGroup.isPending,
      isReorderInFlight,
      localGroups,
      filteredGroups,
      searchQuery,
      validityFilter,
      viewMode,
      selectedIds,
      newGroupName,
      createDialogOpen,
      batchDeleteOpen,
      authorizeDialogOpen,
      renameDialogOpen,
      renameDialogGroupId,
      renameDialogCurrentName,
      selectedGroupId,
      selectedPlatform,
      loginModalOpen,
      isCheckingStatus,
    }),
    [
      groups,
      isLoading,
      refetch,
      createGroup.isPending,
      renameGroup.isPending,
      isReorderInFlight,
      localGroups,
      filteredGroups,
      searchQuery,
      validityFilter,
      viewMode,
      selectedIds,
      newGroupName,
      createDialogOpen,
      batchDeleteOpen,
      authorizeDialogOpen,
      renameDialogOpen,
      renameDialogGroupId,
      renameDialogCurrentName,
      selectedGroupId,
      selectedPlatform,
      loginModalOpen,
      isCheckingStatus,
    ],
  )

  return (
    <AccountsDispatchCtx.Provider value={dispatch}>
      <AccountsStateCtx.Provider value={state}>{children}</AccountsStateCtx.Provider>
    </AccountsDispatchCtx.Provider>
  )
}

export function useAccountsState(): AccountsState {
  const ctx = useContext(AccountsStateCtx)
  if (!ctx) throw new Error('useAccountsState must be used inside <AccountsProvider>')
  return ctx
}

export function useAccountsDispatch(): AccountsDispatch {
  const ctx = useContext(AccountsDispatchCtx)
  if (!ctx) throw new Error('useAccountsDispatch must be used inside <AccountsProvider>')
  return ctx
}
