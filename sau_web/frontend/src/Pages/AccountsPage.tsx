import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import { PageHeader } from '@/components/ui/page-header'
import {
  useAccountsDispatch,
  useAccountsState,
} from '@/features/accounts/AccountsProvider'
import { GroupGridArea } from '@/features/accounts/GroupGridArea'
import { GroupListArea } from '@/features/accounts/GroupListArea'
import { GroupToolbar } from '@/features/accounts/GroupToolbar'
import { HomepageOverview } from '@/features/accounts/HomepageOverview'
import { DialogHost } from '@/features/accounts/dialogs'
import { Loader2, Plus, RefreshCw, Search, Users } from 'lucide-react'
import { cn } from '@/lib/utils'

/** AccountsPage — wrapped by <AccountsProvider> in App.tsx so context
 *  survives Fast Refresh without tearing down provider state. */
export default function AccountsPage() {
  return <AccountsShell />
}

/**
 * Slim shell orchestrator (~70 lines). Owns no state — only layout.
 * Each child subscribes to the slice of state / dispatch it cares about.
 */
function AccountsShell() {
  const state = useAccountsState()
  const dispatch = useAccountsDispatch()
  const navigate = useNavigate()

  const handleCreateGroup = useCallback(
    () => dispatch.setCreateDialogOpen(true),
    [dispatch],
  )
  const handleCheckAllStatus = useCallback(
    () => void dispatch.handleCheckAllStatus(),
    [dispatch],
  )
  const handleOpenTasks = useCallback(() => navigate('/tasks'), [navigate])
  const handleOpenPublish = useCallback(() => navigate('/publish'), [navigate])

  return (
    <div className="space-y-5 p-6">
      <PageHeader
        title="账号管理"
        description="管理账号分组和平台授权"
        icon={<Users className="h-5 w-5 text-muted-foreground" />}
        actions={<HeaderActions />}
      />

      <HomepageOverview
        onCreateGroup={handleCreateGroup}
        onCheckAllStatus={handleCheckAllStatus}
        onOpenTasks={handleOpenTasks}
        onOpenPublish={handleOpenPublish}
      />

      {state.localGroups.length > 0 && <GroupToolbar />}

      <BodyArea />

      <DialogHost />
    </div>
  )
}

function HeaderActions() {
  const dispatch = useAccountsDispatch()
  const state = useAccountsState()
  return (
    <div className="flex items-center gap-2">
      <Button
        variant="outline"
        size="sm"
        onClick={() => void dispatch.handleCheckAllStatus()}
        disabled={state.isCheckingStatus || state.groups.length === 0}
        className="gap-1.5"
        data-tour="check-all"
      >
        <RefreshCw
          className={cn('h-3.5 w-3.5', state.isCheckingStatus && 'animate-spin')}
        />
        {state.isCheckingStatus ? '检测中…' : '一键检测'}
      </Button>
      <Button size="sm" onClick={() => dispatch.setCreateDialogOpen(true)} data-tour="new-group">
        <Plus className="h-4 w-4 mr-1" />
        新建分组
      </Button>
    </div>
  )
}

function BodyArea() {
  const state = useAccountsState()
  const dispatch = useAccountsDispatch()
  if (state.isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-3">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground/50" />
        <span className="text-sm text-muted-foreground/50">加载中…</span>
      </div>
    )
  }
  if (state.groups.length === 0) {
    return (
      <EmptyState
        icon={<Users className="h-6 w-6" />}
        title="暂无账号分组"
        description="创建一个分组，然后添加各平台的授权"
        action={
          <Button size="sm" onClick={() => dispatch.setCreateDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-1" />
            新建分组
          </Button>
        }
      />
    )
  }
  if (state.filteredGroups.length === 0) {
    return (
      <EmptyState
        icon={<Search className="h-6 w-6" />}
        title="未找到匹配的分组"
        description={`没有找到包含 "${state.searchQuery}" 的分组`}
        action={
          <Button size="sm" variant="outline" onClick={dispatch.handleClearSearch}>
            清除搜索
          </Button>
        }
      />
    )
  }
  return state.viewMode === 'grid' ? <GroupGridArea /> : <GroupListArea />
}
