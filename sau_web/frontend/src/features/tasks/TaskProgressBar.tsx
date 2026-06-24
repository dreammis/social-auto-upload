import { memo } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { toneFillBgClass } from '@/lib/tone'

type TaskCounts = Record<string, number>

type ProgressSegment = {
  key: string
  label: string
  count: number
  barClass: string
}

type TaskProgressBarProps = {
  total: number
  counts: TaskCounts
}

const completedKeys = ['success']
const activeKeys = ['running', 'pending', 'scheduled']
const failedKeys = ['failed', 'error']

function sum(keys: string[], counts: TaskCounts) {
  return keys.reduce((s, k) => s + (counts[k] ?? 0), 0)
}

function segments(total: number, counts: TaskCounts): ProgressSegment[] {
  const done = sum(completedKeys, counts)
  const active = sum(activeKeys, counts)
  const failed = sum(failedKeys, counts)

  if (total === 0) return [{ key: 'empty', label: '暂无任务', count: 0, barClass: 'bg-muted' }]

  // barClass is the bar-segment fill color. Composed via `@/lib/tone`'s
  // `toneFillBgClass` so the segment fill is sourced from the same
  // `--status-X-fg` token vocabulary as Badge / Alert / Toast / ChipBar /
  // ValidityBadge. The literal `bg-[var(--status-X-fg)]` strings only
  // appear in `@/lib/tone` — Tailwind v4 auto-scanner picks them up there.
  return [
    { key: 'done', label: '成功', count: done, barClass: toneFillBgClass('success') },
    { key: 'active', label: '进行中', count: active, barClass: toneFillBgClass('info') },
    { key: 'failed', label: '失败/异常', count: failed, barClass: toneFillBgClass('error') },
  ].filter((s) => s.count > 0)
}

/**
 * Stacked progress bar summarising task status distribution.
 * Pure presentational — reads from pre-computed counts.
 */
export const TaskProgressBar = memo(function TaskProgressBar({
  total,
  counts,
}: TaskProgressBarProps) {
  const segs = segments(total, counts)

  return (
    <Card className="border-border/40 shadow-none">
      <CardContent className="flex items-center gap-4 p-4">
        {/* Bar */}
        <div className="flex flex-1 h-2.5 rounded-full overflow-hidden bg-muted">
          {segs.map((s) => (
            <div
              key={s.key}
              className={cn('h-full transition-all duration-500', s.barClass)}
              style={{ width: total > 0 ? `${(s.count / total) * 100}%` : '100%' }}
            />
          ))}
        </div>

        {/* Stats */}
        <div className="flex items-center gap-4 text-xs text-muted-foreground whitespace-nowrap">
          {segs.map((s) => (
            <div key={s.key} className="flex items-center gap-1.5">
              <span className={cn('h-2 w-2 rounded-full', s.barClass)} />
              <span>{s.label}</span>
              <span className="font-medium tabular-nums">{s.count}</span>
            </div>
          ))}
          <div className="flex items-center gap-1.5 border-l border-border pl-4">
            <span>总计</span>
            <span className="font-medium tabular-nums">{total}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
})
