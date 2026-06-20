import { useCallback, useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/alert-dialog'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'
import { PageHeader } from '@/components/ui/page-header'
import { cn } from '@/lib/utils'
import { PLATFORMS, api, type AccountItem } from '../api/client'
import { useToast } from '@/components/ui/toast'
import {
  CheckCircle,
  Check,
  Trash2,
  HelpCircle,
  QrCode,
  Loader2,
  Users,
  RefreshCw,
} from 'lucide-react'

const BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) || 'http://localhost:5409'

type QuickResult = {
  valid: boolean
  reason: string
  age_hours: number | null
  file_size: number | null
}

const QUICK_STATUS_META: Record<string, { className: string; label: string }> = {
  fresh: { className: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400', label: '有效' },
  stale: { className: 'bg-amber-500/15 text-amber-700 dark:text-amber-400', label: '可能过期' },
  no_file: { className: 'bg-red-500/15 text-red-700 dark:text-red-400', label: '无文件' },
  empty: { className: 'bg-red-500/15 text-red-700 dark:text-red-400', label: '空文件' },
  empty_cookies: { className: 'bg-red-500/15 text-red-700 dark:text-red-400', label: '无Cookie' },
  verified: { className: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400', label: '已验证' },
  invalid: { className: 'bg-red-500/15 text-red-700 dark:text-red-400', label: '已失效' },
}

function AccountsPage() {
  const { addToast } = useToast()
  const [accounts, setAccounts] = useState<AccountItem[]>([])
  const [quickResults, setQuickResults] = useState<Map<string, QuickResult>>(new Map())
  const [loading, setLoading] = useState(false)
  const [loginSubmitting, setLoginSubmitting] = useState(false)
  const [checkingAccounts, setCheckingAccounts] = useState<Set<string>>(new Set())
  const [checkingAll, setCheckingAll] = useState(false)
  const [platform, setPlatform] = useState('douyin')
  const [accountName, setAccountName] = useState('')
  const [headless, setHeadless] = useState(true)
  const [qrcodeModalVisible, setQrcodeModalVisible] = useState(false)
  const [qrcodeUrl, setQrcodeUrl] = useState<string | null>(null)
  const [loginStatus, setLoginStatus] = useState<string>('')

  const pendingTasksRef = useRef<Map<string, string>>(new Map())
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  const pollPendingTasks = useCallback(async () => {
    const pending = pendingTasksRef.current
    if (pending.size === 0) {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
        pollTimerRef.current = null
      }
      return
    }

    try {
      const res = await api.getTasks()
      if (!res.success || !res.data) return

      for (const task of res.data) {
        const taskKey = Array.from(pending.entries()).find(([_, tid]) => tid === task.task_id)?.[0]
        if (!taskKey) continue

        if (task.status === 'success') {
          pending.delete(taskKey)
          setQuickResults((prev) => new Map(prev).set(taskKey, { valid: true, reason: 'verified', age_hours: null, file_size: null }))
          addToast(`深度检查通过：${taskKey}`, 'success')
        } else if (task.status === 'failed' || task.status === 'error') {
          pending.delete(taskKey)
          setQuickResults((prev) => new Map(prev).set(taskKey, { valid: false, reason: 'invalid', age_hours: null, file_size: null }))
          addToast(`深度检查失败：${taskKey}`, 'error')
        }
      }

      pendingTasksRef.current = pending
      if (pending.size === 0 && pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
        pollTimerRef.current = null
      }
    } catch {
      void 0
    }
  }, [addToast])

  useEffect(() => {
    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
      }
      eventSourceRef.current?.close()
    }
  }, [])

  const handleDelete = async (platform: string, account: string) => {
    try {
      const res = await api.deleteAccount(platform, account)
      if (res.success) {
        addToast(res.message || `已删除 ${platform}/${account}`, 'success')
        loadAccounts()
      } else {
        addToast(res.message || '删除失败', 'error')
      }
    } catch {
      addToast('删除请求失败', 'error')
    }
  }

  const handleCheck = async (platform: string, account: string) => {
    const key = `${platform}_${account}`
    setCheckingAccounts((prev) => new Set(prev).add(key))
    try {
      const res = await api.checkAccount(platform, account, true)
      if (res.success && res.data) {
        if (res.data.quick) {
          setQuickResults((prev) => new Map(prev).set(key, res.data!.quick))
        }
        if (res.data.task_id) {
          pendingTasksRef.current.set(key, res.data.task_id)
          addToast('深度检查中...', 'info')
          if (!pollTimerRef.current) {
            pollTimerRef.current = setInterval(pollPendingTasks, 2000)
          }
        }
      } else {
        addToast(res.message || '检查失败', 'error')
      }
    } catch {
      addToast('检查请求失败', 'error')
    } finally {
      setCheckingAccounts((prev) => {
        const next = new Set(prev)
        next.delete(key)
        return next
      })
    }
  }

  const handleCheckAll = async () => {
    setCheckingAll(true)
    try {
      const res = await api.checkAllAccounts()
      if (res.success && res.data) {
        const newMap = new Map<string, QuickResult>()
        for (const item of res.data) {
          const key = `${item.platform}_${item.account}`
          newMap.set(key, item.quick)
        }
        setQuickResults(newMap)
        addToast(`已检查 ${res.data.length} 个账号`, 'success')
      } else {
        addToast('批量检查失败', 'error')
      }
    } catch {
      addToast('批量检查请求失败', 'error')
    } finally {
      setCheckingAll(false)
    }
  }

  const loadAccounts = async () => {
    setLoading(true)
    try {
      const res = await api.getAccounts()
      setAccounts(res.data)
    } catch {
      addToast('加载账号列表失败', 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAccounts()
  }, [])

  const onLogin = async () => {
    if (!accountName.trim()) {
      addToast('请输入账号名称', 'warning')
      return
    }

    setLoginSubmitting(true)
    setQrcodeModalVisible(true)
    setQrcodeUrl(null)
    setLoginStatus('正在启动浏览器...')

    const qrLoginPlatforms = ['douyin', 'kuaishou', 'xiaohongshu', 'tencent']

    if (!qrLoginPlatforms.includes(platform)) {
      setQrcodeModalVisible(false)
      try {
        const data = await api.loginAccount({
          platform,
          account: accountName,
          headless,
        })
        if (data.success) {
          addToast(`登录任务已提交：${data.data?.task_id ?? '-'}`, 'success')
          setAccountName('')
          loadAccounts()
        } else {
          addToast(data.message || '登录失败', 'error')
        }
      } catch {
        addToast('登录请求失败', 'error')
      } finally {
        setLoginSubmitting(false)
      }
      return
    }

    const eventSource = new EventSource(
      `${BASE_URL}/api/accounts/login/sse?platform=${encodeURIComponent(platform)}&account=${encodeURIComponent(accountName)}&headless=${encodeURIComponent(String(headless))}`
    )

    let connected = false

    eventSource.onopen = () => {
      connected = true
      setLoginStatus('正在连接登录服务...')
    }

    eventSource.addEventListener('qrcode', (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.image_data_url) {
          setQrcodeUrl(data.image_data_url)
          setLoginStatus('请使用手机扫码登录')
        }
      } catch {
        void 0
      }
    })

    eventSource.addEventListener('result', (e) => {
      eventSource.close()
      try {
        const data = JSON.parse(e.data)
        if (data.success) {
          setLoginStatus('登录成功！')
          addToast('扫码登录成功', 'success')
          setTimeout(() => {
            setQrcodeModalVisible(false)
            setAccountName('')
            loadAccounts()
          }, 1000)
        } else {
          setQrcodeModalVisible(false)
          addToast(data.message || '登录失败', 'error')
          setLoginSubmitting(false)
        }
      } catch {
        setQrcodeModalVisible(false)
        addToast('登录失败，请稍后重试', 'error')
        setLoginSubmitting(false)
      }
    })

    eventSource.onerror = () => {
      if (!connected) {
        eventSource.close()
        setQrcodeModalVisible(false)
        setLoginSubmitting(false)
        addToast('无法连接登录服务，请确认后端已启动', 'error')
      }
    }

    eventSourceRef.current = eventSource
    setTimeout(() => {
      eventSource.close()
      setQrcodeModalVisible(false)
      setLoginSubmitting(false)
      addToast('登录超时，请重试', 'warning')
    }, 30000)
  }

  const accountKey = (record: AccountItem) => `${record.platform}_${record.account_name}`
  const isChecking = (record: AccountItem) => checkingAccounts.has(accountKey(record))

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="账号管理"
        description="管理已登录的社交媒体账号"
        icon={<Users className="h-5 w-5 text-muted-foreground" />}
        actions={
          <Button variant="outline" size="sm" onClick={loadAccounts}>
            <RefreshCw className="h-4 w-4 mr-1" />
            刷新
          </Button>
        }
      />

      <Card className="card-refined">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>账号列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center gap-4 mb-4">
            <Select
              onValueChange={async (value) => {
                const plat = value === 'all' ? undefined : value
                try {
                  const res = await api.getAccounts(plat)
                  setAccounts(res.data)
                } catch {
                  addToast('筛选失败', 'error')
                }
              }}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="全部平台" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部平台</SelectItem>
                {PLATFORMS.map((p) => (
                  <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button onClick={loadAccounts}>刷新列表</Button>
            <Button
              variant="outline"
              onClick={handleCheckAll}
              disabled={checkingAll || accounts.length === 0}
            >
              {checkingAll ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Check className="h-4 w-4 mr-2" />}
              批量检查
            </Button>
          </div>

          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[100px]">平台</TableHead>
                  <TableHead className="w-[160px]">账号</TableHead>
                  <TableHead className="w-[120px]">状态</TableHead>
                  <TableHead className="w-[200px]">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  Array.from({ length: 3 }).map((_, i) => (
                    <TableRow key={i}>
                      <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                      <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                      <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                      <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                    </TableRow>
                  ))
                ) : accounts.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4}>
                      <EmptyState
                        icon={<Users className="h-6 w-6" />}
                        title="暂无账号"
                        description="登录账号后会在这里显示"
                      />
                    </TableCell>
                  </TableRow>
                ) : (
                  accounts.map((record) => {
                    const key = accountKey(record)
                    const isDeepChecking = pendingTasksRef.current.has(key)
                    const result = quickResults.get(key)

                    return (
                      <TableRow key={key}>
                        <TableCell className="font-medium">{record.platform}</TableCell>
                        <TableCell>{record.account_name}</TableCell>
                        <TableCell>
                          {isDeepChecking ? (
                            <Badge className="bg-blue-500/15 text-blue-700 dark:text-blue-400">
                              <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                              验证中
                            </Badge>
                          ) : result ? (
                            <Tooltip>
                              <TooltipTrigger>
                                <Badge className={cn(QUICK_STATUS_META[result.reason]?.className ?? 'bg-muted text-muted-foreground')}>
                                  {QUICK_STATUS_META[result.reason]?.label ?? result.reason}
                                </Badge>
                              </TooltipTrigger>
                              <TooltipContent>
                                {result.age_hours !== null
                                  ? `${QUICK_STATUS_META[result.reason]?.label ?? result.reason} (${Math.round(result.age_hours)}小时前更新)`
                                  : QUICK_STATUS_META[result.reason]?.label ?? result.reason}
                              </TooltipContent>
                            </Tooltip>
                          ) : (
                            <Badge variant="outline">
                              <HelpCircle className="h-3 w-3 mr-1" />
                              未检查
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleCheck(record.platform, record.account_name)}
                                  disabled={isChecking(record)}
                                >
                                  {isChecking(record) ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                  ) : (
                                    <CheckCircle className="h-4 w-4" />
                                  )}
                                  <span className="ml-1">检查</span>
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>检查 Cookie 是否有效</TooltipContent>
                            </Tooltip>
                            <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive">
                                  <Trash2 className="h-4 w-4" />
                                  <span className="ml-1">删除</span>
                                </Button>
                              </AlertDialogTrigger>
                              <AlertDialogContent>
                                <AlertDialogHeader>
                                  <AlertDialogTitle>确认删除</AlertDialogTitle>
                                  <AlertDialogDescription>
                                    确认删除 {record.platform}/{record.account_name}？删除后 Cookie 文件将被移除，无法恢复。
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>取消</AlertDialogCancel>
                                  <AlertDialogAction
                                    onClick={() => handleDelete(record.platform, record.account_name)}
                                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                  >
                                    确认删除
                                  </AlertDialogAction>
                                </AlertDialogFooter>
                              </AlertDialogContent>
                            </AlertDialog>
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

      <Card className="card-refined">
        <CardHeader>
          <CardTitle>登录账号</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-2">
              <Label>平台</Label>
              <Select value={platform} onValueChange={setPlatform}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PLATFORMS.map((p) => (
                    <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>账号名称</Label>
              <Input
                placeholder="例如 xiandnahuang"
                value={accountName}
                onChange={(e) => setAccountName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>无头模式</Label>
              <Select value={String(headless)} onValueChange={(v) => setHeadless(v === 'true')}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="true">是</SelectItem>
                  <SelectItem value="false">否（显示浏览器）</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-end">
              <Button
                className="w-full"
                onClick={onLogin}
                disabled={loginSubmitting || !accountName.trim()}
              >
                {loginSubmitting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <QrCode className="h-4 w-4 mr-2" />}
                登录
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Dialog open={qrcodeModalVisible} onOpenChange={setQrcodeModalVisible}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <QrCode className="h-5 w-5 text-primary" />
              扫码登录
            </DialogTitle>
            <DialogDescription>
              {loginStatus || '正在获取二维码...'}
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-center py-4">
            {qrcodeUrl ? (
              <img
                src={qrcodeUrl}
                alt="登录二维码"
                className="w-60 h-60 rounded-lg border"
              />
            ) : (
              <div className="w-60 h-60 flex items-center justify-center rounded-lg border bg-muted/50">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default AccountsPage
