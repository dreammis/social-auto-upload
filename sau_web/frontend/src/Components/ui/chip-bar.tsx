import { type ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { toneChipClasses, toneRingClass } from '@/lib/tone'

export type ChipBarVariant =
  | 'neutral'
  | 'info'
  | 'success'
  | 'warning'
  | 'error'

export interface ChipBarOption {
  /** Stable identity used by `value` / `onChange` */
  value: string
  /** Human-readable label */
  label: string
  /** Optional count, rendered as a small tabular figure */
  count?: number
  /** Optional leading icon (use lucide-react icons at h-3.5 / w-3.5) */
  icon?: ReactNode
  /** Semantic palette for the active state. Defaults to `neutral`. */
  variant?: ChipBarVariant
}

interface ChipBarProps {
  options: ChipBarOption[]
  /** Currently selected value */
  value: string
  /** Receives the clicked option's `value` */
  onChange: (value: string) => void
  /** Optional additional class names applied to the outer row */
  className?: string
}

/**
 * Horizontal row of clickable filter chips. Each chip shows
 *   `icon · label · count`
 * and clicking it sets `value` via `onChange`. The active chip uses the
 * semantic palette in `index.css` (`--status-*-bg/fg`, `--status-*-fg/30`),
 * composed via `@/lib/tone` so it shares a vocabulary with Badge / Alert /
 * Toast / ValidityBadge.
 *
 * The four status-keyed variants share a `toneChipClasses · /30 ring`
 * shape; `neutral` is intentionally distinct (uses `bg-foreground` /
 * `ring-foreground/20` for the "no-status / action button" case).
 *
 * Designed to replace the traditional "stats cards on top + Select on the
 * side" pattern: the same surface both communicates state (counts) and
 * triggers filtering (one click), so a user reads *and* operates the
 * dashboard in one glance.
 */
const ACTIVE_CLASS: Record<ChipBarVariant, string> = {
  neutral: 'bg-foreground text-background ring-foreground/20',
  // `Record<ChipBarVariant, string>` already narrows the four status keys;
  // no `satisfies Tone` needed.
  info: cn(toneChipClasses('info'), `${toneRingClass('info')}/30`),
  success: cn(toneChipClasses('success'), `${toneRingClass('success')}/30`),
  warning: cn(toneChipClasses('warning'), `${toneRingClass('warning')}/30`),
  error: cn(toneChipClasses('error'), `${toneRingClass('error')}/30`),
}

export function ChipBar({ options, value, onChange, className }: ChipBarProps) {
  return (
    <div
      role="group"
      aria-label="筛选"
      className={cn('flex flex-wrap items-center gap-1.5', className)}
    >
      {options.map((opt) => {
        const active = opt.value === value
        const variant = opt.variant ?? 'neutral'
        return (
          <button
            key={opt.value}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(opt.value)}
            className={cn(
              'inline-flex h-8 items-center gap-1.5 rounded-full px-3 text-xs font-medium ring-1 transition-all duration-150',
              active
                ? ACTIVE_CLASS[variant]
                : 'ring-border/40 text-muted-foreground hover:bg-foreground/[0.04] hover:text-foreground',
            )}
          >
            {opt.icon && (
              <span className="flex h-3.5 w-3.5 items-center justify-center">
                {opt.icon}
              </span>
            )}
            <span className="truncate">{opt.label}</span>
            {opt.count !== undefined && (
              <span
                className={cn(
                  'tabular-nums text-[10px] font-semibold',
                  active ? 'opacity-80' : 'opacity-50',
                )}
              >
                {opt.count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
