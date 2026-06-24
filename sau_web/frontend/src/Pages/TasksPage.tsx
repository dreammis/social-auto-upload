import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { ChipBar } from '@/components/ui/chip-bar'
import { PageHeader } from '@/components/ui/page-header'
import { api, type TaskItem } from '../api/client'
import { useTasks } from '../hooks/useTasks'
import { useQueryClient } from '@tanstack/react-query'
import { useToast } from '@/components/ui/toast'
import {
  BarChart3,
  Loader2,
  Plus,
  RefreshCw,
  Trash2,
} from 'lucide-react'
import {
  STATUS_CHIPS,
  type BatchProgress,
  type BatchResultItem,
  type StatusType,
} from '../features/tasks/shared'
import {
  BATCH_CONCURRENCY,
  runWithConcurrency,
  shortenId,
} from '@/lib/features'
import { TaskTable, TaskTableCard } from '../features/tasks/TaskTable'
import { TaskDrawer } from '../features/tasks/TaskDrawer'
import { TaskBatchActions } from '../features/tasks/TaskBatchActions'
import { AddTaskDialog, type AddTaskFormState } from '../features/tasks/AddTaskDialog'
import { TaskProgressBar } from '../features/tasks/TaskProgressBar'

const TASKS_QUERY_KEY = ['tasks'] as const
export default function TasksPage() {
  const qc = useQueryClient()
  const { addToast } = useToast()
  const { data: tasks = [], isLoading, refetch } = useTasks()
  const [keyword, setKeyword] = useState('')
  const [debouncedKeyword, setDebouncedKeyword] = useState('')
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => {
    debounceTimerRef.current = setTimeout(() => {
      setDebouncedKeyword(keyword)
    }, 300)
    return () => {
      if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current)
    }
  }, [keyword])
  const [status, setStatus] = useState<StatusType>('all')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [batchProgress, setBatchProgress] = useState<BatchProgress>(null)
  const [batchDetailOpen, setBatchDetailOpen] = useState(false)
  const [drawerTaskId, setDrawerTaskId] = useState<string | null>(null)
  const [retrying, setRetrying] = useState<string | null>(null)
  const [manualRefreshing, setManualRefreshing] = useState(false)
  const [addModalOpen, setAddModalOpen] = useState(false)
  const [addForm, setAddForm] = useState<AddTaskFormState>({
    platform: '',
    action: '',
    account: '',
    title: '',
  })
  const searchInputRef = useRef<HTMLInputElement>(null)
  const [searchParams, setSearchParams] = useSearchParams()
  useEffect(() => {
    const focusId = searchParams.get('focus')
    if (!focusId) return
    if (tasks.length === 0) return
    if (tasks.some((t) => t.task_id === focusId)) {
      const id = focusId
      requestAnimationFrame(() => setDrawerTaskId(id))
    }
    const next = new URLSearchParams(searchParams)
    next.delete('focus')
    setSearchParams(next, { replace: true })
  }, [searchParams, tasks, setSearchParams])
  const filtered = useMemo(() => {
    const kw = debouncedKeyword.trim().toLowerCase()
    return tasks
      .filter((item) => {
        if (status !== 'all' && (item.status ?? '') !== status) return false
        if (!kw) return true
        return (
          (item.task_id ?? '').toLowerCase().includes(kw) ||
          (item.platform ?? '').toLowerCase().includes(kw) ||
          (item.action ?? '').toLowerCase().includes(kw) ||
          (item.account ?? '').toLowerCase().includes(kw)
        )
      })
      .sort((a, b) => (b.created ?? '').localeCompare(a.created ?? ''))
  }, [tasks, debouncedKeyword, status])
  const counts = useMemo(() => {
    const map: Record<string, number> = { all: 0 }
    tasks.forEach((item) => {
      map.all += 1
      map[item.status ?? 'pending'] = (map[item.status ?? 'pending'] || 0) + 1
    })
    return map
  }, [tasks])
  const chipOptions = useMemo(
    () => STATUS_CHIPS.map((c) => ({ ...c, count: counts[c.value] ?? 0 })),
    [counts],
  )
  const refresh = useCallback(async () => {
    setManualRefreshing(true)
    await refetch()
    setManualRefreshing(false)
  }, [refetch])
  const handleOpenDrawer = useCallback((record: TaskItem) => {
    setDrawerTaskId(record.task_id)
  }, [])
  const handleCloseDrawer = useCallback(() => setDrawerTaskId(null), [])
  const handleRetry = useCallback(
    async (record: TaskItem) => {
      setRetrying(record.task_id)
      try {
        const res = await api.retryTask(record.task_id)
        if (res.success && res.data?.task_id) {
          addToast(`已创建重试任务：${shortenId(res.data.task_id)}`, 'success')
          qc.invalidateQueries({ queryKey: TASKS_QUERY_KEY })
        } else {
          addToast(res.message ?? '重试失败', 'error')
        }
      } catch {
        addToast('重试请求失败，请检查后端连接', 'error')
      } finally {
        setRetrying(null)
        if (drawerTaskId === record.task_id) setDrawerTaskId(null)
      }
    },
    [qc, addToast, drawerTaskId],
  )
  const handleDelete = useCallback(
    async (taskId: string) => {
      try {
        const res = await api.deleteTask(taskId)
        if (res.success) {
          addToast('任务已删除', 'success')
          qc.invalidateQueries({ queryKey: TASKS_QUERY_KEY })
        } else {
          addToast(res.message ?? '删除失败', 'error')
        }
      } catch {
        addToast('删除请求失败', 'error')
      } finally {
        if (drawerTaskId === taskId) setDrawerTaskId(null)
      }
    },
    [qc, addToast, drawerTaskId],
  )
  const handleClear = useCallback(async () => {
    try {
      const res = await api.clearTasks(['success', 'failed', 'error'])
      if (res.success && res.data) {
        addToast(`已清理 ${res.data.deleted} 个任务`, 'success')
        qc.invalidateQueries({ queryKey: TASKS_QUERY_KEY })
      } else {
        addToast('清理失败', 'error')
      }
    } catch {
      addToast('清理请求失败', 'error')
    }
  }, [qc, addToast])
  const handleOpenAddModal = useCallback(() => {
    setAddForm({ platform: '', action: '', account: '', title: '' })
    setAddModalOpen(true)
  }, [])
  const handleCloseAddModal = useCallback(() => setAddModalOpen(false), [])
  const handleAddTaskChange = useCallback((next: AddTaskFormState) => setAddForm(next), [])
  const handleAddTaskConfirm = useCallback(async () => {
    if (!addForm.platform || !addForm.action || !addForm.account) {
      addToast('请填写必填字段', 'warning')
      return
    }
    try {
      const res = await api.addTask({
        platform: addForm.platform,
        action: addForm.action,
        account: addForm.account,
        title: addForm.title || undefined,
      })
      if (res.success && res.data) {
        addToast(`任务已创建：${shortenId(res.data.task_id)}`, 'success')
        handleCloseAddModal()
        qc.invalidateQueries({ queryKey: TASKS_QUERY_KEY })
      } else {
        addToast(res.message || '创建失败', 'error')
      }
    } catch {
      addToast('创建请求失败', 'error')
    }
  }, [addForm, qc, addToast, handleCloseAddModal])
  const handleToggleSelect = useCallback((taskId: string, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (checked) next.add(taskId)
      else next.delete(taskId)
      return next
    })
  }, [])
  const handleToggleAll = useCallback(
    (checked: boolean) => {
      setSelectedIds((prev) => {
        const next = new Set(prev)
        if (checked) filtered.forEach((t) => next.add(t.task_id))
        else filtered.forEach((t) => next.delete(t.task_id))
        return next
      })
    },
    [filtered],
  )
  const handleClearSelection = useCallback(() => setSelectedIds(new Set()), [])
  const handleStatusBadgeClick = useCallback((next: StatusType) => {
    setStatus((prev) => (prev === next ? 'all' : next))
  }, [])
  const canDelete = (s?: string) =>
    s === 'success' || s === 'failed' || s === 'error' || s === 'scheduled'
  const canRetry = (s?: string) => s === 'failed' || s === 'error'
  const runBatch = useCallback(
    async (
      type: 'retry' | 'delete',
      targets: TaskItem[],
      callApi: (t: TaskItem) => Promise<{ success: boolean; message?: string }>,
      successToast: string,
    ) => {
      const results: BatchResultItem[] = []
      setBatchProgress({ type, total: targets.length, current: 0, results: [] })
      setBatchDetailOpen(false)
      await runWithConcurrency(
        targets,
        BATCH_CONCURRENCY,
        async (t) => {
          try {
            const res = await callApi(t)
            return { taskId: t.task_id, success: res.success, message: res.message, status: t.status }
          } catch (err) {
            return {
              taskId: t.task_id,
              success: false,
              message: err instanceof Error ? err.message : '请求失败',
              status: t.status,
            }
          }
        },
        (_idx, result) => {
          setBatchProgress((prev) =>
            prev ? { ...prev, current: prev.current + 1, results: [...prev.results, result] } : prev,
          )
          results.push(result)
        },
      )
      setSelectedIds((prev) => {
        const next = new Set(prev)
        targets.forEach((t) => next.delete(t.task_id))
        return next
      })
      const succeeded = results.filter((r) => r.success).length
      addToast(
        `${successToast}：${succeeded} 成功，${results.length - succeeded} 失败`,
        succeeded > 0 ? 'success' : 'error',
      )
      qc.invalidateQueries({ queryKey: TASKS_QUERY_KEY })
    },
    [addToast, qc],
  )
  const handleBatchRetry = useCallback(() => {
    const retryable = filtered.filter((t) => selectedIds.has(t.task_id) && canRetry(t.status))
    if (retryable.length === 0) {
      addToast('选中的任务中没有可重试的任务', 'warning')
      return
    }
    void runBatch(
      'retry',
      retryable,
      (t) => api.retryTask(t.task_id).then((r) => ({ success: r.success, message: r.message })),
      '批量重试完成',
    )
  }, [filtered, selectedIds, addToast, runBatch])
  const handleBatchDelete = useCallback(() => {
    const deletable = filtered.filter((t) => selectedIds.has(t.task_id) && canDelete(t.status))
    if (deletable.length === 0) {
      addToast('选中的任务中没有可删除的任务', 'warning')
      return
    }
    void runBatch(
      'delete',
      deletable,
      (t) => api.deleteTask(t.task_id).then((r) => ({ success: r.success, message: r.message })),
      '批量删除完成',
    )
  }, [filtered, selectedIds, addToast, runBatch])
  const filteredRef = useRef(filtered)
  useEffect(() => {
    filteredRef.current = filtered
  }, [filtered])
  useEffect(() => {
    const raf = requestAnimationFrame(() => {
      setSelectedIds((prev) => {
        const visible = new Set(filteredRef.current.map((t) => t.task_id))
        let anyDropped = false
        const next = new Set<string>()
        prev.forEach((id) => {
          if (visible.has(id)) next.add(id)
          else anyDropped = true
        })
        return anyDropped ? next : prev
      })
    })
    return () => cancelAnimationFrame(raf)
  }, [debouncedKeyword, status])
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.tagName === 'SELECT' ||
        target.isContentEditable
      ) {
        return
      }
      if (e.metaKey || e.ctrlKey || e.altKey) return
      if (document.querySelector('[data-radix-dialog-content]')) return
      if (drawerTaskId || addModalOpen) return
      switch (e.key.toLowerCase()) {
        case 'r':
          e.preventDefault()
          void refresh()
          break
        case 'n':
          e.preventDefault()
          handleOpenAddModal()
          break
        case '/':
          e.preventDefault()
          searchInputRef.current?.focus()
          break
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [refresh, drawerTaskId, addModalOpen, handleOpenAddModal])
  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="任务列表"
        description="查看和管理所有上传任务"
        icon={<BarChart3 className="h-5 w-5 text-muted-foreground" />}
        actions={
          <Button variant="outline" size="sm" onClick={handleOpenAddModal}>
            <Plus className="h-4 w-4 mr-1" />
            新建任务
          </Button>
        }
      />
      <ChipBar
        options={chipOptions}
        value={status}
        onChange={(v) => setStatus(v as StatusType)}
        className="mb-2"
      />
      {tasks.length > 0 && (
        <TaskProgressBar total={tasks.length} counts={counts} />
      )}
      <TaskTableCard>
        <TaskBatchActions
          selectedCount={selectedIds.size}
          onClearSelection={handleClearSelection}
          onBatchRetry={handleBatchRetry}
          onBatchDelete={handleBatchDelete}
          batchProgress={batchProgress}
          onDismissProgress={() => setBatchProgress(null)}
          batchDetailOpen={batchDetailOpen}
          onToggleBatchDetail={() => setBatchDetailOpen((v) => !v)}
        />
        <div className="flex flex-wrap items-center gap-4 mb-4">
          <div className="flex-1 min-w-[200px]">
            <Input
              ref={searchInputRef}
              placeholder="搜索任务 ID、平台、账号（按 / 聚焦）"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              data-search-input
            />
          </div>
          <div className="flex items-center gap-2">
            <ClearTasksButton onConfirm={handleClear} />
            <Button onClick={handleOpenAddModal}>
              <Plus className="h-4 w-4 mr-1" />
              新建任务
            </Button>
            <Button
              variant="outline"
              onClick={refresh}
              aria-label="Refresh tasks"
            >
              {manualRefreshing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
            </Button>
            <Badge variant="secondary" className="text-xs">
              <Loader2 className="h-3 w-3 mr-1 animate-spin" />
              轮询中
            </Badge>
            <Tooltip>
              <TooltipTrigger asChild>
                <Badge variant="outline" className="text-[10px] cursor-help hidden sm:inline-flex">
                  R·N·/
                </Badge>
              </TooltipTrigger>
              <TooltipContent>
                <div className="space-y-1 text-xs">
                  <div>
                    <kbd className="px-1 py-0.5 rounded bg-muted border">R</kbd> 刷新列表
                  </div>
                  <div>
                    <kbd className="px-1 py-0.5 rounded bg-muted border">N</kbd> 新建任务
                  </div>
                  <div>
                    <kbd className="px-1 py-0.5 rounded bg-muted border">/</kbd> 聚焦搜索
                  </div>
                </div>
              </TooltipContent>
            </Tooltip>
          </div>
        </div>
        <TaskTable
          isLoading={isLoading}
          filtered={filtered}
          selectedIds={selectedIds}
          onToggle={handleToggleSelect}
          onToggleAll={handleToggleAll}
          onOpenDrawer={handleOpenDrawer}
          onRetry={handleRetry}
          onDelete={handleDelete}
          onStatusFilter={handleStatusBadgeClick}
          retrying={retrying}
          manualRefreshing={manualRefreshing}
          onRefresh={refresh}
          onAddTask={handleOpenAddModal}
        />
      </TaskTableCard>
      <TaskDrawer
        taskId={drawerTaskId}
        onClose={handleCloseDrawer}
        onRetry={handleRetry}
        retrying={retrying}
      />
      <AddTaskDialog
        open={addModalOpen}
        values={addForm}
        onChange={handleAddTaskChange}
        onConfirm={handleAddTaskConfirm}
        onCancel={handleCloseAddModal}
      />
    </div>
  )
}
const ClearTasksButton = ({ onConfirm }: { onConfirm: () => void }) => (
  <AlertDialog>
    <AlertDialogTrigger asChild>
      <Button variant="outline">
        <Trash2 className="h-4 w-4 mr-1" />
        清理
      </Button>
    </AlertDialogTrigger>
    <AlertDialogContent>
      <AlertDialogHeader>
        <AlertDialogTitle>确认清理</AlertDialogTitle>
        <AlertDialogDescription>清理所有已完成、失败、异常的任务？</AlertDialogDescription>
      </AlertDialogHeader>
      <AlertDialogFooter>
        <AlertDialogCancel>取消</AlertDialogCancel>
        <AlertDialogAction onClick={onConfirm}>清理</AlertDialogAction>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
)
