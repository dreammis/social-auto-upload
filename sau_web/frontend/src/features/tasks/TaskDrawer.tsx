import { memo, useEffect, useMemo, useRef } from 'react'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
  Badge,
  Button,
  Separator,
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/index'
import { FileText, Loader2, RotateCcw, Terminal } from 'lucide-react'
import { CliCommandBlock } from '@/components/CliCommand'
import { escapeQuotes } from '@/lib/utils'
import { useQuery } from '@tanstack/react-query'
import { api, type TaskItem } from '../../api/client'
import { useTaskLogs } from '../../hooks/useTasks'
import { formatDateTime, shortenId } from '@/lib/features'
import { STATUS_META } from './shared'
import { cn } from '@/lib/utils'
import { toneTextClass } from '@/lib/tone'

const TASKS_QUERY_KEY = ['tasks'] as const

/**
 * Slide-over panel + memoized body. Self-fetches the `task: TaskItem` from
 * the TanStack Query cache using only `taskId` so polling-churn on the
 * parent doesn't bust <TaskDrawer>'s memo. The body listens to cache
 * invalidations and refreshes the read on each render, so live status
 * changes still appear.
 */
export const TaskDrawer = memo(function TaskDrawer({
  taskId,
  onClose,
  onRetry,
  retrying,
}: {
  taskId: string | null
  onClose: () => void
  onRetry: (task: TaskItem) => void
  /** task_id currently being retried — drives the spinner in the drawer's primary button */
  retrying: string | null
}) {
  return (
    <Sheet open={taskId !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-[520px] sm:max-w-[520px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            任务详情
            {taskId && <TaskStatusBadge taskId={taskId} />}
          </SheetTitle>
          <SheetDescription>查看任务的详细信息和运行日志</SheetDescription>
        </SheetHeader>
        {taskId && (
          <div className="mt-4">
            <RetryButton taskId={taskId} onRetry={onRetry} retrying={retrying} />
            <TaskDrawerBody taskId={taskId} />
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
})

/**
 * Live badge that subscribes to cache updates. Re-rendering is local —
 * never busts the outer memo unless `taskId` truly changes.
 */
const TaskStatusBadge = memo(function TaskStatusBadge({ taskId }: { taskId: string }) {
  const task = useTaskFromCache(taskId)
  const meta = STATUS_META[task?.status ?? 'pending'] ?? STATUS_META.pending
  return <Badge variant={meta.variant}>{meta.label}</Badge>
})

const RetryButton = memo(function RetryButton({
  taskId,
  onRetry,
  retrying,
}: {
  taskId: string
  onRetry: (task: TaskItem) => void
  retrying: string | null
}) {
  const task = useTaskFromCache(taskId)
  const canRetry = task && (task.status === 'failed' || task.status === 'error')
  if (!canRetry) return null
  return (
    <Button
      className="w-full mb-4"
      onClick={() => {
        onRetry(task)
      }}
    >
      {retrying === taskId ? (
        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
      ) : (
        <RotateCcw className="h-4 w-4 mr-2" />
      )}
      重试此任务
    </Button>
  )
})

/**
 * Detail body — task metadata + collapsible log accordion. Memoized on
 * `taskId` only.
 */
const TaskDrawerBody = memo(function TaskDrawerBody({ taskId }: { taskId: string }) {
  const task = useTaskFromCache(taskId)
  const { data: taskLogs = [], isLoading: logsLoading } = useTaskLogs(
    task?.task_id ?? null,
    task?.status,
  )
  const statusMeta = STATUS_META[task?.status ?? 'pending'] ?? STATUS_META.pending
  const logsEndRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [taskLogs])

  const command = useMemo(() => {
    if (!task) return null
    if (task.argv) {
      try {
        const argv = JSON.parse(task.argv) as string[]
        return argv.join(' ')
      } catch {
        return task.argv
      }
    }
    if (task.platform && task.action && task.account) {
      return `sau ${escapeQuotes(task.platform)} ${escapeQuotes(task.action)} --account "${escapeQuotes(task.account)}"`
    }
    return null
  }, [task])

  if (!task) return null

  return (
    <div className="space-y-4">
      <div className="space-y-3">
        <Field label="任务 ID">
          <code className="text-xs bg-muted px-2 py-1 rounded max-w-[300px] truncate" title={task.task_id}>
            {task.task_id}
          </code>
        </Field>
        <Separator />
        <Field label="平台" value={task.platform} />
        <Separator />
        <Field label="动作" value={task.action} />
        <Separator />
        <Field label="账号" value={task.account} />
        <Separator />
        <Field label="状态" alignRight>
          <Badge variant={statusMeta.variant}>{statusMeta.label}</Badge>
        </Field>
        <Separator />
        <Field label="创建时间" value={formatDateTime(task.created)} />
        <Separator />
        <Field label="退出码" alignRight>
          {task.code !== undefined && task.code !== null ? (
            <Badge variant={task.code === 0 ? 'success' : 'error'}>{task.code}</Badge>
          ) : (
            <span className="text-sm">-</span>
          )}
        </Field>
        {task.error && (
          <>
            <Separator />
            <div className="space-y-2">
              <span className="text-sm text-muted-foreground">错误信息</span>
              <pre className="text-xs bg-muted p-2 rounded-lg overflow-auto max-h-[200px] whitespace-pre-wrap">
                {task.error}
              </pre>
            </div>
          </>
        )}
        <ResultSection result={task.result} />
        {command && (
          <>
            <Separator />
            <div className="space-y-2">
              <span className="text-sm text-muted-foreground flex items-center gap-1">
                <Terminal className="h-3.5 w-3.5" />
                CLI 命令
              </span>
              <CliCommandBlock command={command} className="max-h-[200px]" />
              <p className="text-[10px] text-muted-foreground/60">
                {task.argv
                  ? '点击命令区域可复制，用于在终端中手动重试'
                  : '基础命令预览（完整参数请参考原始提交或任务日志）'}
              </p>
            </div>
          </>
        )}
      </div>

      <Accordion
        type="single"
        collapsible
        defaultValue={
          task.status === 'running' || task.status === 'failed' || task.status === 'error' ? 'logs' : undefined
        }
      >
        <AccordionItem value="logs">
          <AccordionTrigger>
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              <span className="font-medium">运行日志</span>
              <Badge variant="secondary">{taskLogs.length} 条</Badge>
              {(task.status === 'pending' || task.status === 'running') && (
                // Spinner color: --status-info-fg via `@/lib/tone`
                // (matches the lavender "task in flight" cue used elsewhere).
                <Loader2 className={cn('h-4 w-4 animate-spin', toneTextClass('info'))} />
              )}
            </div>
          </AccordionTrigger>
          <AccordionContent>
            <div className="rounded-lg bg-muted p-3 font-mono text-xs leading-relaxed max-h-[400px] overflow-auto">
              {logsLoading ? (
                <p className="text-muted-foreground">加载中...</p>
              ) : taskLogs.length === 0 ? (
                <p className="text-muted-foreground">暂无日志</p>
              ) : (
                <>
                  {taskLogs.map((entry, idx) => (
                    <div key={idx} className="mb-0.5">
                      {/* Log-line timestamp uses --status-success-fg via
                          `@/lib/tone` to keep the running-log chrome aligned
                          with LogsPage's mint-green timestamp convention. */}
                      <span className={cn('mr-2', toneTextClass('success'))}>{entry.ts}</span>
                      <span className="text-foreground">{entry.message}</span>
                    </div>
                  ))}
                  <div ref={logsEndRef} />
                </>
              )}
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>
  )
})

/**
 * Key/value row helper used by the detail panel.
 */
const Field = memo(function Field({
  label,
  value,
  children,
  alignRight,
}: {
  label: string
  value?: string
  children?: React.ReactNode
  alignRight?: boolean
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-muted-foreground">{label}</span>
      {alignRight ? children : <span className="text-sm">{value ?? children ?? '-'}</span>}
    </div>
  )
})

function ResultSection({ result }: { result?: string | null }) {
  if (!result) return null
  let parsed: Record<string, string>
  try {
    parsed = JSON.parse(result)
  } catch {
    return null
  }
  const entries = Object.entries(parsed).filter(
    ([, v]) => v !== undefined && v !== null && v !== '',
  )
  if (entries.length === 0) return null
  return (
    <>
      {entries.map(([key, value]) => {
        let label = key
        if (key === 'video_url') label = '视频链接'
        else if (key === 'publish_status') label = '发布状态'
        else if (key === 'verified') label = '发布验证'
        return (
          <div key={key}>
            <Separator className="my-2" />
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">{label}</span>
              {key === 'verified' ? (
                <Badge variant={value === 'true' ? 'success' : 'warning'}>
                  {value === 'true' ? '已验证' : '未验证'}
                </Badge>
              ) : key === 'video_url' && value ? (
                <a
                  href={value}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-primary hover:underline max-w-[200px] truncate block"
                >
                  {value}
                </a>
              ) : (
                <span className="text-sm max-w-[200px] truncate">{String(value)}</span>
              )}
            </div>
          </div>
        )
      })}
    </>
  )
}

/**
 * Reads a single task from the TanStack Query cache. Subscribes directly
 * to the parent `['tasks']` query (instead of a synthetic by-id subquery),
 * so the drawer's render naturally fires whenever the polling list is
 * invalidated. No secondary query, no error-retry loop on initial mount.
 */
function useTaskFromCache(taskId: string | null): TaskItem | undefined {
  const { data: tasks } = useQuery({
    queryKey: TASKS_QUERY_KEY,
    queryFn: async () => {
      const res = await api.getTasks()
      return res.data ?? []
    },
    // Mirror the parent query's freshness so the drawer doesn't refetch on
    // its own; it stays a pure subscriber to list updates.
    staleTime: 1_000,
  })
  return tasks?.find((t) => t.task_id === taskId)
}

// silence unused-import warning for the LiveBadge short-circuit shape above
void shortenId
