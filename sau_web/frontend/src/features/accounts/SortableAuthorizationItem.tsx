import { memo } from 'react'
import { useSortable } from '@dnd-kit/react/sortable'
import { GripVertical, MoreHorizontal, Unlink } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { PlatformBadge } from './PlatformBadge'
import type { AccountAuthorization } from '@/api/client'
import { useAccountsDispatch } from './AccountsProvider'
import { toneChipClasses, toneFillBgClass, type Tone } from '@/lib/tone'

interface SortableAuthorizationItemProps {
  auth: AccountAuthorization
  index: number
  groupId: number
}

function AuthorizationStatusPill({ valid }: { valid: boolean }) {
  // Drive the chip's tone from the `valid` flag. Valid → success (mint),
  // Invalid → warning (amber) so the row reads as "needs attention"
  // rather than "broken" (kept amber to preserve the prior visual signal
  // — expiry isn't necessarily a fatal failure).
  const tone: Tone = valid ? 'success' : 'warning'
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium whitespace-nowrap',
        toneChipClasses(tone),
      )}
    >
      <span className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0', toneFillBgClass(tone))} />
      {valid ? '有效' : '失效'}
    </span>
  )
}

function SortableAuthorizationItemImpl({
  auth,
  index,
  groupId,
}: SortableAuthorizationItemProps) {
  const dispatch = useAccountsDispatch()
  const { ref, isDragging } = useSortable({
    id: `auth:${groupId}:${auth.id}`,
    index,
  })

  const platformLabel = dispatch.getPlatformLabel(auth.platform)

  return (
    <div
      ref={ref}
      className={cn(
        'auth-row group/auth',
        isDragging && 'opacity-50 shadow-lg scale-[1.01] z-10',
      )}
    >
      <div className="flex items-center gap-2.5 min-w-0 flex-1">
        <div
          className={cn(
            'cursor-grab active:cursor-grabbing p-0.5 rounded transition-colors flex-shrink-0',
            'text-muted-foreground/25 hover:text-muted-foreground/60',
          )}
        >
          <GripVertical className="h-3 w-3" />
        </div>
        <PlatformBadge
          platform={auth.platform}
          size="md"
          interactive
          title={platformLabel}
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium truncate">
              {platformLabel}
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground/50 truncate mt-0.5 font-mono">
            {auth.platform}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2 flex-shrink-0">
        <AuthorizationStatusPill valid={auth.valid} />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-muted-foreground/40 hover:text-foreground hover:bg-muted/50 opacity-100 md:opacity-0 md:group-hover/auth:opacity-100 transition-all"
              aria-label="More actions"
            >
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-36">
            <DropdownMenuItem
              className="text-destructive focus:text-destructive cursor-pointer"
              onClick={() => void dispatch.handleRemoveAuth(groupId, auth.platform)}
            >
              <Unlink className="h-3.5 w-3.5 mr-2" />
              断开连接
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  )
}

export const SortableAuthorizationItem = memo(SortableAuthorizationItemImpl)
