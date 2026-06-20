import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { PageHeader } from '@/components/ui/page-header'
import { api, type LogEntry } from '../api/client'
import { useToast } from '@/components/ui/toast'
import {
  AlertCircle,
  Download,
  Info,
  Loader2,
  RefreshCw,
  Search,
  AlertTriangle,
  FileText,
} from 'lucide-react'

type Level = 'all' | 'info' | 'warn' | 'error'

const MAX_LOGS = 5000

function classifyLevel(message: string): Level {
  if (/error|失败|ERROR|Exception/.test(message)) return 'error'
  if (/warn|警告|WARN|注意/.test(message)) return 'warn'
  return 'info'
}

function parseDate(ts: string) {
  const d = new Date(ts)
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleString('zh-CN', { hour12: false })
}

function extractTaskId(message: string): string | null {
  const match = message.match(/^\[([^\]]+)\]/)
  return match ? match[1] : null
}

function LogsPage() {
  const { addToast } = useToast()
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [keyword, setKeyword] = useState('')
  const [level, setLevel] = useState<Level>('all')
  const [autoScroll, setAutoScroll] = useState(true)
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const latestTsRef = useRef<string | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadLogs = useCallback(async () => {
    try {
      const res = await api.getLogs(latestTsRef.current || undefined)
      const list = res.data ?? []
      if (list.length === 0) return

      setLogs((prev) => {
        const map = new Map(prev.map((item) => [item.ts, item]))
        for (const item of list) {
          map.set(item.ts, item)
        }
        const sorted = Array.from(map.values()).sort((a, b) => a.ts.localeCompare(b.ts))
        return sorted.length > MAX_LOGS ? sorted.slice(-MAX_LOGS) : sorted
      })
      latestTsRef.current = list[list.length - 1].ts
    } catch {
      // ignore poll errors
    }
  }, [])

  useEffect(() => {
    loadLogs()
    pollingRef.current = setInterval(loadLogs, 2000)
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
    }
  }, [loadLogs])

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [logs, autoScroll])

  const taskIdOptions = useMemo(() => {
    const ids = new Set<string>()
    for (const entry of logs) {
      const tid = extractTaskId(entry.message)
      if (tid) ids.add(tid)
    }
    return Array.from(ids).sort()
  }, [logs])

  const filteredLogs = useMemo(() => {
    let result = logs

    if (level !== 'all') {
      result = result.filter((item) => classifyLevel(item.message) === level)
    }

    if (selectedTaskId) {
      const prefix = `[${selectedTaskId}]`
      result = result.filter((item) => item.message.startsWith(prefix))
    }

    const kw = keyword.trim().toLowerCase()
    if (kw) {
      result = result.filter((item) => item.message.toLowerCase().includes(kw))
    }

    return result
  }, [logs, keyword, level, selectedTaskId])

  const summary = useMemo(() => {
    let info = 0
    let warn = 0
    let error = 0
    for (const item of logs) {
      const lv = classifyLevel(item.message)
      if (lv === 'info') info += 1
      else if (lv === 'warn') warn += 1
      else error += 1
    }
    return { all: logs.length, info, warn, error }
  }, [logs])

  const exportText = useMemo(() => {
    return filteredLogs.map((item) => `${item.ts} | ${item.message}`).join('\n')
  }, [filteredLogs])

  const handleExport = () => {
    const blob = new Blob([exportText], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `logs-${new Date().toISOString().replace(/[: ]/g, '-')}.txt`
    a.click()
    URL.revokeObjectURL(url)
    addToast('日志导出完成', 'success')
  }

  const handleReset = () => {
    latestTsRef.current = null
    setLogs([])
    loadLogs()
  }

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="运行日志"
        description="实时查看系统运行日志"
        icon={<FileText className="h-5 w-5 text-muted-foreground" />}
        actions={
          <Button variant="outline" size="sm" onClick={handleExport} disabled={filteredLogs.length === 0}>
            <Download className="h-4 w-4 mr-1" />
            导出日志
          </Button>
        }
      />

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card className="card-refined">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">日志总量</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary.all}</div>
          </CardContent>
        </Card>
        <Card className="card-refined">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">信息</CardTitle>
            <Info className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{summary.info}</div>
          </CardContent>
        </Card>
        <Card className="card-refined">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">警告</CardTitle>
            <AlertTriangle className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber-600">{summary.warn}</div>
          </CardContent>
        </Card>
        <Card className="card-refined">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">错误</CardTitle>
            <AlertCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{summary.error}</div>
          </CardContent>
        </Card>
      </div>

      <Card className="card-refined">
        <CardContent className="pt-6">
          <div className="flex flex-wrap items-center gap-4 mb-4">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="搜索日志内容..."
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  className="pl-8"
                />
              </div>
            </div>
            <Select value={level} onValueChange={(v) => setLevel(v as Level)}>
              <SelectTrigger className="w-[120px]">
                <SelectValue placeholder="日志级别" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部</SelectItem>
                <SelectItem value="info">信息</SelectItem>
                <SelectItem value="warn">警告</SelectItem>
                <SelectItem value="error">错误</SelectItem>
              </SelectContent>
            </Select>
            <Select value={selectedTaskId ?? ''} onValueChange={(v) => setSelectedTaskId(v || null)}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="按任务筛选" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部任务</SelectItem>
                {taskIdOptions.map((id) => (
                  <SelectItem key={id} value={id}>
                    <code className="text-xs">{id.length > 20 ? `${id.slice(0, 10)}...${id.slice(-8)}` : id}</code>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-2">
                <Checkbox
                  id="auto-scroll"
                  checked={autoScroll}
                  onCheckedChange={(checked) => setAutoScroll(checked === true)}
                />
                <Label htmlFor="auto-scroll" className="text-sm">自动滚动</Label>
              </div>
              <Button variant="outline" size="sm" onClick={handleReset}>
                <RefreshCw className="h-4 w-4 mr-1" />
                重置
              </Button>
              <Button size="sm" onClick={handleExport} disabled={filteredLogs.length === 0}>
                <Download className="h-4 w-4 mr-1" />
                导出日志
              </Button>
            </div>
          </div>

          {filteredLogs.length === 0 ? (
            <div className="flex h-[520px] items-center justify-center rounded-lg bg-muted/50">
              <p className="text-sm text-muted-foreground">
                {logs.length === 0 ? '等待日志...' : '无匹配日志'}
              </p>
            </div>
          ) : (
            <div
              ref={containerRef}
              className="h-[520px] overflow-y-auto rounded-lg bg-zinc-950 p-4 font-mono text-xs leading-relaxed"
            >
              {filteredLogs.map((entry, idx) => {
                const lv = classifyLevel(entry.message)
                const color =
                  lv === 'error' ? 'text-red-400' :
                  lv === 'warn' ? 'text-yellow-400' :
                  'text-zinc-300'
                const badge =
                  lv === 'error' ? '🔴' :
                  lv === 'warn' ? '🟡' :
                  '  '
                return (
                  <div key={`${entry.ts}-${idx}`} className="mb-0.5">
                    <span className="mr-2 select-none text-emerald-500">
                      {parseDate(entry.ts)}
                    </span>
                    <span className={color}>{badge} {entry.message}</span>
                  </div>
                )
              })}
              <div className="flex items-center gap-2 mt-1 text-zinc-500">
                <Loader2 className="h-3 w-3 animate-spin" />
                <span className="text-[11px]">实时接收中...</span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default LogsPage
