import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { PLATFORMS } from '@/api/client'
import { useAccountsDispatch, useAccountsState } from '../AccountsProvider'

/**
 * Add-platform-to-group modal. Validates selection, then delegates the
 * actual login flow to the LoginProgressModal.
 */
export function AuthorizeDialog() {
  const state = useAccountsState()
  const dispatch = useAccountsDispatch()

  return (
    <Dialog
      open={state.authorizeDialogOpen}
      onOpenChange={dispatch.setAuthorizeDialogOpen}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>添加平台授权</DialogTitle>
          <DialogDescription>选择要授权的平台，然后扫码登录</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>选择平台</Label>
            <Select
              value={state.selectedPlatform}
              onValueChange={dispatch.setSelectedPlatform}
            >
              <SelectTrigger>
                <SelectValue placeholder="选择平台" />
              </SelectTrigger>
              <SelectContent>
                {PLATFORMS.map((p) => (
                  <SelectItem key={p.value} value={p.value}>
                    {p.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => dispatch.setAuthorizeDialogOpen(false)}
          >
            取消
          </Button>
          <Button onClick={dispatch.handleAuthorize} disabled={!state.selectedPlatform}>
            开始授权
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
