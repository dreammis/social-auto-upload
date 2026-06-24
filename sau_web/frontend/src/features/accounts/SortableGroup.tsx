import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { useSortable } from '@dnd-kit/react/sortable'
import { GripVertical, Pencil, Plus, Shield, Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { pctToTone, toneChipClasses, toneDotStyle, toneFgVar, toneTextClass, validityTone } from '@/lib/tone'
import type { AccountGroup } from '@/api/client'
import { useAccountsDispatch } from './AccountsProvider'
import { SortableAuthorizationList } from './SortableAuthorizationList'

interface SortableGroupProps {
  group: AccountGroup
  index: number
}

function GroupGridEmptyState({ onAuthorize }: { onAuthorize: () => void }) {
  return (
    <div className="text-center py-8 border border-dashed border-muted-foreground/15 rounded-xl bg-muted/10">
      <Shield className="h-10 w-10 mx-auto text-muted-foreground/25 mb-3" />
      <p className="text-sm text-muted-foreground/70 font-medium">暂无平台授权</p>
      <p className="text-xs text-muted-foreground/50 mt-1 mb-3">添加平台以开始使用</p>
      <Button
        variant="ghost"
        size="sm"
        className="btn-dashed mx-auto max-w-[180px]"
        onClick={onAuthorize}
      >
        <Plus className="h-3.5 w-3.5 mr-1.5" />
        添加授权
      </Button>
    </div>
  )
}

function GroupSummaryLine({
  validCount,
  totalCount,
}: {
  validCount: number
  totalCount: number
}) {
  // Drives ONLY the text color (no chip background in the summary line).
  // `validityTone` is the dedicated 2-band mapper (success / warning) used
  // across the accounts surface — `rateToTone` is the 4-band alternative
  // for "validity ratio" displays that benefit from an `info` band (e.g.
  // the homepage tile). This sister component recomputes the tone from
  // its props (idempotent — the parent chip body and this line call the
  // same pure mapper, so the result is identical without prop drilling).
  const text =
    totalCount > 0 ? (
      <>
        <span className={cn('font-medium tabular-nums text-xs', toneTextClass(validityTone(validCount, totalCount)))}>
          {validCount}/{totalCount}
        </span>{' '}
        <span className="text-muted-foreground/60">个平台已授权</span>
      </>
    ) : (
      <span className="text-muted-foreground/50">暂无授权</span>
    )

  return <p className="text-xs mt-0.5">{text}</p>
}

function TokenHealthBar({
  validCount,
  totalCount,
}: {
  validCount: number
  totalCount: number
}) {
  if (totalCount === 0) return null
  const pct = Math.round((validCount / totalCount) * 100)
  const tone = pctToTone(pct)

  return (
    <div className="token-indicator mt-2">
      <div
        className="token-indicator-bar"
        style={{
          width: `${pct}%`,
          background: toneFgVar(tone),
        }}
      />
    </div>
  )
}

function GroupDeleteDialog({
  name,
  authCount,
  onConfirm,
}: {
  name: string
  authCount: number
  onConfirm: () => void
}) {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 text-muted-foreground/60 hover:text-destructive hover:bg-destructive/10"
          aria-label="Delete group"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>确认删除</AlertDialogTitle>
          <AlertDialogDescription>
            {'删除分组 "'}
            {name}
            {'" 将同时清空其 '}
            <span className="font-medium text-foreground">{authCount}</span>
            {' 项平台授权，确认继续？'}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>取消</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm}>删除</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}

export function SortableGroup({ group, index }: SortableGroupProps) {
  const dispatch = useAccountsDispatch()
  const { ref, handleRef, isDragging } = useSortable({
    id: `group:${group.id}`,
    index,
  })

  const validCount = group.authorizations.filter((a) => a.valid).length
  const totalCount = group.authorizations.length
  // Hoist the chip tone to component scope so the chip body (`toneChipClasses`)
  // and inner dot (`toneDotStyle`) helpers share a single mapper call — both
  // helpers absorb `Tone | null | undefined` gracefully so the JSX-level
  // `{totalCount > 0 && <chip>}` guard is the only shape-relevant check.
  const chipTone = validityTone(validCount, totalCount)

  return (
    <Card
      ref={ref}
      className={cn(
        'card-refined group/card relative overflow-hidden',
        isDragging && 'opacity-50 scale-[1.02] z-50',
      )}
    >
      <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.03] to-transparent opacity-0 group-hover/card:opacity-100 transition-opacity duration-500 pointer-events-none" />

      <CardHeader className="pb-3 relative">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div
              ref={handleRef}
              className={cn(
                'cursor-grab active:cursor-grabbing p-1 rounded-md transition-colors',
                'text-muted-foreground/30 hover:text-muted-foreground hover:bg-muted/50',
                'group-hover/card:text-muted-foreground/60',
              )}
            >
              <GripVertical className="h-4 w-4" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <h3 className="text-[0.9375rem] font-semibold text-foreground/90 leading-tight truncate">
                  {group.name}
                </h3>                    {totalCount > 0 && (
                      <span
                        className={cn(
                          'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium tabular-nums',
                          // Shared "chip + dot" shape with GroupListItem.GroupValidityChip
                          // — `validityTone(validCount, totalCount)` is the dedicated
                          // 2-band mapper (success=all-valid, warning=partial).
                          toneChipClasses(chipTone),
                        )}
                      >
                        {/* Inner dot now flows through `@/lib/tone` —
                            `toneDotStyle(chipTone)` returns the canonical
                            `--status-{tone}-fg` background + 40% halo
                            (replaces the deleted `.status-dot-{valid,invalid}`
                            CSS rules). */}
                        <span className="status-dot" style={toneDotStyle(chipTone)} />
                        {validCount}/{totalCount}
                      </span>
                    )}
              </div>
              <GroupSummaryLine validCount={validCount} totalCount={totalCount} />
              <TokenHealthBar validCount={validCount} totalCount={totalCount} />
            </div>
          </div>

          <div className="flex items-center gap-0.5 opacity-100 md:opacity-0 md:group-hover/card:opacity-100 transition-opacity duration-200">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-muted-foreground/60 hover:text-primary hover:bg-primary/10"
              onClick={() => dispatch.handleStartRename(group.id, group.name)}
              aria-label="Rename group"
            >
              <Pencil className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-muted-foreground/60 hover:text-primary hover:bg-primary/10"
              onClick={() => dispatch.handleStartAuthorize(group.id)}
              aria-label="Add authorization"
              data-tour="add-auth"
            >
              <Plus className="h-3.5 w-3.5" />
            </Button>
            <GroupDeleteDialog
              name={group.name}
              authCount={group.authorizations.length}
              onConfirm={() => void dispatch.handleDeleteGroup(group.id, group.name)}
            />
          </div>
        </div>
      </CardHeader>

      <CardContent className="relative">
        {group.authorizations.length === 0 ? (
          <GroupGridEmptyState
            onAuthorize={() => dispatch.handleStartAuthorize(group.id)}
          />
        ) : (
          <SortableAuthorizationList
            groupId={group.id}
            authorizations={group.authorizations}
          />
        )}
      </CardContent>

      {totalCount > 0 && (
        <div className="px-5 pb-4 relative">
          <button
            type="button"
            className="btn-dashed"
            onClick={() => dispatch.handleStartAuthorize(group.id)}
          >
            <Plus className="h-3.5 w-3.5 mr-1.5" />
            添加更多平台
          </button>
        </div>
      )}
    </Card>
  )
}
