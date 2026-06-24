import { memo, useMemo, type ReactNode } from 'react'
import { ArrowUpRight, Folders, Loader2, Plus, Send, ShieldCheck } from 'lucide-react'
import { PLATFORMS, type TaskItem } from '@/api/client'
import { useAccountGroups } from '@/hooks/useAccountGroups'
import { useTasks } from '@/hooks/useTasks'
import { cn } from '@/lib/utils'
import {
  rateToTone,
  toneChipClasses,
  toneDotClasses,
  type Tone,
} from '@/lib/tone'

/* ── Public overview props ──────────────────────────────────────────── */

interface HomepageOverviewProps {
  /** Triggered by the inline CTA when the user has zero groups. */
  onCreateGroup?: () => void
  /** Triggered by the "validity" tile when at least one authorization exists. */
  onCheckAllStatus?: () => void
  /** Triggered by the "recent publish" tile to navigate to /tasks. */
  onOpenTasks?: () => void
  /** Triggered by "recent publish" empty-state to navigate to /publish. */
  onOpenPublish?: () => void
}

/* ── Tone mappers ───────────────────────────────────────────────────── */

/** Maps backend task.status → Chinese label + Tone (nullable). Mirrors
 *  the union handled by TasksPage. `null` = "unknown / no data". */
function taskStatusDisplay(status?: string): { label: string; tone: Tone | null } {
  if (!status) return { label: '未知', tone: null }
  switch (status) {
    case 'success':
      return { label: '成功', tone: 'success' }
    case 'failed':
      return { label: '失败', tone: 'error' }
    case 'error':
      return { label: '异常', tone: 'error' }
    case 'pending':
      return { label: '等待', tone: 'warning' }
    case 'running':
      return { label: '运行中', tone: 'warning' }
    case 'scheduled':
      return { label: '已计划', tone: 'info' }
    default:
      return { label: status, tone: null }
  }
}

function platformLabel(value?: string): string {
  if (!value) return ''
  return PLATFORMS.find((p) => p.value === value)?.label ?? value
}

