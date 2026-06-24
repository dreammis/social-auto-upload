import { memo, useMemo } from 'react'
import {
  Badge,
  Button,
  Card,
  CardContent,
  Checkbox,
  EmptyState,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/index'
import { BarChart3, Loader2, Plus, RefreshCw } from 'lucide-react'
import type { TaskItem } from '../../api/client'
import { TaskTableRow, TaskTableRowSkeleton } from './TaskTableRow'
import type { StatusType } from './shared'

/**
 * Table renderer. NOT memoized — it legitimately re-renders on filter
 * changes (`isLoading`, `filtered.length`, `selectedIds.size`). Row-level
 * memoization via <TaskTableRow> keeps the per-row churn scoped: when
 * polling replaces `data` with a new array reference, TanStack Query keeps
 * the per-item reference stable for unchanged tasks, so unaffected rows
 * skip re-rendering.
 */
export const TaskTable = memo(function TaskTable({
  isLoading,
  filtered,
  selectedIds,
  onToggle,
  onToggleAll,
  onOpenDrawer,
  onRetry,
  onDelete,
  onStatusFilter,
  retrying,
  manualRefreshing,
  onRefresh,
  onAddTask,
}: {
  isLoading: boolean
  filtered: TaskItem[]
  selectedIds: Set<string>
  onToggle: (taskId: string, checked: boolean) => void
  onToggleAll: (checked: boolean) => void
  onOpenDrawer: (task: TaskItem) => void
  onRetry: (task: TaskItem) => void
  onDelete: (taskId: string) => void
  onStatusFilter: (s: StatusType) => void
  retrying: string | null
  manualRefreshing: boolean
  onRefresh: () => void
  onAddTask: () => void
}) {
  const allVisibleSelected = useMemo(
    () => filtered.length > 0 && filtered.every((t) => selectedIds.has(t.task_id)),
    [filtered, selectedIds],
  )
  const someVisibleSelected = useMemo(
    () => filtered.some((t) => selectedIds.has(t.task_id)),
    [filtered, selectedIds],
  )
  const headerChecked: boolean | 'indeterminate' = allVisibleSelected
    ? true
    : someVisibleSelected
      ? 'indeterminate'
      : false

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[40px] px-2">
              <Checkbox
                checked={headerChecked}
                onCheckedChange={(checked) => onToggleAll(checked === true)}
                aria-label="全选"
              />
            </TableHead>
            <TableHead className="w-[220px]">任务 ID</TableHead>
            <TableHead className="w-[110px]">平台</TableHead>
            <TableHead className="w-[140px]">动作</TableHead>
            <TableHead className="w-[140px]">账号</TableHead>
            <TableHead className="w-[110px]">状态</TableHead>
            <TableHead className="w-[180px]">创建时间</TableHead>
            <TableHead className="w-[240px] border-l">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading &&
            Array.from({ length: 5 }).map((_, i) => <TaskTableRowSkeleton key={i} />)}
          {!isLoading && filtered.length === 0 && (
            <TableRow>
              <TableCell colSpan={8}>
                <EmptyState
                  icon={<BarChart3 className="h-6 w-6" />}
                  title="暂无任务"
                  description="创建任务后会在这里显示"
                  action={
                    <div className="flex items-center gap-2">
                      <Button size="sm" onClick={onAddTask}>
                        <Plus className="h-4 w-4 mr-1" />
                        新建任务
                      </Button>
                      <Button size="sm" variant="outline" onClick={onRefresh}>
                        {manualRefreshing ? (
                          <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                        ) : (
                          <RefreshCw className="h-4 w-4 mr-1" />
                        )}
                        刷新列表
                      </Button>
                    </div>
                  }
                />
              </TableCell>
            </TableRow>
          )}
          {!isLoading &&
            filtered.map((record) => (
              <TaskTableRow
                key={record.task_id}
                task={record}
                selected={selectedIds.has(record.task_id)}
                onToggle={onToggle}
                onOpenDrawer={onOpenDrawer}
                onRetry={onRetry}
                onDelete={onDelete}
                onStatusFilter={onStatusFilter}
                retrying={retrying}
              />
            ))}
        </TableBody>
      </Table>
    </div>
  )
})

/** Re-export the toolbar badges so TasksPage can render the polling chip and shortcut hints. */
export function TaskToolbarExtras({ manualRefreshing }: { manualRefreshing: boolean }) {
  return (
    <>
      {manualRefreshing ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <RefreshCw className="h-4 w-4" />
      )}
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
    </>
  )
}

/** Compact Card wrapper used by TasksPage to host the table and batch panel. */
export function TaskTableCard({ children }: { children: React.ReactNode }) {
  return (
    <Card className="card-refined">
      <CardContent className="pt-6">{children}</CardContent>
    </Card>
  )
}

