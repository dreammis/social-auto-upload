import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { PageHeader } from '@/components/ui/page-header'
import { cn } from '@/lib/utils'
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
import { ChipBar, type ChipBarVariant } from '@/components/ui/chip-bar'
import { toneFillBgClass, toneTextClass, type Tone } from '@/lib/tone'

type Level = 'all' | 'info' | 'warn' | 'error'
type ResolvedLevel = Exclude<Level, 'all'>

function classifyLevel(message: string): ResolvedLevel {
  if (/error|失败|ERROR|Exception/.test(message)) return 'error'
  if (/warn|警告|WARN|注意/.test(message)) return 'warn'
  return 'info'
}

// Syslog-style channel naming diverges from the project's `Tone` vocabulary
// (ResLevel `warn` ↦ Tone `warning`). Adapter kept LOCAL here so the API
// contract stays syslog-shaped while the rendering tier talks `Tone`.
// Single source of truth for status colors stays in `@/lib/tone`.
function levelToTone(level: ResolvedLevel): Tone {
  return level === 'warn' ? 'warning' : level
}

// Linear DESIGN.md — semantic dot replaces the prior emoji prefix (🔴🟡).
// Colored via the status palette composed through `@/lib/tone` so it tracks
// the design system in both themes (and shares vocabulary with Badge / Alert
// / Toast / ValidityBadge). Records route through `levelToTone()` so the
// syslog→Tone rename happens once here, not at every call site.
const LEVEL_DOT_CLASS: Record<ResolvedLevel, string> = {
  info: toneFillBgClass(levelToTone('info')),
  warn: toneFillBgClass(levelToTone('warn')),
  error: toneFillBgClass(levelToTone('error')),
}

const LEVEL_TEXT_CLASS: Record<ResolvedLevel, string> = {
  // `info` channels stay neutral — they aren't a status warning, they're the
  // baseline log voice, so `text-foreground` (compared to the colored
  // `warning` / `error` text) is intentional.
  info: 'text-foreground',
  warn: toneTextClass(levelToTone('warn')),
  error: toneTextClass(levelToTone('error')),
}

const LEVEL_CHIPS: ReadonlyArray<{
  value: Level
  label: string
  icon: ReactNode
  variant: ChipBarVariant
}> = [
  { value: 'all', label: '全部', icon: <FileText className="h-3.5 w-3.5" />, variant: 'neutral' },
  { value: 'info', label: '信息', icon: <Info className="h-3.5 w-3.5" />, variant: 'info' },
  { value: 'warn', label: '警告', icon: <AlertTriangle className="h-3.5 w-3.5" />, variant: 'warning' },
  { value: 'error', label: '错误', icon: <AlertCircle className="h-3.5 w-3.5" />, variant: 'error' },
]

function parseDate(ts: string) {
  const d = new Date(ts)
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleString('zh-CN', { hour12: false })
}

function extractTaskId(message: string): string | null {
  const match = message.match(/^\[([^\]]+)\]/)
  return match ? match[1] : null
}

function LogsPage() {
  const qc = useQueryClient()
  const { addToast } = useToast()
  const [keyword, setKeyword] = useState('')
  const [debouncedKeyword, setDebouncedKeyword] = useState('')
  const [level, setLevel] = useState<Level>('all')
  const [autoScroll, setAutoScroll] = useState(true)
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    debounceTimerRef.current = setTimeout(() => {
      setDebouncedKeyword(keyword)
    }, 300)
    return () => {
      if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current)
    }
  }, [keyword])

  const { data: logs = [] } = useQuery<LogEntry[]>({
    queryKey: ['logs'],
    queryFn: async () => {
      const res = await api.getLogs()
      return res.data ?? []
    },
    refetchInterval: 2000,
  })

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

    const kw = debouncedKeyword.trim().toLowerCase()
    if (kw) {
      result = result.filter((item) => item.message.toLowerCase().includes(kw))
    }

    return result
  }, [logs, debouncedKeyword, level, selectedTaskId])

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
    qc.invalidateQueries({ queryKey: ['logs'] })
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

      <ChipBar
        options={LEVEL_CHIPS.map((c) => ({ ...c, count: summary[c.value] }))}
        value={level}
        onChange={(v) => setLevel(v as Level)}
        className="mb-2"
      />

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
                  data-search-input
                />
              </div>
            </div>
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
            <div className="flex h-[520px] items-center justify-center rounded-lg bg-muted">
              <p className="text-sm text-muted-foreground">
                {logs.length === 0 ? '等待日志...' : '无匹配日志'}
              </p>
            </div>
          ) : (
            <div
              ref={containerRef}
              className="h-[520px] overflow-y-auto rounded-lg bg-muted p-4 font-mono text-xs leading-relaxed"
            >
              {filteredLogs.map((entry, idx) => {
                const lv = classifyLevel(entry.message)
                return (
                  <div key={`${entry.ts}-${idx}`} className="flex items-start gap-2 mb-0.5">
                    <span
                      className={cn(
                        'mt-[6px] h-1.5 w-1.5 shrink-0 rounded-full',
                        LEVEL_DOT_CLASS[lv],
                      )}
                      aria-hidden
                    />
                    <span className="mr-1 select-none whitespace-nowrap text-emerald-600 dark:text-emerald-400">
                      {parseDate(entry.ts)}
                    </span>
                    <span className={LEVEL_TEXT_CLASS[lv]}>{entry.message}</span>
                  </div>
                )
              })}
              <div className="flex items-center gap-2 mt-1 text-muted-foreground">
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