/** Compact "…​5 minutes ago" formatter — zh-CN, no seconds granularity. */
function timeAgo(iso?: string): string {
  if (!iso) return '—'
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return '—'
  const diffSec = Math.max(0, Math.floor((Date.now() - t) / 1000))
  if (diffSec < 60) return '刚刚'
  const mins = Math.floor(diffSec / 60)
  if (mins < 60) return `${mins} 分钟前`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs} 小时前`
  const days = Math.floor(hrs / 24)
  if (days < 30) return `${days} 天前`
  return new Date(t).toLocaleDateString('zh-CN')
}

/** Mirror publish/shared.formatTaskId — ellipsises long IDs to last 10 chars. */
function compactTaskId(value?: string): string {
  if (!value) return ''
  return value.length > 14 ? `…${value.slice(-10)}` : value
}

/* ── Single stat tile ───────────────────────────────────────────────── */

interface TileProps {
  icon: ReactNode
  label: string
  value: ReactNode
  hint?: ReactNode
  /** Tone for the icon-chip background. `null` → muted neutral. */
  accent: Tone | null
  onClick?: () => void
  footer?: ReactNode
  /** Render the value with muted foreground color — signals "zero / empty"
   *  state vs primary foreground for "active / positive" data. Linear
   *  convention: tertiary ink on passive metrics, full ink on actionable ones. */
  muted?: boolean
}

function Tile({ icon, label, value, hint, accent, onClick, footer, muted }: TileProps) {
  const interactive = Boolean(onClick)
  return (
    <div
      className={cn(
        // Solid `card-refined` + relative overflow-hidden hosts the
        // absolute top-light sheen below. No transition on the base —
        // non-interactive tiles have no hover state to animate.
        'card-refined relative overflow-hidden p-4',
        // Single Tailwind arbitrary transition covers color (bg hover
        // from `.card-refined:hover`) AND transform (micro-lift)
        // under one `transition-property` declaration — avoids the
        // source-order cascade collision two separate `transition-*`
        // classes would trigger. The lift is gated alone behind
        // `motion-safe:`; color hover stays visible for reduced-motion
        // users since color is not a vestibular trigger.
        interactive && 'cursor-pointer group transition-[color,background-color,border-color,fill,stroke,transform] duration-200 motion-safe:hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-background',
      )}
      onClick={onClick}
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      onKeyDown={
        interactive
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                onClick?.()
              }
            }
          : undefined
      }
      aria-label={interactive ? label : undefined}
    >
      {/* Linear-style top-light sheen — pale white gradient on the upper
          edge for tactile card depth. Mirrors ambient light on a real card. */}
      <span
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/[0.08] to-transparent"
      />

      <div className="flex items-start justify-between gap-2 mb-3">
        {/* Linear-style icon tile: tone-coloured bg+fg with inset shadow
            stacking for "raised tactile surface" feel (top highlight + bottom
            shade). 9×9 (was 8×8) matches the page-header icon for visual
            hierarchy parity across the app's chrome surfaces. */}
        <div
          className={cn(
            'relative flex h-9 w-9 items-center justify-center rounded-lg',
            // Top-only highlight: the original bottom-shade had
            // `oklch(0 0 0 / 0.04)` — black at 4% is invisible against
            // either surface. The icon tile reads as "raised" via the
            // single top-light cap alone; the bottom shade was a
            // vestigial component of the Linear template, dropped.
            'shadow-[inset_0_1px_0_oklch(1_0_0_/_0.08)]',
            toneChipClasses(accent),
          )}
        >
          {icon}
          {/* Inner top-light — sharp 1px sheen accent on the icon tile. */}
          <span
            aria-hidden="true"
            className="pointer-events-none absolute inset-x-1 top-1 h-px bg-gradient-to-r from-transparent via-white/[0.10] to-transparent"
          />
        </div>
        {interactive && (
          <ArrowUpRight
            aria-hidden="true"
            // Color shift is fine for reduced-motion users (no vestibular
            // trigger); only the transform group-hover gets motion-safe
            // gating so the chevron doesn't slide while the card stays
            // static for `prefers-reduced-motion: reduce` users.
            className="h-4 w-4 text-muted-foreground/40 group-hover:text-foreground/80 motion-safe:transition-transform motion-safe:duration-200 motion-safe:group-hover:translate-x-0.5 motion-safe:group-hover:-translate-y-0.5"
          />
        )}
      </div>

      <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/70">
        {label}
      </div>
      <div
        className={cn(
          'text-[26px] font-semibold tracking-tighter tabular-nums leading-none mt-1.5',
          muted ? 'text-muted-foreground/70' : 'text-foreground',
        )}
      >
        {value}
      </div>
      {hint && <div className="text-[12px] text-muted-foreground/80 mt-1.5">{hint}</div>}
      {footer && <div className="mt-2.5">{footer}</div>}
    </div>
  )
}

/* ── Public overview component ──────────────────────────────────────── */

function HomepageOverviewImpl({
  onCreateGroup,
  onCheckAllStatus,
  onOpenTasks,
  onOpenPublish,
}: HomepageOverviewProps) {
  const { data: groups = [], isLoading: isGroupsLoading } = useAccountGroups()
  const { data: tasks = [] } = useTasks()

  const metrics = useMemo(() => {
    const totalGroups = groups.length
    const auths = groups.flatMap((g) => g.authorizations)
    const authTotal = auths.length
    const authValid = auths.filter((a) => a.valid).length
    const authRate = authTotal > 0 ? authValid / authTotal : 0

    const inFlightCount = tasks.filter(
      (t) => t.status === 'pending' || t.status === 'running',
    ).length

    /* Single-pass O(N) latest-task lookup — banner only needs the most
     * recent entry, so a full sort is wasted work on 1000+ task lists. */
    const lastTask: TaskItem | undefined =
      tasks.length > 0
        ? tasks.reduce<TaskItem>((latest, t) => {
            const a = latest.created ?? ''
            const b = t.created ?? ''
            return b.localeCompare(a) > 0 ? t : latest
          }, tasks[0])
        : undefined

    return {
      totalGroups,
      authTotal,
      authValid,
      authRate,
      inFlightCount,
      lastTask,
      taskCount: tasks.length,
    }
  }, [groups, tasks])

  // Branded empty state — only shown when not loading AND the user has
  // zero groups. Skin: muted card with right-aligned primary CTA.
  if (!isGroupsLoading && metrics.totalGroups === 0) {
    return (
      <div className="rounded-xl border border-dashed border-border/60 bg-muted/20 p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <div
            className={cn(
              'flex h-10 w-10 items-center justify-center rounded-xl flex-shrink-0',
              toneChipClasses('info'),
            )}
          >
            <Folders className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/70">
              账号分组
            </div>
            <div className="text-base font-semibold text-foreground mt-0.5">尚未创建分组</div>
            <div className="text-[12px] text-muted-foreground/80 mt-0.5">
              建一个分组，再开始给各平台添加授权
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={onCreateGroup}
          className={cn(
            'btn-elegant inline-flex items-center justify-center gap-1.5 rounded-md px-3.5 py-2',
            'bg-primary text-primary-foreground text-[13px] font-medium',
            'hover:opacity-90 transition-opacity self-start sm:self-auto',
          )}
        >
          <Plus className="h-4 w-4" />
          新建分组
        </button>
      </div>
    )
  }

  // Loading shells (rare because useAccountGroups is fast; cheap to render).
  if (isGroupsLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            // Skeleton stays on `bg-card/40` (NOT `card-refined`) so the
            // `animate-pulse` 100%→50% opacity modulation is visible
            // against the half-opacity base. A solid surface damps the
            // pulse to invisibility, defeating the loading affordance —
            // this is the only place the legacy `bg-card/40` shape is
            // intentionally retained.
            className="rounded-xl border border-border/40 bg-card/40 p-4 min-h-[130px] animate-pulse"
          />
        ))}
      </div>
    )
  }

  /* Tile-level JSX inlined below so the parent controls render order
   * directly. Tile is intentionally not memo-wrapped: a fresh icon element
   * is produced each render and memo() would never hit anyway. */

  const lastStatus = taskStatusDisplay(metrics.lastTask?.status)
  const lastTileContent = metrics.lastTask ? (
    <div className="flex items-center gap-1.5 flex-wrap">
      <span
        className={cn(
          'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium',
          toneChipClasses(lastStatus.tone),
        )}
      >
        <span className={cn('w-1.5 h-1.5 rounded-full', toneDotClasses(lastStatus.tone))} />
        {lastStatus.label}
      </span>
      <span className="text-[10px] font-mono text-muted-foreground/70">
        {compactTaskId(metrics.lastTask.task_id)}
      </span>
    </div>
  ) : null

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
      <Tile
        icon={<Folders className="h-4 w-4" />}
        label="账号分组"
        value={metrics.totalGroups}
        hint={
          metrics.authTotal > 0
            ? `${metrics.authTotal} 个平台授权`
            : '尚无平台授权'
        }
        accent="info"
      />
      <Tile
        icon={<ShieldCheck className="h-4 w-4" />}
        label="有效率"
        value={metrics.authTotal > 0 ? `${Math.round(metrics.authRate * 100)}%` : '—'}
        hint={
          metrics.authTotal > 0
            ? `${metrics.authValid} / ${metrics.authTotal} 个授权正常`
            : '暂无授权可检测'
        }
        accent={rateToTone(metrics.authRate, metrics.authTotal)}
        onClick={metrics.authTotal > 0 ? onCheckAllStatus : undefined}
        muted={metrics.authTotal === 0}
      />
      <Tile
        icon={<Send className="h-4 w-4" />}
        label="最近发布"
        value={
          metrics.lastTask ? (
            <span className="inline-block max-w-full truncate align-middle">
              {platformLabel(metrics.lastTask.platform) ||
                metrics.lastTask.action ||
                '—'}
            </span>
          ) : metrics.taskCount > 0 ? (
            <span className="text-muted-foreground/60 text-[18px]">—</span>
          ) : (
            <span className="text-muted-foreground/60 text-[18px]">暂无</span>
          )
        }
        hint={
          metrics.lastTask
            ? `${metrics.lastTask.account ?? '—'} · ${timeAgo(metrics.lastTask.created)}`
            : metrics.taskCount > 0
              ? '查看上方任务记录'
              : '去发布中心提交一个任务吧'
        }
        accent={lastStatus.tone}
        onClick={
          metrics.lastTask
            ? onOpenTasks
            : metrics.taskCount > 0
              ? onOpenTasks
              : onOpenPublish
        }
        footer={lastTileContent}
      />
      <Tile
        icon={
          <Loader2
            className={cn(
              'h-4 w-4',
              metrics.inFlightCount > 0 && 'animate-spin',
            )}
          />
        }
        label="正在运行"
        value={metrics.inFlightCount}
        hint={
          metrics.inFlightCount > 0
            ? `${metrics.inFlightCount} 个任务进行中`
            : metrics.taskCount > 0
              ? '当前没有运行中的任务'
              : '尚无历史任务'
        }
        accent={metrics.inFlightCount > 0 ? 'warning' : null}
        onClick={metrics.taskCount > 0 ? onOpenTasks : undefined}
        muted={metrics.inFlightCount === 0}
      />
    </div>
  )
}

export const HomepageOverview = memo(HomepageOverviewImpl)
