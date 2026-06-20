import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { CloseOutlined, ExpandOutlined, FileTextOutlined, ShrinkOutlined } from '@ant-design/icons'
import { FloatButton, Input, Space, Tag, Tooltip } from 'antd'
import { api, type LogEntry } from '../api/client'
import { useTheme } from './ThemeProvider'

type Position = {
  x: number
  y: number
}

type Size = {
  width: number
  height: number
}

function getInitialPosition(): Position {
  if (typeof window === 'undefined') {
    return { x: 24, y: 24 }
  }
  return {
    x: window.innerWidth - 520,
    y: window.innerHeight - 420,
  }
}

function getInitialSize(): Size {
  return { width: 520, height: 380 }
}

function getLogColor(message: string) {
  if (/( error|失败|ERROR)/.test(message)) {
    return 'red'
  }
  if (/( success|成功|finished|完成)/.test(message)) {
    return 'green'
  }
  if (/( warn|警告|WARN)/.test(message)) {
    return 'orange'
  }
  return undefined
}

function LogLine({ entry, tsColor }: { entry: LogEntry; tsColor: string }) {
  const color = getLogColor(entry.message)
  return (
    <div style={{ padding: '2px 0', fontFamily: 'ui-monospace, Consolas, monospace', fontSize: 12 }}>
      <span style={{ color: tsColor, marginRight: 8 }}>{entry.ts}</span>
      {color ? <Tag color={color} style={{ marginRight: 4 }}>{entry.message}</Tag> : <span>{entry.message}</span>}
    </div>
  )
}

