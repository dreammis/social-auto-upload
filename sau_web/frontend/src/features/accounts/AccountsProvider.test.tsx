import { describe, expect, it, vi } from 'vitest'
import { act, render, renderHook } from '@testing-library/react'
import { makeQueryClient, TestProviders } from '@/test/render-harness'
import type { AccountGroup } from '@/api/client'

// ── stable mock data refs (avoid infinite loops from new-array-on-every-call) ──

const _defaultGroups: AccountGroup[] = []
let _currentMockData: AccountGroup[] = _defaultGroups

// ── mocks (must precede under-test imports) ─────────────────────────────

vi.mock('@/components/ui/toast', () => ({
  useToast: () => ({ addToast: vi.fn() }),
}))

vi.mock('@/hooks/useAccountGroups', () => ({
  useAccountGroups: () => ({
    data: _currentMockData,
    isLoading: false,
    refetch: vi.fn(),
  }),
  useCreateAccountGroup: () => ({
    mutateAsync: vi.fn().mockResolvedValue({ success: true, data: { id: 1, name: '新建分组' } }),
    isPending: false,
  }),
  useDeleteAccountGroup: () => ({
    mutateAsync: vi.fn().mockResolvedValue({ success: true }),
    isPending: false,
  }),
  useRenameAccountGroup: () => ({
    mutateAsync: vi.fn().mockResolvedValue({ success: true, data: { id: 1, name: '新名字' } }),
    isPending: false,
  }),
  useRemoveAuthorization: () => ({
    mutateAsync: vi.fn().mockResolvedValue({ success: true }),
    isPending: false,
  }),
  useReorderAccountGroups: () => ({
    mutate: vi.fn().mockResolvedValue({ success: true }),
    isPending: false,
  }),
  useReorderAuthorizations: () => ({
    mutate: vi.fn().mockResolvedValue({ success: true }),
    isPending: false,
  }),
}))

vi.mock('@/api/client', () => ({
  api: {
    checkAllAccounts: vi.fn().mockResolvedValue({
      success: true,
      data: [
        { platform: 'douyin', account: '主号', quick: { valid: true, reason: '', age_hours: null, file_size: null } },
      ],
    }),
  },
  PLATFORMS: [
    { label: '抖音', value: 'douyin', color: 'magenta' },
    { label: '快手', value: 'kuaishou', color: 'orange' },
    { label: '小红书', value: 'xiaohongshu', color: 'red' },
    { label: '视频号', value: 'tencent', color: 'green' },
    { label: 'Bilibili', value: 'bilibili', color: 'blue' },
    { label: 'TikTok', value: 'tiktok', color: 'cyan' },
    { label: '百家号', value: 'baijiahao', color: 'gold' },
  ] as const,
}))

// ── imports (post-mock) ────────────────────────────────────────────────

import { AccountsProvider, useAccountsState, useAccountsDispatch, validateGroupName } from './AccountsProvider'

// ── helpers: render context hooks inside AccountsProvider ───────────────

/**
 * Render a combined hook that returns both state and dispatch from the
 * SAME provider instance. Using two separate renderHook calls creates
 * separate component trees → state updates via dispatch in one tree
 * are NOT reflected in the other tree's state.
 */
function renderCombined(groups?: AccountGroup[]) {
  _currentMockData = groups ?? _defaultGroups
  const qc = makeQueryClient()
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <TestProviders client={qc}>
      <AccountsProvider>{children}</AccountsProvider>
    </TestProviders>
  )
  return renderHook(
    () => ({
      state: useAccountsState(),
      dispatch: useAccountsDispatch(),
    }),
    { wrapper },
  )
}



// ── test suite ─────────────────────────────────────────────────────────

describe('AccountsProvider — rendering', () => {
  it('renders children without error', () => {
    _currentMockData = _defaultGroups
    const qc = makeQueryClient()
    const { container } = render(
      <TestProviders client={qc}>
        <AccountsProvider>
          <div data-testid="child">hello</div>
        </AccountsProvider>
      </TestProviders>,
    )
    expect(container.querySelector('[data-testid="child"]')).toBeTruthy()
    expect(container.textContent).toBe('hello')
  })

  it('regression: does NOT throw ReferenceError (Temporal Dead Zone fix)', () => {
    // Guards against "Cannot access 'getPlatformLabel' before initialization"
    _currentMockData = _defaultGroups
    const qc = makeQueryClient()
    expect(() => {
      render(
        <TestProviders client={qc}>
          <AccountsProvider>
            <div />
          </AccountsProvider>
        </TestProviders>,
      )
    }).not.toThrow()
  })

  it('exposes state context with default values', () => {
    const { result } = renderCombined()
    expect(result.current.state.groups).toEqual([])
    expect(result.current.state.isLoading).toBe(false)
    expect(result.current.state.searchQuery).toBe('')
    expect(result.current.state.viewMode).toBe('grid')
    expect(result.current.state.selectedIds).toEqual(new Set())
    expect(result.current.state.newGroupName).toBe('')
    expect(result.current.state.createDialogOpen).toBe(false)
    expect(result.current.state.authorizeDialogOpen).toBe(false)
    expect(result.current.state.loginModalOpen).toBe(false)
    expect(result.current.state.renameDialogOpen).toBe(false)
    expect(result.current.state.isCheckingStatus).toBe(false)
  })

  it('exposes server groups from useAccountGroups', () => {
    const groups: AccountGroup[] = [
      {
        id: 1,
        name: '测试分组',
        created: '2024-01-01T00:00:00Z',
        authorizations: [],
      },
    ]
    const { result } = renderCombined(groups)
    expect(result.current.state.groups).toHaveLength(1)
    expect(result.current.state.groups[0].name).toBe('测试分组')
  })

  it('useAccountsState throws when used outside provider', () => {
    expect(() => {
      renderHook(() => useAccountsState())
    }).toThrow('useAccountsState must be used inside <AccountsProvider>')
  })

  it('useAccountsDispatch throws when used outside provider', () => {
    expect(() => {
      renderHook(() => useAccountsDispatch())
    }).toThrow('useAccountsDispatch must be used inside <AccountsProvider>')
  })
})

