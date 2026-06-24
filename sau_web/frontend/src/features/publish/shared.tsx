import { PLATFORMS } from '../../api/client'
import type { ReactNode } from 'react'

/**
 * Per-platform tag-count limits (XHS caps at 10; most others at 5).
 * Used to cap the TagInput and to surface a contextual hint.
 */
export const PLATFORM_TAG_LIMITS: Record<string, number | undefined> = {
  xiaohongshu: 10,
  bilibili: 5,
  baijiahao: 5,
  douyin: 5,
  kuaishou: 5,
  tencent: 5,
  tiktok: 5,
}

export function effectiveMaxTags(platforms: string[]): number | undefined {
  const limits = platforms
    .map((p) => PLATFORM_TAG_LIMITS[p])
    .filter((l): l is number => l !== undefined)
  if (limits.length === 0) return undefined
  return Math.min(...limits)
}

export function platformTagLabel(platforms: string[]): string {
  const limit = effectiveMaxTags(platforms)
  if (limit === undefined) return '无限制'
  const matched = platforms.find((p) => PLATFORM_TAG_LIMITS[p] === limit)
  const label = matched ? PLATFORMS.find((p) => p.value === matched)?.label || matched : ''
  return label ? `${label}最多 ${limit} 个` : `最多 ${limit} 个`
}

/**
 * Render an icon-equipped section header used inside publishing cards.
 * Keep this here in publish/shared — it's tightly coupled to the publish
 * card layout (border-b / flex gap / rounded-lg background).
 *
 * The badge color is the unified `--primary` token; per-section overrides
 * were removed as part of the `feat(ui): unify brand colors` cleanup so
 * the design vocabulary has exactly one accent.
 */
export function SectionHeader({
  icon,
  title,
}: {
  icon: ReactNode
  title: string
}) {
  return (
    <div className="flex items-center gap-2 mb-4 pb-2 border-b">
      <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10 text-primary">
        {icon}
      </div>
      <span className="text-sm font-semibold">{title}</span>
    </div>
  )
}

/**
 * Used by PublishOverview to compactly render recently submitted task IDs.
 * Long IDs are shortened to the last 10 chars preceded by an ellipsis.
 *
 * Note: this is the publish-specific simple-elide form. The cross-page
 * hyphen-aware compactor is `shortenId` in `@/lib/features`.
 */
export function formatTaskId(value?: string): string {
  if (!value) return '-'
  return value.length > 14 ? `...${value.slice(-10)}` : value
}
