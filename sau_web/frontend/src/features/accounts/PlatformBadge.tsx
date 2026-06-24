import { cn } from '@/lib/utils'
import {
  PlatformIcon,
  PLATFORM_COLORS,
} from '@/components/ui/platform-icon'

interface PlatformBadgeProps {
  /** Platform key used to look up both the brand-color token and the SVG icon. */
  platform: string
  /**
   * Visual size:
   * - `sm`: h-7 w-7 / icon h-4 w-4 (used in the chip-strip of `GroupListItem`)
   * - `md`: h-9 w-9 / icon h-5 w-5 (used in `SortableAuthorizationItem`)
   */
  size?: 'sm' | 'md'
  /**
   * If true, applies a `transform` micro-interaction (hover scale) and a soft
   * shadow. Defaults to false. Preserves the legacy `group-hover/auth:scale-105`
   * behavior on the sortable row variant.
   */
  interactive?: boolean
  /** Native HTML title (e.g. the platform label) for hover affordance. */
  title?: string
  /** Extra utility classes for layout-side concerns (margins, etc). */
  className?: string
}

const SIZE_CLASSES: Record<NonNullable<PlatformBadgeProps['size']>, string> = {
  sm: 'h-7 w-7 rounded-lg',
  md: 'h-9 w-9 rounded-xl shadow-sm',
}

export function PlatformBadge({
  platform,
  size = 'md',
  interactive = false,
  title,
  className,
}: PlatformBadgeProps) {
  const bg = PLATFORM_COLORS[platform] ?? 'bg-muted'

  return (
    <div
      className={cn(
        'flex items-center justify-center text-white',
        bg,
        SIZE_CLASSES[size],
        interactive &&
          'transition-transform duration-200 group-hover/auth:scale-105',
        className,
      )}
      title={title}
    >
      <PlatformIcon
        platform={platform}
        className={size === 'sm' ? 'h-4 w-4' : 'h-5 w-5'}
      />
    </div>
  )
}
