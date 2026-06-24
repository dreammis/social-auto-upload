import { useMemo } from 'react'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { cn } from '@/lib/utils'
import { useAccountsDispatch, useAccountsState } from '../AccountsProvider'

const MAX_NAMES_SHOWN = 3

/**
 * Confirmation dialog for batch-deleting selected account groups. Hits
 * `dispatch.handleBatchDelete` which fans out via Promise.allSettled in
 * the provider and toastifies per-outcome.
 *
 * P1-7: show up to MAX_NAMES_SHOWN group names with overflow tail, total
 * authorization count, and Cmd/Ctrl+Enter to confirm.
 */
export function BatchDeleteDialog() {
  const state = useAccountsState()
  const dispatch = useAccountsDispatch()

  /* Resolve selected IDs into a stable slice of group metadata. Computing
   * inline would re-derive on every external re-render (e.g. role UI updates
   * after a selectedId changes), so memoize against the actual inputs. */
  const { previewNames, hiddenCount, totalAuthCount } = useMemo(() => {
    if (state.selectedIds.size === 0) {
      return { previewNames: [], hiddenCount: 0, totalAuthCount: 0 }
    }
    const selected = Array.from(state.selectedIds)
    const matched = selected
      .map((id) => state.groups.find((g) => g.id === id))
      .filter((g): g is NonNullable<typeof g> => Boolean(g))
    const names = matched.map((g) => g.name)
    const authCount = matched.reduce((s, g) => s + g.authorizations.length, 0)
    return {
      previewNames: names.slice(0, MAX_NAMES_SHOWN),
      hiddenCount: Math.max(0, names.length - MAX_NAMES_SHOWN),
      totalAuthCount: authCount,
    }
  }, [state.selectedIds, state.groups])

  /* Cmd/Ctrl+Enter confirms without lifting hands off the keyboard. We
   * attach to the dialog content (shadcn/Radix renders on the wrapping
   * div) so the handler is scoped to the open dialog lifetime — no
   * global listener cleanup.
   * `e.repeat` guard prevents a held key from re-firing into the closed
   * dialog (Radix unmounts on confirm, and stray repeats would toast on
   * stale selectedIds after the modal is gone). */
  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter' && !e.repeat) {
      e.preventDefault()
      void dispatch.handleBatchDelete()
    }
  }

  const selectedCount = state.selectedIds.size

  return (
    <AlertDialog
      open={state.batchDeleteOpen}
      onOpenChange={dispatch.setBatchDeleteOpen}
    >
      <AlertDialogContent onKeyDown={handleKeyDown}>
        <AlertDialogHeader>
          <AlertDialogTitle>确认批量删除</AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="space-y-2 text-sm text-muted-foreground">
              <p>
                将删除以下 <span className="font-medium text-foreground">{selectedCount}</span> 个分组，
                并同时清空{' '}
                {totalAuthCount > 0 ? (
                  <>
                    <span className="font-medium text-foreground">{totalAuthCount}</span> 项平台授权
                  </>
                ) : (
                  <span className="text-foreground/80">所有关联平台授权（暂无）</span>
                )}。
              </p>
              {previewNames.length > 0 && (
                <ul className="text-[12px] space-y-0.5 pl-1">
                  {previewNames.map((name) => (
                    <li key={name} className={cn('truncate text-foreground/80')}>
                      · {name}
                    </li>
                  ))}
                  {hiddenCount > 0 && (
                    <li className="text-muted-foreground/60">…其它 {hiddenCount} 个</li>
                  )}
                </ul>
              )}
              <p className="text-[11px] text-muted-foreground/60 pt-1">
                提示：按 <kbd className="kbd-hint mr-1">⌘</kbd>
                <kbd className="kbd-hint">Enter</kbd> 直接确认
              </p>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>取消</AlertDialogCancel>
          <AlertDialogAction
            onClick={() => void dispatch.handleBatchDelete()}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            删除 {selectedCount} 个分组
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
