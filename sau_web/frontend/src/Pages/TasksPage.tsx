import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/alert-dialog'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { Separator } from '@/components/ui/separator'
import { EmptyState } from '@/components/ui/empty-state'
import { PageHeader } from '@/components/ui/page-header'
import { PLATFORMS, api, type TaskItem } from '../api/client'
import { useTasks, useTaskLogs } from '../hooks/useTasks'
import { useQueryClient } from '@tanstack/react-query'
import { useToast } from '@/components/ui/toast'
import {
  Trash2,
  FileText,
  Loader2,
  Plus,
  RefreshCw,
  RotateCcw,
  BarChart3,
} from 'lucide-react'

type StatusType = 'all' | 'pending' | 'running' | 'success' | 'failed' | 'error'

const STATUS_OPTIONS: { label: string; value: StatusType }[] = [
  { label: '全部', value: 'all' },
  { label: '等待中', value: 'pending' },
  { label: '执行中', value: 'running' },
  { label: '成功', value: 'success' },
  { label: '失败', value: 'failed' },
  { label: '异常', value: 'error' },
]

const STATUS_META: Record<string, { className: string; label: string }> = {
  pending: { className: 'bg-muted text-muted-foreground', label: '等待中' },
  running: { className: 'bg-blue-500/15 text-blue-700 dark:text-blue-400', label: '执行中' },
  success: { className: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400', label: '成功' },
  failed: { className: 'bg-red-500/15 text-red-700 dark:text-red-400', label: '失败' },
  error: { className: 'bg-red-500/15 text-red-700 dark:text-red-400', label: '异常' },
}

function formatDateTime(value?: string) {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('zh-CN', { hour12: false })
}

function shortenId(value?: string) {
  if (!value) return '-'
  if (value.length <= 16) return value
  const lastDash = value.lastIndexOf('-')
  if (lastDash > 0) {
    const prefix = value.slice(0, lastDash)
    const suffix = value.slice(lastDash + 1)
    const short = `${prefix}-${suffix.slice(-6)}`
    return short.length <= 24 ? short : `${prefix.slice(0, 10)}-${suffix.slice(-6)}`
  }
  return `${value.slice(0, 8)}...${value.slice(-6)}`
}

function TaskDrawerContent({ task }: { task: TaskItem }) {
  const { data: taskLogs = [], isLoading: logsLoading } = useTaskLogs(task.task_id, task.status)
  const statusMeta = STATUS_META[task.status ?? 'pending'] ?? STATUS_META.pending
  const logsEndRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [taskLogs])

  return (
    <div className="space-y-4">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">任务 ID</span>
          <code className="text-xs bg-muted px-2 py-1 rounded max-w-[300px] truncate" title={task.task_id}>
            {task.task_id}
          </code>
        </div>
        <Separator />
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">平台</span>
          <span className="text-sm font-medium">{task.platform || '-'}</span>
        </div>
        <Separator />
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">动作</span>
          <span className="text-sm font-medium">{task.action || '-'}</span>
        </div>
        <Separator />
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">账号</span>
          <span className="text-sm font-medium">{task.account || '-'}</span>
        </div>
        <Separator />
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">状态</span>
          <Badge className={statusMeta.className}>{statusMeta.label}</Badge>
        </div>
        <Separator />
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">创建时间</span>
          <span className="text-sm">{formatDateTime(task.created)}</span>
        </div>
        <Separator />
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">退出码</span>
          {task.code !== undefined && task.code !== null ? (
            <Badge className={task.code === 0 ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400' : 'bg-red-500/15 text-red-700 dark:text-red-400'}>
              {task.code}
            </Badge>
          ) : (
            <span className="text-sm">-</span>
          )}
        </div>
        {task.error && (
          <>
            <Separator />
            <div className="space-y-2">
              <span className="text-sm text-muted-foreground">错误信息</span>
              <pre className="text-xs bg-muted p-2 rounded-lg overflow-auto max-h-[200px] whitespace-pre-wrap">
                {task.error}
              </pre>
            </div>
          </>
        )}
        {task.result && (() => {
          let resultData: Record<string, string>
          try { resultData = JSON.parse(task.result) } catch { return null }
          const entries = Object.entries(resultData).filter(([, v]) => v !== undefined && v !== null && v !== '')
          if (entries.length === 0) return null
          return entries.map(([key, value]) => {
            let label = key
            if (key === 'video_url') label = '视频链接'
            else if (key === 'publish_status') label = '发布状态'
            else if (key === 'verified') label = '发布验证'
            return (
              <div key={key}>
                <Separator className="my-2" />
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">{label}</span>
                  {key === 'verified' ? (
                    <Badge className={value === 'true' ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400' : 'bg-amber-500/15 text-amber-700 dark:text-amber-400'}>
                      {value === 'true' ? '已验证' : '未验证'}
                    </Badge>
                  ) : key === 'video_url' && value ? (
                    <a href={value} target="_blank" rel="noreferrer" className="text-sm text-primary hover:underline max-w-[200px] truncate block">
                      {value}
                    </a>
                  ) : (
                    <span className="text-sm max-w-[200px] truncate">{String(value)}</span>
                  )}
                </div>
              </div>
            )
          })
        })()}
        {task.argv && (
          <>
            <Separator />
            <div className="space-y-2">
              <span className="text-sm text-muted-foreground">执行命令</span>
              <pre className="text-xs bg-muted p-2 rounded-lg overflow-auto max-h-[300px] whitespace-pre-wrap">
                {(() => {
                  try {
                    return JSON.parse(task.argv).join(' ')
                  } catch {
                    return task.argv
                  }
                })()}
              </pre>
            </div>
          </>
        )}
      </div>

      <Accordion type="single" collapsible>
        <AccordionItem value="logs">
          <AccordionTrigger>
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              <span className="font-medium">运行日志</span>
              <Badge variant="secondary">{taskLogs.length} 条</Badge>
              {(task.status === 'pending' || task.status === 'running') && (
                <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
              )}
            </div>
          </AccordionTrigger>
          <AccordionContent>
            <div className="rounded-lg bg-zinc-950 p-3 font-mono text-xs leading-relaxed max-h-[400px] overflow-auto">
              {logsLoading ? (
                <p className="text-zinc-500">加载中...</p>
              ) : taskLogs.length === 0 ? (
                <p className="text-zinc-500">暂无日志</p>
              ) : (
                <>
                  {taskLogs.map((entry, idx) => (
                    <div key={idx} className="mb-0.5">
                      <span className="mr-2 text-emerald-500">{entry.ts}</span>
                      <span className="text-zinc-300">{entry.message}</span>
                    </div>
                  ))}
                  <div ref={logsEndRef} />
                </>
              )}
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>
  )
}

function TasksPage() {
  const qc = useQueryClient()
  const { addToast } = useToast()
  const [keyword, setKeyword] = useState('')
  const [status, setStatus] = useState<StatusType>('all')
  const [drawerTask, setDrawerTask] = useState<TaskItem | null>(null)
  const [retrying, setRetrying] = useState<string | null>(null)
  const [manualRefreshing, setManualRefreshing] = useState(false)
  const [addModalOpen, setAddModalOpen] = useState(false)
  const [addPlatform, setAddPlatform] = useState('')
  const [addAction, setAddAction] = useState('')
  const [addAccount, setAddAccount] = useState('')
  const [addTitle, setAddTitle] = useState('')

  const { data: tasks = [], isLoading, refetch } = useTasks()

  const filteredData = useMemo(() => {
    const kw = keyword.trim().toLowerCase()
    return tasks
      .filter((item) => {
        if (status !== 'all' && (item.status ?? '') !== status) return false
        if (!kw) return true
        return (
          (item.task_id ?? '').toLowerCase().includes(kw) ||
          (item.platform ?? '').toLowerCase().includes(kw) ||
          (item.action ?? '').toLowerCase().includes(kw) ||
          (item.account ?? '').toLowerCase().includes(kw)
        )
      })
      .sort((a, b) => (b.created ?? '').localeCompare(a.created ?? ''))
  }, [tasks, keyword, status])

  const counts = useMemo(() => {
    const map: Record<string, number> = { all: 0 }
    tasks.forEach((item) => {
      map.all += 1
      map[item.status ?? 'pending'] = (map[item.status ?? 'pending'] || 0) + 1
    })
    return map
  }, [tasks])

  const handleRetry = useCallback(async (record: TaskItem) => {
    setRetrying(record.task_id)
    try {
      const res = await api.retryTask(record.task_id)
      if (res.success && res.data?.task_id) {
        addToast(`已创建重试任务：${shortenId(res.data.task_id)}`, 'success')
        qc.invalidateQueries({ queryKey: ['tasks'] })
      } else {
        addToast(res.message ?? '重试失败', 'error')
      }
    } catch {
      addToast('重试请求失败，请检查后端连接', 'error')
    } finally {
      setRetrying(null)
    }
  }, [qc, addToast])

  const handleDelete = useCallback(async (taskId: string) => {
    try {
      const res = await api.deleteTask(taskId)
      if (res.success) {
        addToast('任务已删除', 'success')
        qc.invalidateQueries({ queryKey: ['tasks'] })
      } else {
        addToast(res.message ?? '删除失败', 'error')
      }
    } catch {
      addToast('删除请求失败', 'error')
    }
  }, [qc, addToast])

  const handleClear = useCallback(async () => {
    try {
      const res = await api.clearTasks(['success', 'failed', 'error'])
      if (res.success && res.data) {
        addToast(`已清理 ${res.data.deleted} 个任务`, 'success')
        qc.invalidateQueries({ queryKey: ['tasks'] })
      } else {
        addToast('清理失败', 'error')
      }
    } catch {
      addToast('清理请求失败', 'error')
    }
  }, [qc, addToast])

  const handleAddTask = useCallback(async () => {
    if (!addPlatform || !addAction || !addAccount) {
      addToast('请填写必填字段', 'warning')
      return
    }
    try {
      const res = await api.addTask({
        platform: addPlatform,
        action: addAction,
        account: addAccount,
        title: addTitle || undefined,
      })
      if (res.success && res.data) {
        addToast(`任务已创建：${shortenId(res.data.task_id)}`, 'success')
        setAddModalOpen(false)
        setAddPlatform('')
        setAddAction('')
        setAddAccount('')
        setAddTitle('')
        qc.invalidateQueries({ queryKey: ['tasks'] })
      } else {
        addToast(res.message || '创建失败', 'error')
      }
    } catch {
      addToast('创建请求失败', 'error')
    }
  }, [addPlatform, addAction, addAccount, addTitle, qc, addToast])

  const canDelete = (status?: string) => status === 'success' || status === 'failed' || status === 'error'
  const canRetry = (status?: string) => status === 'failed' || status === 'error'

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="任务列表"
        description="查看和管理所有上传任务"
        icon={<BarChart3 className="h-5 w-5 text-muted-foreground" />}
        actions={
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="text-xs">
              <Loader2 className="h-3 w-3 mr-1 animate-spin" />
              轮询中
            </Badge>
            <Button variant="outline" size="sm" onClick={() => setAddModalOpen(true)}>
              <Plus className="h-4 w-4 mr-1" />
              新建任务
            </Button>
          </div>
        }
      />

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card className="card-refined">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">全部任务</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{counts.all}</div>
          </CardContent>
        </Card>
        <Card className="card-refined">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">执行中</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <div className="text-2xl font-bold text-blue-600">{counts.running ?? 0}</div>
              {(counts.running ?? 0) > 0 && (
                <div className="relative h-2 w-2">
                  <div className="absolute inset-0 rounded-full bg-blue-500 animate-pulse" />
                </div>
              )}
            </div>
          </CardContent>
        </Card>
        <Card className="card-refined">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">成功</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-600">{counts.success ?? 0}</div>
          </CardContent>
        </Card>
        <Card className="card-refined">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">失败 / 异常</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{(counts.failed ?? 0) + (counts.error ?? 0)}</div>
          </CardContent>
        </Card>
      </div>

      <Card className="card-refined">
        <CardContent className="pt-6">
          <div className="flex flex-wrap items-center gap-4 mb-4">
            <div className="flex-1 min-w-[200px]">
              <Input
                placeholder="搜索任务 ID、平台、账号"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
              />
            </div>
            <Select value={status} onValueChange={(v) => setStatus(v as StatusType)}>
              <SelectTrigger className="w-[120px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map((item) => (
                  <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <div className="flex items-center gap-2">
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="outline">
                    <Trash2 className="h-4 w-4 mr-1" />
                    清理
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>确认清理</AlertDialogTitle>
                    <AlertDialogDescription>
                      清理所有已完成、失败、异常的任务？
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>取消</AlertDialogCancel>
                    <AlertDialogAction onClick={handleClear}>清理</AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
              <Button onClick={() => setAddModalOpen(true)}>
                <Plus className="h-4 w-4 mr-1" />
                新建任务
              </Button>
              <Button
                variant="outline"
                onClick={async () => {
                  setManualRefreshing(true)
                  await refetch()
                  setManualRefreshing(false)
                }}
              >
                {manualRefreshing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              </Button>
              <Badge variant="secondary" className="text-xs">
                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                轮询中
              </Badge>
            </div>
          </div>

          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[220px]">任务 ID</TableHead>
                  <TableHead className="w-[110px]">平台</TableHead>
                  <TableHead className="w-[140px]">动作</TableHead>
                  <TableHead className="w-[140px]">账号</TableHead>
                  <TableHead className="w-[110px]">状态</TableHead>
                  <TableHead className="w-[180px]">创建时间</TableHead>
                  <TableHead className="w-[240px]">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <TableRow key={i}>
                      {Array.from({ length: 7 }).map((_, j) => (
                        <TableCell key={j}>
                          <div className="h-4 bg-muted animate-pulse rounded" />
                        </TableCell>
                      ))}
                    </TableRow>
                  ))
                ) : filteredData.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7}>
                      <EmptyState
                        icon={<BarChart3 className="h-6 w-6" />}
                        title="暂无任务"
                        description="创建任务后会在这里显示"
                        action={
                          <Button size="sm" onClick={() => setAddModalOpen(true)}>
                            <Plus className="h-4 w-4 mr-1" />
                            新建任务
                          </Button>
                        }
                      />
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredData.map((record) => {
                    const meta = STATUS_META[record.status ?? 'pending'] ?? STATUS_META.pending
                    return (
                      <TableRow
                        key={record.task_id}
                        className="cursor-pointer table-row-refined"
                        onClick={() => setDrawerTask(record)}
                      >
                        <TableCell>
                          <Tooltip>
                            <TooltipTrigger>
                              <code className="text-xs bg-muted px-2 py-1 rounded">
                                {shortenId(record.task_id)}
                              </code>
                            </TooltipTrigger>
                            <TooltipContent>{record.task_id}</TooltipContent>
                          </Tooltip>
                        </TableCell>
                        <TableCell>{record.platform || '-'}</TableCell>
                        <TableCell>{record.action || '-'}</TableCell>
                        <TableCell>{record.account || '-'}</TableCell>
                        <TableCell>
                          <Badge className={meta.className}>{meta.label}</Badge>
                        </TableCell>
                        <TableCell className="whitespace-nowrap">
                          {formatDateTime(record.created)}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                            <Button variant="ghost" size="sm" onClick={() => setDrawerTask(record)}>
                              详情
                            </Button>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  disabled={!canRetry(record.status)}
                                  onClick={() => handleRetry(record)}
                                >
                                  {retrying === record.task_id ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                  ) : (
                                    <RotateCcw className="h-4 w-4" />
                                  )}
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>重新执行此任务</TooltipContent>
                            </Tooltip>
                            {canDelete(record.status) && (
                              <AlertDialog>
                                <AlertDialogTrigger asChild>
                                  <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive">
                                    <Trash2 className="h-4 w-4" />
                                  </Button>
                                </AlertDialogTrigger>
                                <AlertDialogContent>
                                  <AlertDialogHeader>
                                    <AlertDialogTitle>确认删除</AlertDialogTitle>
                                    <AlertDialogDescription>确认删除此任务？</AlertDialogDescription>
                                  </AlertDialogHeader>
                                  <AlertDialogFooter>
                                    <AlertDialogCancel>取消</AlertDialogCancel>
                                    <AlertDialogAction onClick={() => handleDelete(record.task_id)}>删除</AlertDialogAction>
                                  </AlertDialogFooter>
                                </AlertDialogContent>
                              </AlertDialog>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    )
                  })
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <Sheet open={!!drawerTask} onOpenChange={(open) => !open && setDrawerTask(null)}>
        <SheetContent className="w-[520px] sm:max-w-[520px] overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              任务详情
              {drawerTask && (
                <Badge className={STATUS_META[drawerTask.status ?? 'pending']?.className ?? ''}>
                  {STATUS_META[drawerTask.status ?? 'pending']?.label ?? ''}
                </Badge>
              )}
            </SheetTitle>
            <SheetDescription>
              查看任务的详细信息和运行日志
            </SheetDescription>
          </SheetHeader>
          {drawerTask && (
            <div className="mt-4">
              {canRetry(drawerTask.status) && (
                <Button
                  className="w-full mb-4"
                  onClick={() => {
                    const task = drawerTask
                    setDrawerTask(null)
                    handleRetry(task)
                  }}
                >
                  {retrying === drawerTask.task_id ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <RotateCcw className="h-4 w-4 mr-2" />
                  )}
                  重试此任务
                </Button>
              )}
              <TaskDrawerContent task={drawerTask} />
            </div>
          )}
        </SheetContent>
      </Sheet>

      <Dialog open={addModalOpen} onOpenChange={setAddModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新建任务</DialogTitle>
            <DialogDescription>创建一个新的任务</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>平台</Label>
              <Select value={addPlatform} onValueChange={setAddPlatform}>
                <SelectTrigger>
                  <SelectValue placeholder="选择平台" />
                </SelectTrigger>
                <SelectContent>
                  {PLATFORMS.map((p) => (
                    <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>操作</Label>
              <Select value={addAction} onValueChange={setAddAction}>
                <SelectTrigger>
                  <SelectValue placeholder="选择操作" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="login">登录</SelectItem>
                  <SelectItem value="check">检查</SelectItem>
                  <SelectItem value="upload-video">上传视频</SelectItem>
                  <SelectItem value="upload-note">上传图文</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>账号</Label>
              <Input
                placeholder="输入账号名称"
                value={addAccount}
                onChange={(e) => setAddAccount(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>标题</Label>
              <Input
                placeholder="输入标题（上传操作需要）"
                value={addTitle}
                onChange={(e) => setAddTitle(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddModalOpen(false)}>取消</Button>
            <Button onClick={handleAddTask}>创建</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default TasksPage
