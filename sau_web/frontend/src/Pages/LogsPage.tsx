import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Button,
  Card,
  Checkbox,
  Col,
  Input,
  message,
  Row,
  Select,
  Space,
  Statistic,
  Typography,
} from 'antd'
import {
  CloseCircleOutlined,
  InfoCircleOutlined,
  LoadingOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import { api, type LogEntry } from '../api/client'

type Level = 'all' | 'info' | 'warn' | 'error'

const MAX_LOGS = 5000

const LEVEL_OPTIONS: { label: React.ReactNode; value: Level }[] = [
  { label: '全部', value: 'all' },
  { label: <Space size={4}><InfoCircleOutlined style={{ color: '#096dd9' }} /><span>信息</span></Space>, value: 'info' },
  { label: <Space size={4}><WarningOutlined style={{ color: '#d48806' }} /><span>警告</span></Space>, value: 'warn' },
  { label: <Space size={4}><CloseCircleOutlined style={{ color: '#cf1322' }} /><span>错误</span></Space>, value: 'error' },
]

function classifyLevel(message: string): Level {
  if (/error|失败|ERROR|Exception/.test(message)) return 'error'
  if (/warn|警告|WARN|注意/.test(message)) return 'warn'
  return 'info'
}

function parseDate(ts: string) {
  const d = new Date(ts)
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleString('zh-CN', { hour12: false })
}

/** Extract task id from a log message like `[upload-video-a1b2c3d4e5f6] ...` */
function extractTaskId(message: string): string | null {
  const match = message.match(/^\[([^\]]+)\]/)
  return match ? match[1] : null
}

function LogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [keyword, setKeyword] = useState('')
  const [level, setLevel] = useState<Level>('all')
  const [autoScroll, setAutoScroll] = useState(true)
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const latestTsRef = useRef<string | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Load logs incrementally
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
        // Cap to prevent unbounded memory growth, keeping most recent
        return sorted.length > MAX_LOGS ? sorted.slice(-MAX_LOGS) : sorted
      })
      latestTsRef.current = list[list.length - 1].ts
    } catch {
      // ignore poll errors
    }
  }, [])

  // Poll every 2s
  useEffect(() => {
    loadLogs()
    pollingRef.current = setInterval(loadLogs, 2000)
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
    }
  }, [loadLogs])

  // Auto scroll when new logs arrive
  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [logs, autoScroll])

  // Extract unique task ids from all logs (for the filter dropdown)
  const taskIdOptions = useMemo(() => {
    const ids = new Set<string>()
    for (const entry of logs) {
      const tid = extractTaskId(entry.message)
      if (tid) ids.add(tid)
    }
    return Array.from(ids).sort()
  }, [logs])

  // Filtered logs
  const filteredLogs = useMemo(() => {
    let result = logs

    // Level filter
    if (level !== 'all') {
      result = result.filter((item) => classifyLevel(item.message) === level)
    }

    // Task ID filter
    if (selectedTaskId) {
      const prefix = `[${selectedTaskId}]`
      result = result.filter((item) => item.message.startsWith(prefix))
    }

    // Keyword search
    const kw = keyword.trim().toLowerCase()
    if (kw) {
      result = result.filter((item) => item.message.toLowerCase().includes(kw))
    }

    return result
  }, [logs, keyword, level, selectedTaskId])

  // Stats
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

  // Export
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
    message.success('日志导出完成')
  }

  const handleReset = () => {
    latestTsRef.current = null
    setLogs([])
    loadLogs()
  }

  return (
    <div style={{ padding: 0 }}>
      {/* Stats */}
      <Row gutter={12} style={{ marginBottom: 12 }}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="日志总量" value={summary.all} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="信息" value={summary.info} valueStyle={{ color: '#096dd9' }} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="警告" value={summary.warn} valueStyle={{ color: '#d48806' }} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="错误" value={summary.error} valueStyle={{ color: '#cf1322' }} />
          </Card>
        </Col>
      </Row>

      {/* Filters */}
      <Card>
        <Row gutter={12} align="middle" style={{ marginBottom: 10 }}>
          <Col xs={24} sm={12} md={8}>
            <Input.Search
              placeholder="搜索日志内容..."
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onSearch={(value) => setKeyword(value)}
              allowClear
            />
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Select<Level>
              value={level}
              onChange={(val) => setLevel(val)}
              options={LEVEL_OPTIONS}
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Select<string | null>
              value={selectedTaskId}
              onChange={(val) => setSelectedTaskId(val)}
              allowClear
              placeholder="按任务筛选"
              style={{ width: '100%' }}
              showSearch
              optionFilterProp="label"
            >
              {taskIdOptions.map((id) => (
                <Select.Option key={id} value={id} label={id}>
                  <code style={{ fontSize: 12 }}>{id.length > 24 ? `${id.slice(0, 12)}...${id.slice(-8)}` : id}</code>
                </Select.Option>
              ))}
            </Select>
          </Col>
          <Col xs={24} sm={24} md={8} style={{ textAlign: 'right' }}>
            <Space size="small" style={{ marginLeft: 'auto' }} wrap>
              <Checkbox checked={autoScroll} onChange={(e) => setAutoScroll(e.target.checked)}>
                自动滚动
              </Checkbox>
              <Button onClick={handleReset}>重置</Button>
              <Button type="primary" onClick={handleExport} disabled={filteredLogs.length === 0}>
                导出日志
              </Button>
            </Space>
          </Col>
        </Row>

        {/* Live log view */}
        {filteredLogs.length === 0 ? (
          <div
            style={{
              height: 520,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: '#1e1e1e',
              borderRadius: 8,
            }}
          >
            <Typography.Text type="secondary" style={{ color: '#888' }}>
              {logs.length === 0 ? '等待日志...' : '无匹配日志'}
            </Typography.Text>
          </div>
        ) : (
          <div
            ref={containerRef}
            style={{
              height: 520,
              overflowY: 'auto',
              background: '#1e1e1e',
              borderRadius: 8,
              padding: '10px 14px',
              fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
              fontSize: 12,
              lineHeight: 1.7,
            }}
          >
            {filteredLogs.map((entry, idx) => {
              const lv = classifyLevel(entry.message)
              const color =
                lv === 'error' ? '#f48771' :
                lv === 'warn' ? '#dcdcaa' :
                '#d4d4d4'
              const badge =
                lv === 'error' ? '🔴' :
                lv === 'warn' ? '🟡' :
                '  '
              return (
                <div key={`${entry.ts}-${idx}`} style={{ marginBottom: 1 }}>
                  <span style={{ color: '#6a9955', marginRight: 10, userSelect: 'none' }}>
                    {parseDate(entry.ts)}
                  </span>
                  <span style={{ color }}>{badge} {entry.message}</span>
                </div>
              )
            })}
            {/* Loading indicator pinned to bottom if backend is still producing logs */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4, color: '#888' }}>
              <LoadingOutlined style={{ fontSize: 11 }} />
              <span style={{ fontSize: 11 }}>实时接收中...</span>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}

export default LogsPage
