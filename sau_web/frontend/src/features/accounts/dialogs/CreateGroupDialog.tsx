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
 * Create-group modal. Owns a small piece of UI-local state (`touched`) so
 * the validation hint doesn't pop on first render.
 */
export function CreateGroupDialog() {
  const state = useAccountsState()
  const dispatch = useAccountsDispatch()

  const [touched, setTouched] = useState(false)
  useEffect(() => {
    if (state.createDialogOpen) setTouched(false)
  }, [state.createDialogOpen])

  const validation = validateGroupName(state.newGroupName)
  const showHint = touched && !validation.ok

  const attemptSubmit = () => {
    setTouched(true)
    void dispatch.handleCreateGroup()
  }

  return (
    <Dialog open={state.createDialogOpen} onOpenChange={dispatch.setCreateDialogOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>新建账号分组</DialogTitle>
          <DialogDescription>
            创建一个分组来管理多个平台的授权
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="create-name-input">分组名称</Label>
            <Input
              id="create-name-input"
              placeholder="例如：工作号、个人号、主账号"
              value={state.newGroupName}
              onChange={(e) => dispatch.setNewGroupName(e.target.value)}
              onBlur={() => setTouched(true)}
              aria-invalid={showHint}
              aria-describedby={showHint ? 'create-name-hint' : undefined}
              onKeyDown={(e) => {
                if (e.key === 'Enter') attemptSubmit()
              }}
            />
            {showHint && (
              // Inline validation hint — same Tone vocabulary as
              // GroupRenameDialog: error foreground, kept at `text-xs`.
              <p
                id="create-name-hint"
                className={cn('text-xs', toneTextClass('error'))}
              >
                {validation.message}
              </p>
            )}
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => dispatch.setCreateDialogOpen(false)}
          >
            取消
          </Button>
          <Button
            onClick={attemptSubmit}
            disabled={state.isCreatePending}
          >
            {state.isCreatePending && (
              <Loader2 className="h-4 w-4 mr-1 animate-spin" />
            )}
            创建
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
