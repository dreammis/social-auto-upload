import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import type { AccountGroup } from '@/api/client'
import { CheckSquare, Pencil, Plus, Square, Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAccountsDispatch } from './AccountsProvider'
import { PlatformBadge } from './PlatformBadge'
import { toneChipClasses, toneFillBgClass, validityTone } from '@/lib/tone'

interface GroupListItemProps {
  group: AccountGroup
  selected: boolean
}

function GroupValidityChip({
  validCount,
  totalCount,
}: {
  validCount: number
  totalCount: number
}) {
  // Drive the chip's tone from the validity ratio via the dedicated 2-band
  // `validityTone` mapper (success=all-valid, warning=partial). Same
  // vocabulary as SortableGroup's inline chip and the homepage's
  // `AuthorizationStatusPill` (which uses boolean, not counts).
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium tabular-nums',
        toneChipClasses(validityTone(validCount, totalCount)),
      )}
    >
      <span className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0', toneFillBgClass(validityTone(validCount, totalCount)))} />
      {validCount}/{totalCount}
    </span>
  )
}

export function GroupListItem({ group, selected }: GroupListItemProps) {
  const dispatch = useAccountsDispatch()
  const validCount = group.authorizations.filter((a) => a.valid).length
  const totalCount = group.authorizations.length

  return (
    <div
      className={cn(
        'flex items-center gap-4 p-4 rounded-xl border transition-all duration-200',
        'hover:bg-muted/20 hover:border-primary/15',
        selected && 'bg-primary/5 border-primary/25',
        !selected && 'border-border/50',
      )}
    >
      <button
        type="button"
        onClick={() => dispatch.handleSelectGroup(group.id, !selected)}
        className="flex-shrink-0"
        aria-label={selected ? 'Deselect group' : 'Select group'}
      >
        {selected ? (
          <CheckSquare className="h-5 w-5 text-primary" />
        ) : (
          <Square className="h-5 w-5 text-muted-foreground/30 hover:text-muted-foreground/60" />
        )}
      </button>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-[0.9375rem] truncate">{group.name}</span>
          {totalCount > 0 && (
            <GroupValidityChip validCount={validCount} totalCount={totalCount} />
          )}
        </div>
        <p className="text-xs text-muted-foreground/50 mt-0.5">
          创建于 {new Date(group.created).toLocaleDateString('zh-CN')}
        </p>
      </div>

      <div className="flex items-center gap-1.5">
        {group.authorizations.slice(0, 5).map((auth) => (
          <PlatformBadge
            key={auth.id}
            platform={auth.platform}
            size="sm"
            title={dispatch.getPlatformLabel(auth.platform)}
          />
        ))}
        {group.authorizations.length > 5 && (
          <span className="text-xs text-muted-foreground/50 ml-1">
            +{group.authorizations.length - 5}
          </span>
        )}
      </div>

      <div className="flex items-center gap-0.5 opacity-100 md:opacity-0 md:hover:opacity-100 transition-opacity">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-muted-foreground/60 hover:text-primary hover:bg-primary/10"
          onClick={() => dispatch.handleStartRename(group.id, group.name)}
          aria-label="Rename group"
        >
          <Pencil className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-muted-foreground/60 hover:text-primary hover:bg-primary/10"
          onClick={() => dispatch.handleStartAuthorize(group.id)}
          aria-label="Add authorization"
        >
          <Plus className="h-3.5 w-3.5" />
        </Button>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-muted-foreground/60 hover:text-destructive hover:bg-destructive/10"
              aria-label="Delete group"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>确认删除</AlertDialogTitle>
              <AlertDialogDescription>
                删除分组 "{group.name}" 将同时删除所有平台授权，确认继续？
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>取消</AlertDialogCancel>
              <AlertDialogAction
                onClick={() => void dispatch.handleDeleteGroup(group.id, group.name)}
              >
                删除
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  )
}
