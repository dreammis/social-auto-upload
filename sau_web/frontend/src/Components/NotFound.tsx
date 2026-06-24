import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Compass } from 'lucide-react'
import { cn } from '@/lib/utils'
import { toneBgClass, toneTextClass } from '@/lib/tone'

// Linear DESIGN.md — 404 keeps the same empty-state grammar as the rest of
// the app (centered icon chip in a status-info tint, neutral copy, primary
// CTA) so a bad route doesn't fall back to bare HTML. The status-info
// palette is composed via `@/lib/tone` to share the tonal vocabulary
// with NotFound's siblings ErrorBoundary / Banner / Alert.
export function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-20 text-center">
      <div className={cn('mb-5 flex h-14 w-14 items-center justify-center rounded-2xl', toneBgClass('info'))}>
        <Compass className={cn('h-7 w-7', toneTextClass('info'))} />
      </div>
      <h2 className="text-lg font-semibold tracking-tight text-foreground">
        页面未找到
      </h2>
      <p className="mt-1.5 max-w-xs text-sm text-muted-foreground">
        请检查 URL 是否正确，或返回首页继续操作。
      </p>
      <Button asChild className="mt-6">
        <Link to="/">返回首页</Link>
      </Button>
    </div>
  )
}
