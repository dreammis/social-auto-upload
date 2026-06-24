import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Loader2 } from 'lucide-react'
import { useAccountsDispatch, useAccountsState, validateGroupName } from '../AccountsProvider'
import { cn } from '@/lib/utils'
import { toneTextClass } from '@/lib/tone'

/**
 * Rename-group modal. Local `newName` state intentionally lived here so
 * that typing in the rename field doesn't re-render the entire accounts
 * page on every keystroke. We resync from `currentName` whenever the
 * dialog is reopened (or the source-of-truth name changes).
 */
export function GroupRenameDialog() {
  const state = useAccountsState()
  const dispatch = useAccountsDispatch()

  const [newName, setNewName] = useState(state.renameDialogCurrentName)
  useEffect(() => {
    if (state.renameDialogOpen) setNewName(state.renameDialogCurrentName)
  }, [state.renameDialogOpen, state.renameDialogCurrentName])

  const validation = validateGroupName(newName)
  const canConfirm =
    validation.ok &&
    validation.cleaned !== state.renameDialogCurrentName &&
    !state.isRenamePending

  return (
    <Dialog open={state.renameDialogOpen} onOpenChange={dispatch.setRenameDialogOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>重命名分组</DialogTitle>
          <DialogDescription>
            原名称：{state.renameDialogCurrentName}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label>新名称</Label>
          <Input
            placeholder="例如：主账号、工作号"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && canConfirm)
                void dispatch.handleRename(state.renameDialogGroupId ?? -1, newName)
            }}
            autoFocus
          />
          {!validation.ok && newName.length > 0 && (
            // Inline validation hint — routed through `@/lib/tone` so the
            // error text color matches the rest of the form-validation
            // surface (CreateGroupDialog, TagInput at-limit state).
            <p className={cn('text-xs', toneTextClass('error'))}>{validation.message}</p>
          )}
          {validation.ok && validation.cleaned === state.renameDialogCurrentName && (
            <p className="text-xs text-muted-foreground">新名称与当前名称一致</p>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => dispatch.setRenameDialogOpen(false)}>
            取消
          </Button>
          <Button
            disabled={!canConfirm}
            onClick={() =>
              void dispatch.handleRename(state.renameDialogGroupId ?? -1, newName)
            }
          >
            {state.isRenamePending && (
              <Loader2 className="h-4 w-4 mr-1 animate-spin" />
            )}
            确认重命名
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
