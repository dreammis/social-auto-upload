import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import { Dialog, DialogContent } from '@/components/ui/dialog'
import { useTasks } from '@/hooks/useTasks'
import { cn } from '@/lib/utils'

interface CommandPaletteProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const MAX_RESULTS = 8

function statusVariant(
  status?: string,
): 'info' | 'success' | 'warning' | 'error' | 'secondary' {
  switch (status) {
    case 'running':
      return 'info'
    case 'scheduled':
      return 'warning'
    case 'success':
      return 'success'
    case 'failed':
    case 'error':
      return 'error'
    default:
      return 'secondary'
  }
}

function statusLabel(status?: string): string {
  switch (status) {
    case 'running':
      return '执行中'
    case 'scheduled':
      return '定时中'
    case 'success':
      return '成功'
    case 'failed':
      return '失败'
    case 'error':
      return '异常'
    case 'pending':
      return '等待中'
    default:
      return status ?? '-'
  }
}

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const navigate = useNavigate()
  const { data: tasksData } = useTasks()
  // useMemo caches the same [] for repeated undefined — avoids dep-array churn
  // (inline `?? []` makes a new array ref every render).
  const tasks = useMemo(() => tasksData ?? [], [tasksData])
  const [query, setQuery] = useState('')

  // Reset the query field each time the dialog re-opens. Going through `onOpenChange`
  // (rather than a dedicated `useEffect`) keeps the state transition in one place so
  // the only thing that happens on open is closing the previous instance cleanly.
  const handleOpenChange = (nextOpen: boolean) => {
    if (nextOpen) setQuery('')
    onOpenChange(nextOpen)
  }

  const results = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return []
    return tasks
      .filter((t) => {
        return (
          (t.task_id ?? '').toLowerCase().includes(q) ||
          (t.platform ?? '').toLowerCase().includes(q) ||
          (t.action ?? '').toLowerCase().includes(q) ||
          (t.account ?? '').toLowerCase().includes(q)
        )
      })
      .slice(0, MAX_RESULTS)
  }, [query, tasks])

  const goToTasks = (taskId: string) => {
    onOpenChange(false)
    // Encode the focus param so TasksPage can match and auto-open that row's drawer.
    navigate(`/tasks?focus=${encodeURIComponent(taskId)}`)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[560px] gap-0 p-0 overflow-hidden">
        {/* Search input row */}
        <div className="flex items-center gap-3 px-4 h-12 border-b border-border/40">
          <Search className="h-4 w-4 text-muted-foreground shrink-0" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜索任务 ID / 平台 / 账号..."
            aria-label="搜索任务"
            autoFocus
            spellCheck={false}
            autoComplete="off"
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          />
          <kbd className="hidden sm:inline-flex h-5 items-center gap-1 px-1.5 rounded border border-border/40 bg-muted/40 text-[10px] font-mono text-muted-foreground">
            esc
          </kbd>
        </div>

        {/* Results list */}
        <div className="max-h-[420px] overflow-y-auto">
          {!query && (
            <div className="px-4 py-10 text-center text-sm text-muted-foreground">
              输入关键词搜索任务；回车跳转到任务列表
            </div>
          )}
          {query && results.length === 0 && (
            <div className="px-4 py-10 text-center text-sm text-muted-foreground">
              没有匹配任务
            </div>
          )}
          {results.length > 0 && (
            <ul className="py-1">
              {results.map((t) => {
                const variant = statusVariant(t.status)
                const shortId = (t.task_id ?? '').length > 12
                  ? `...${(t.task_id ?? '').slice(-10)}`
                  : t.task_id ?? '-'
                return (
                  <li key={t.task_id}>
                    <button
                      type="button"
                      onClick={() => goToTasks(t.task_id)}
                      className={cn(
                        'w-full text-left px-4 py-2.5 flex items-center gap-3 transition-colors',
                        'hover:bg-muted/60 focus:bg-muted/60 focus:outline-none',
                      )}
                    >
                      <span
                        className={cn(
                          'inline-flex shrink-0 items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full',
                          variant === 'info' &&
                            'bg-[var(--status-info-bg)] text-[var(--status-info-fg)]',
                          variant === 'success' &&
                            'bg-[var(--status-success-bg)] text-[var(--status-success-fg)]',
                          variant === 'warning' &&
                            'bg-[var(--status-warning-bg)] text-[var(--status-warning-fg)]',
                          variant === 'error' &&
                            'bg-[var(--status-error-bg)] text-[var(--status-error-fg)]',
                          variant === 'secondary' &&
                            'bg-secondary text-secondary-foreground',
                        )}
                      >
                        {statusLabel(t.status)}
                      </span>
                      <span className="font-mono text-xs text-muted-foreground shrink-0">
                        {shortId}
                      </span>
                      <span className="text-sm truncate">
                        {(t.platform ?? '-')} · {t.action ?? '-'} · {t.account ?? '-'}
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </div>

        {/* Footer hint */}
        <div className="flex items-center justify-between px-4 h-9 border-t border-border/40 text-[11px] text-muted-foreground bg-muted/30">
          <span>共 {tasks.length} 个任务</span>
          <span className="font-mono">⌘K 打开</span>
        </div>
      </DialogContent>
    </Dialog>
  )
}
