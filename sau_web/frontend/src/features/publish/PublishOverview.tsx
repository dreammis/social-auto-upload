import { memo } from 'react'
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Separator,
} from '@/components/ui/index'
import { Flag, RefreshCw } from 'lucide-react'
import { PLATFORMS, type AccountItem } from '../../api/client'
import { formatTaskId } from './shared'
import { cn } from '@/lib/utils'
import { toneTextClass } from '@/lib/tone'

type PublishOverviewProps = {
  accountOptions: AccountItem[]
  lastTaskIds: string[]
  onRefresh: () => void
}

/**
 * Right-column summary card. Stays mounted across mode toggles so memo is
 * meaningful: parent re-renders on mode change shouldn't repaint this when
 * props haven't changed.
 */
export const PublishOverview = memo(function PublishOverview({
  accountOptions,
  lastTaskIds,
  onRefresh,
}: PublishOverviewProps) {
  return (
    <Card className="sticky top-6">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {/* Flag accent uses --status-warning-fg via `@/lib/tone` so the
              header line preview matches the Tone vocabulary shared with
              the warning-fill callouts/dots elsewhere. */}
          <Flag className={cn('h-5 w-5', toneTextClass('warning'))} />
          <span>发布概览</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">可用账号</span>
          <span className="text-sm font-bold text-primary">{accountOptions.length}</span>
        </div>
        <Separator />
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">支持平台</span>
          <span className="text-sm font-bold">{PLATFORMS.length}</span>
        </div>
        <Separator />
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">最近提交</span>
          <span className="text-sm font-bold">
            {lastTaskIds.length > 0 ? `${lastTaskIds.length} 个` : '暂无'}
          </span>
        </div>
        <Separator />
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">最新任务 ID</p>
          {lastTaskIds.length === 0 ? (
            <p className="text-xs text-muted-foreground">暂无提交记录</p>
          ) : (
            <div className="flex flex-wrap gap-1">
              {lastTaskIds.map((id) => (
                <Badge key={id} variant="secondary" className="text-xs">
                  {formatTaskId(id)}
                </Badge>
              ))}
            </div>
          )}
        </div>
        <Separator />
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground">
            后端地址：<code className="bg-muted px-1 rounded">http://localhost:6001</code>
          </p>
          <p className="text-xs text-muted-foreground">
            接口：<code className="bg-muted px-1 rounded">/api/upload/*</code>
          </p>
        </div>
        <Button variant="outline" size="sm" className="w-full" onClick={onRefresh}>
          <RefreshCw className="h-4 w-4 mr-1" />
          刷新
        </Button>
      </CardContent>
    </Card>
  )
})