function FloatingLogs() {
  const { resolved } = useTheme()
  const isDark = resolved === 'dark'

  const themeColors = useMemo(() => ({
    containerBg: isDark ? '#1f1f1f' : '#fff',
    containerBorder: isDark ? '#303030' : '#e8e8e8',
    logAreaBg: isDark ? '#141414' : '#fafafa',
    emptyText: isDark ? '#555' : '#bfbfbf',
    logTs: isDark ? '#6a9955' : '#8c8c8c',
    shadow: isDark ? '0 12px 32px rgba(0,0,0,0.4)' : '0 12px 32px rgba(0,0,0,0.18)',
  }), [isDark])

  const [visible, setVisible] = useState(true)
  const [minimized, setMinimized] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)

  useEffect(() => {
    const observer = new MutationObserver(() => {
      const hasOpenDrawer = document.querySelector('.ant-drawer-open') !== null
      setDrawerOpen(hasOpenDrawer)
    })

    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['class'],
    })

    const hasOpenDrawer = document.querySelector('.ant-drawer-open') !== null
    setDrawerOpen(hasOpenDrawer)

    return () => observer.disconnect()
  }, [])
  const [filter, setFilter] = useState('')
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [size, setSize] = useState<Size>(getInitialSize)
  const [position, setPosition] = useState<Position>(getInitialPosition)

  const containerRef = useRef<HTMLDivElement>(null)
  const draggingRef = useRef(false)
  const resizingRef = useRef(false)
  const rafIdRef = useRef<number>(0)

  const dragOffset = useRef<Position>({ x: 0, y: 0 })
  const resizeStart = useRef<Position>({ x: 0, y: 0 })
  const sizeStart = useRef<Size>({ width: 0, height: 0 })
  const latestTsRef = useRef<string | null>(null)
  const pendingPos = useRef<Position>({ x: 0, y: 0 })
  const pendingSize = useRef<Size>({ width: 0, height: 0 })

  const loadLogs = useCallback(async () => {
    try {
      const res = await api.getLogs(latestTsRef.current || undefined)
      setLogs((prev) => {
        const map = new Map(prev.map((item) => [item.ts, item]))
        for (const item of res.data) {
          map.set(item.ts, item)
        }
        const sorted = Array.from(map.values()).sort((a, b) => a.ts.localeCompare(b.ts))
        // Cap to prevent unbounded memory growth
        return sorted.length > 2000 ? sorted.slice(-2000) : sorted
      })
      const payload = res.data
      if (payload.length) {
        latestTsRef.current = payload[payload.length - 1].ts
      }
    } catch {
      // ignore poll errors
    }
  }, [])

  useEffect(() => {
    loadLogs()
    const timer = setInterval(loadLogs, 2000)
    return () => clearInterval(timer)
  }, [loadLogs])

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (draggingRef.current) {
        pendingPos.current = {
          x: e.clientX - dragOffset.current.x,
          y: e.clientY - dragOffset.current.y,
        }
      }
      if (resizingRef.current) {
        const dx = e.clientX - resizeStart.current.x
        const dy = e.clientY - resizeStart.current.y
        pendingSize.current = {
          width: Math.max(320, sizeStart.current.width + dx),
          height: Math.max(180, sizeStart.current.height + dy),
        }
      }
      if (!rafIdRef.current) {
        rafIdRef.current = requestAnimationFrame(() => {
          rafIdRef.current = 0
          const el = containerRef.current
          if (!el) return
          if (draggingRef.current) {
            el.style.transform = `translate(${pendingPos.current.x}px, ${pendingPos.current.y}px)`
          }
          if (resizingRef.current) {
            el.style.width = `${pendingSize.current.width}px`
            el.style.height = `${pendingSize.current.height}px`
          }
        })
      }
    }

    const handleMouseUp = () => {
      if (rafIdRef.current) {
        cancelAnimationFrame(rafIdRef.current)
        rafIdRef.current = 0
      }
      if (draggingRef.current) {
        draggingRef.current = false
        setPosition(pendingPos.current)
      }
      if (resizingRef.current) {
        resizingRef.current = false
        setSize(pendingSize.current)
      }
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      if (rafIdRef.current) {
        cancelAnimationFrame(rafIdRef.current)
        rafIdRef.current = 0
      }
    }
  }, [])

  const handleDragStart = (e: React.MouseEvent) => {
    draggingRef.current = true
    pendingPos.current = position
    dragOffset.current = {
      x: e.clientX - position.x,
      y: e.clientY - position.y,
    }
  }

  const handleResizeStart = (e: React.MouseEvent) => {
    e.preventDefault()
    resizingRef.current = true
    pendingSize.current = size
    resizeStart.current = { x: e.clientX, y: e.clientY }
    sizeStart.current = { ...size }
  }

  const filteredLogs = filter
    ? logs.filter((item) => item.message.toLowerCase().includes(filter.toLowerCase()))
    : logs

  if (!visible || drawerOpen) {
    return (
      <FloatButton
        icon={<FileTextOutlined style={{ fontSize: 18 }} />}
        type="primary"
        style={{ right: 24, bottom: 24 }}
        onClick={() => setVisible(true)}
      />
    )
  }

  return (
    <div
      ref={containerRef}
      style={{
        position: 'fixed',
        left: 0,
        top: 0,
        transform: `translate(${position.x}px, ${position.y}px)`,
        willChange: 'transform',
        width: size.width,
        height: minimized ? 44 : size.height,
        minWidth: 320,
        minHeight: minimized ? 44 : 180,
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        background: themeColors.containerBg,
        border: `1px solid ${themeColors.containerBorder}`,
        borderRadius: 8,
        boxShadow: themeColors.shadow,
        overflow: 'hidden',
      }}
    >
      <div
        onMouseDown={handleDragStart}
        style={{
          padding: '10px 12px',
          background: '#001529',
          color: '#fff',
          cursor: 'move',
          userSelect: 'none',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 8,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span><FileTextOutlined style={{ marginRight: 6 }} />运行日志</span>
          <Tag color="blue" style={{ margin: 0, fontSize: 12 }}>{filteredLogs.length}</Tag>
        </div>
        <Space>
          <Input
            placeholder="过滤..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            onClick={(e) => e.stopPropagation()}
            onMouseDown={(e) => e.stopPropagation()}
            style={{ width: 140, height: 28, fontSize: 12 }}
          />
          <Tooltip title={minimized ? '展开' : '收起'}>
            <ExpandOutlined
              style={{ cursor: 'pointer' }}
              rotate={minimized ? 180 : 0}
              onClick={(e) => {
                e.stopPropagation()
                setMinimized((v) => !v)
              }}
            />
          </Tooltip>
          <Tooltip title="关闭">
            <CloseOutlined
              style={{ cursor: 'pointer' }}
              onClick={(e) => {
                e.stopPropagation()
                setVisible(false)
              }}
            />
          </Tooltip>
        </Space>
      </div>

      {!minimized && (
        <div style={{ flex: 1, overflow: 'auto', padding: 12, background: themeColors.logAreaBg }}>
          {filteredLogs.length === 0 ? (
            <div style={{ color: themeColors.emptyText, textAlign: 'center', marginTop: 60 }}>暂无日志</div>
          ) : (
            <div>
              {filteredLogs.map((entry) => (
                <LogLine key={entry.ts + entry.message} entry={entry} tsColor={themeColors.logTs} />
              ))}
            </div>
          )}
        </div>
      )}

      {!minimized && (
        <div
          onMouseDown={handleResizeStart}
          style={{
            position: 'absolute',
            right: 0,
            bottom: 0,
            width: 18,
            height: 18,
            cursor: 'nwse-resize',
            display: 'flex',
            alignItems: 'flex-end',
            justifyContent: 'flex-end',
            padding: 2,
          }}
        >
          <ShrinkOutlined style={{ fontSize: 12, color: themeColors.emptyText }} />
        </div>
      )}
    </div>
  )
}

export default FloatingLogs
