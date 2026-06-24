import { type ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { toneFillBgClass, toneStyleClasses } from '@/lib/tone'

interface PageHeaderProps {
  title: string
  description?: string
  icon?: ReactNode
  actions?: ReactNode
  className?: string
}

export function PageHeader({
  title,
  description,
  icon,
  actions,
  className,
}: PageHeaderProps) {
  return (
    <div className={cn("flex items-start justify-between gap-4 mb-6", className)}>
      <div className="flex items-start gap-3">
        {icon && (
          <div
            className={cn(
              // Token wiring: read from `@/lib/tone`'s static style map so
              // the literal `bg-[var(--status-info-bg)]` class only appears
              // in `@/lib/tone` (Tailwind v4's auto-scanner picks it up
              // there). The accent stripe composes `--status-info-fg` at
              // 60% alpha — Tailwind v4 supports arbitrary-value + alpha
              // modifier so `…]/60` resolves at runtime.
              'relative flex h-10 w-10 items-center justify-center rounded-xl flex-shrink-0 mt-0.5',
              toneStyleClasses.info.bg,
            )}
          >
            {/* Linear: single chromatic accent — a 2px lavender edge ties the
                chip to the primary without a heavy fill. */}
            <span
              className={cn(
                'absolute left-0 top-1/2 h-5 w-[2px] -translate-y-1/2 rounded-r-full',
                `${toneFillBgClass('info')}/60`,
              )}
            />
            {icon}
          </div>
        )}
        <div className="min-w-0">
          <h1 className="text-lg font-semibold tracking-tight text-foreground">{title}</h1>
          {description && (
            <p className="text-sm text-muted-foreground mt-0.5">{description}</p>
          )}
        </div>
      </div>
      {actions && (
        <div className="flex items-center gap-2 flex-shrink-0">
          {actions}
        </div>
      )}
    </div>
  )
}