describe('AccountsProvider — state updates', () => {
  it('setSearchQuery updates searchQuery', () => {
    const { result } = renderCombined()
    expect(result.current.state.searchQuery).toBe('')
    act(() => {
      result.current.dispatch.setSearchQuery('抖音')
    })
    expect(result.current.state.searchQuery).toBe('抖音')
  })

  it('handleClearSearch resets searchQuery to empty', () => {
    const { result } = renderCombined()

    act(() => {
      result.current.dispatch.setSearchQuery('搜索词')
    })
    expect(result.current.state.searchQuery).toBe('搜索词')

    act(() => {
      result.current.dispatch.handleClearSearch()
    })
    expect(result.current.state.searchQuery).toBe('')
  })

  it('handleSelectGroup adds and removes IDs', () => {
    const { result } = renderCombined()

    act(() => {
      result.current.dispatch.handleSelectGroup(1, true)
    })
    expect(result.current.state.selectedIds.has(1)).toBe(true)

    act(() => {
      result.current.dispatch.handleSelectGroup(1, false)
    })
    expect(result.current.state.selectedIds.has(1)).toBe(false)
  })

  it('setViewMode toggles view mode', () => {
    const { result } = renderCombined()

    expect(result.current.state.viewMode).toBe('grid')

    act(() => {
      result.current.dispatch.setViewMode('list')
    })
    expect(result.current.state.viewMode).toBe('list')
  })

  it('setNewGroupName updates newGroupName', () => {
    const { result } = renderCombined()

    act(() => {
      result.current.dispatch.setNewGroupName('我的分组')
    })
    expect(result.current.state.newGroupName).toBe('我的分组')
  })

  it('setCreateDialogOpen toggles create dialog', () => {
    const { result } = renderCombined()

    expect(result.current.state.createDialogOpen).toBe(false)
    act(() => {
      result.current.dispatch.setCreateDialogOpen(true)
    })
    expect(result.current.state.createDialogOpen).toBe(true)
  })

  it('handleStartRename sets rename dialog state', () => {
    const { result } = renderCombined()

    act(() => {
      result.current.dispatch.handleStartRename(42, '旧名字')
    })
    expect(result.current.state.renameDialogGroupId).toBe(42)
    expect(result.current.state.renameDialogCurrentName).toBe('旧名字')
    expect(result.current.state.renameDialogOpen).toBe(true)
  })

  it('handleStartAuthorize sets selected group and opens authorize dialog', () => {
    const { result } = renderCombined()

    act(() => {
      result.current.dispatch.handleStartAuthorize(7)
    })
    expect(result.current.state.selectedGroupId).toBe(7)
    expect(result.current.state.selectedPlatform).toBe('')
    expect(result.current.state.authorizeDialogOpen).toBe(true)
  })

  it('handleCreateGroup creates a group via mutation (dialog open → create → close)', async () => {
    const { result } = renderCombined()

    // Step 1: open the dialog (real-world flow)
    act(() => {
      result.current.dispatch.setCreateDialogOpen(true)
    })
    expect(result.current.state.createDialogOpen).toBe(true)

    // Step 2: fill in the group name
    act(() => {
      result.current.dispatch.setNewGroupName('新分组')
    })
    expect(result.current.state.newGroupName).toBe('新分组')

    // Step 3: create the group — reads newGroupName via ref
    await act(async () => {
      await result.current.dispatch.handleCreateGroup()
    })

    // Step 4: after success — name reset, dialog closed
    expect(result.current.state.newGroupName).toBe('')
    expect(result.current.state.createDialogOpen).toBe(false)
  })

  it('handleCreateGroup handles empty name gracefully (no throw)', async () => {
    // When newGroupName is whitespace, handleCreateGroup shows a warning
    // toast and returns early without calling the mutation
    const { result } = renderCombined()

    act(() => {
      result.current.dispatch.setNewGroupName('   ')
    })

    // Should not throw (the warning toast is already mocked)
    await expect(
      act(async () => {
        await result.current.dispatch.handleCreateGroup()
      }),
    ).resolves.not.toThrow()

    expect(result.current.state.newGroupName).toBe('   ')
    expect(result.current.state.createDialogOpen).toBe(false)
  })
})

