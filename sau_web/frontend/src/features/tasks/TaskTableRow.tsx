import { memo } from 'react'
import {
  Badge,
  Button,
  Checkbox,
  Skeleton,
  TableCell,
  TableRow,
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/index'
import { Loader2, RotateCcw, Trash2 } from 'lucide-react'
import type { TaskItem } from '../../api/client'
import { formatDateTime, shortenId } from '@/lib/features'
import { STATUS_META, type StatusType } from './shared'

/**
 * Single table row. Memoized because table polls every 3s — without memo,
 * every row would re-render even when only one status badge changed. TanStack
 * Query stabilizes the `task` reference for unchanged items, so React.memo's
 * shallow-equal check skips re-rendering the other 49 rows.
 *
 * The actions don't memoize further: hover tooltips / Radix dialogs are cheap.
 */
export const TaskTableRow = memo(function TaskTableRow({
  task,
  selected,
  onToggle: _onToggle,
  onOpenDrawer,
  onRetry,
  onDelete,
  onStatusFilter,
  retrying,
}: {
  task: TaskItem
  selected: boolean
  onToggle: (taskId: string, checked: boolean) => void
  onOpenDrawer: (task: TaskItem) => void
  onRetry: (task: TaskItem) => void
  onDelete: (taskId: string) => void
  onStatusFilter: (status: StatusType) => void
  retrying: string | null
}) {
  const meta = STATUS_META[task.status ?? 'pending'] ?? STATUS_META.pending
  const canDelete =
    task.status === 'success' ||
    task.status === 'failed' ||
    task.status === 'error' ||
    task.status === 'scheduled'
  const canRetry = task.status === 'failed' || task.status === 'error'

  return (
    <TableRow className="table-row-refined">
      <TableCell className="px-2">
        <Checkbox
          checked={selected}
          onCheckedChange={(checked) => _onToggle(task.task_id, checked === true)}
          aria-label={`选择任务 ${shortenId(task.task_id)}`}
        />
      </TableCell>
      <TableCell>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              className="cursor-pointer hover:text-primary hover:underline transition-colors"
              aria-label="查看任务详情"
              onClick={() => onOpenDrawer(task)}
            >
              <code className="text-xs bg-muted px-2 py-1 rounded">{shortenId(task.task_id)}</code>
            </button>
          </TooltipTrigger>
          <TooltipContent>{task.task_id}</TooltipContent>
        </Tooltip>
      </TableCell>
      <TableCell>{task.platform || '-'}</TableCell>
      <TableCell>{task.action || '-'}</TableCell>
      <TableCell>{task.account || '-'}</TableCell>
      <TableCell>
        <Badge
          variant={meta.variant}
          className="cursor-pointer hover:ring-2 hover:ring-primary/30 transition-all"
          onClick={() => {
            const nextStatus = (task.status ?? 'pending') as StatusType
            onStatusFilter(nextStatus)
          }}
          title={`筛选「${meta.label}」任务`}
        >
          {meta.label}
        </Badge>
      </TableCell>
      <TableCell className="whitespace-nowrap">{formatDateTime(task.created)}</TableCell>
      <TableCell className="border-l">
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" onClick={() => onOpenDrawer(task)}>
            详情
          </Button>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                disabled={!canRetry}
                onClick={() => onRetry(task)}
                aria-label="Retry task"
              >
                {retrying === task.task_id ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RotateCcw className="h-4 w-4" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent>重新执行此任务</TooltipContent>
          </Tooltip>
          {canDelete && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-destructive hover:text-destructive"
                  aria-label="Delete task"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>确认删除</AlertDialogTitle>
                  <AlertDialogDescription>确认删除此任务？</AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>取消</AlertDialogCancel>
                  <AlertDialogAction onClick={() => onDelete(task.task_id)}>删除</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
        </div>
      </TableCell>
    </TableRow>
  )
})

/**
 * Skeleton placeholder row — used by TaskTable during the initial fetch.
 */
export const TaskTableRowSkeleton = memo(function TaskTableRowSkeleton() {
  return (
    <TableRow>
      <TableCell className="px-2">
        <Skeleton className="h-4 w-4 rounded-sm" />
      </TableCell>
      <TableCell>
        <Skeleton className="h-5 w-[120px] rounded" />
      </TableCell>
      <TableCell>
        <Skeleton className="h-4 w-[60px] rounded" />
      </TableCell>
      <TableCell>
        <Skeleton className="h-4 w-[80px] rounded" />
      </TableCell>
      <TableCell>
        <Skeleton className="h-4 w-[80px] rounded" />
      </TableCell>
      <TableCell>
        <Skeleton className="h-5 w-[50px] rounded-full" />
      </TableCell>
      <TableCell>
        <Skeleton className="h-4 w-[130px] rounded" />
      </TableCell>
      <TableCell className="border-l">
        <div className="flex items-center gap-1">
          <Skeleton className="h-7 w-10 rounded" />
          <Skeleton className="h-7 w-8 rounded" />
          <Skeleton className="h-7 w-8 rounded" />
        </div>
      </TableCell>
    </TableRow>
  )
})