describe('AccountsProvider — getPlatformLabel', () => {
  it('returns Chinese label for known platforms', () => {
    const { result } = renderCombined()
    expect(result.current.dispatch.getPlatformLabel('douyin')).toBe('抖音')
    expect(result.current.dispatch.getPlatformLabel('kuaishou')).toBe('快手')
    expect(result.current.dispatch.getPlatformLabel('xiaohongshu')).toBe('小红书')
    expect(result.current.dispatch.getPlatformLabel('tencent')).toBe('视频号')
    expect(result.current.dispatch.getPlatformLabel('bilibili')).toBe('Bilibili')
    expect(result.current.dispatch.getPlatformLabel('tiktok')).toBe('TikTok')
    expect(result.current.dispatch.getPlatformLabel('baijiahao')).toBe('百家号')
  })

  it('returns raw value for unknown platforms', () => {
    const { result } = renderCombined()
    expect(result.current.dispatch.getPlatformLabel('unknown')).toBe('unknown')
    expect(result.current.dispatch.getPlatformLabel('')).toBe('')
    expect(result.current.dispatch.getPlatformLabel('youtube')).toBe('youtube')
  })

  it('maintains stable identity across re-renders', () => {
    // getPlatformLabel has [] deps, so its identity is stable
    const { result, rerender } = renderCombined()
    const first = result.current.dispatch.getPlatformLabel

    rerender()
    expect(result.current.dispatch.getPlatformLabel).toBe(first)
  })
})

describe('AccountsProvider — filter logic (filteredGroups)', () => {
  it('returns localGroups as filteredGroups when searchQuery is empty', () => {
    const groups: AccountGroup[] = [
      {
        id: 1,
        name: '分组一',
        created: '2024-01-01T00:00:00Z',
        authorizations: [
          { id: 10, platform: 'douyin', cookie_file: '/cookies/douyin.json', valid: true },
        ],
      },
      {
        id: 2,
        name: '分组二',
        created: '2024-01-02T00:00:00Z',
        authorizations: [
          { id: 20, platform: 'kuaishou', cookie_file: '/cookies/kuaishou.json', valid: false },
        ],
      },
    ]
    const { result } = renderCombined(groups)
    expect(result.current.state.filteredGroups).toHaveLength(2)
  })

  it('filters groups by name', () => {
    const groups: AccountGroup[] = [
      {
        id: 1,
        name: '抖音运营',
        created: '2024-01-01T00:00:00Z',
        authorizations: [],
      },
      {
        id: 2,
        name: 'B站频道',
        created: '2024-01-02T00:00:00Z',
        authorizations: [],
      },
    ]
    const { result } = renderCombined(groups)

    act(() => {
      result.current.dispatch.setSearchQuery('抖音')
    })
    expect(result.current.state.filteredGroups).toHaveLength(1)
    expect(result.current.state.filteredGroups[0].name).toBe('抖音运营')
  })

  it('filters by platform label (Chinese)', () => {
    const groups: AccountGroup[] = [
      {
        id: 1,
        name: '分组一',
        created: '2024-01-01T00:00:00Z',
        authorizations: [
          { id: 10, platform: 'douyin', cookie_file: '/cookies/douyin.json', valid: true },
        ],
      },
      {
        id: 2,
        name: '分组二',
        created: '2024-01-02T00:00:00Z',
        authorizations: [
          { id: 20, platform: 'kuaishou', cookie_file: '/cookies/kuaishou.json', valid: false },
        ],
      },
    ]
    const { result } = renderCombined(groups)

    act(() => {
      result.current.dispatch.setSearchQuery('快手')
    })
    expect(result.current.state.filteredGroups).toHaveLength(1)
    expect(result.current.state.filteredGroups[0].name).toBe('分组二')
  })
})

describe('validateGroupName', () => {
  it('accepts valid group names', () => {
    expect(validateGroupName('我的分组')).toEqual({ ok: true, cleaned: '我的分组' })
  })

  it('trims whitespace', () => {
    expect(validateGroupName('  分组名称  ')).toEqual({ ok: true, cleaned: '分组名称' })
  })

  it('rejects empty names', () => {
    expect(validateGroupName('').ok).toBe(false)
    expect(validateGroupName('   ').ok).toBe(false)
    expect(validateGroupName(null).ok).toBe(false)
    expect(validateGroupName(undefined).ok).toBe(false)
  })

  it('rejects names with forbidden characters', () => {
    expect(validateGroupName('分组/名称').ok).toBe(false)
    expect(validateGroupName('分组\\名称').ok).toBe(false)
    expect(validateGroupName('分组:名称').ok).toBe(false)
    expect(validateGroupName('分组*名称').ok).toBe(false)
  })

  it('rejects names exceeding 64 chars', () => {
    expect(validateGroupName('a'.repeat(65)).ok).toBe(false)
    expect(validateGroupName('a'.repeat(64)).ok).toBe(true)
  })
})
