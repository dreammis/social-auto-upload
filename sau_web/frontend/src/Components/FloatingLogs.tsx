import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { api, type LogEntry } from '../api/client'
import { useTheme } from './ThemeProvider'
import {
  FileText,
  Maximize2,
  Minimize2,
  X,
} from 'lucide-react'

type Position = { x: number; y: number }
type Size = { width: number; height: number }

function getInitialPosition(): Position {
  if (typeof window === 'undefined') return { x: 24, y: 24 }
  return { x: window.innerWidth - 520, y: window.innerHeight - 420 }
}

function getInitialSize(): Size {
  return { width: 520, height: 380 }
}

function getLogColor(message: string) {
  if (/( error|失败|ERROR)/.test(message)) return 'text-red-400'
  if (/( success|成功|finished|完成)/.test(message)) return 'text-emerald-500'
  if (/( warn|警告|WARN)/.test(message)) return 'text-amber-400'
  return ''
}

function LogLine({ entry }: { entry: LogEntry }) {
  const color = getLogColor(entry.message)
  return (
    <div className="py-0.5 font-mono text-xs">
      <span className="mr-2 text-emerald-600 dark:text-emerald-400">{entry.ts}</span>
      <span className={color}>{entry.message}</span>
    </div>
  )
}

function FloatingLogs() {
  const { resolved } = useTheme()
  const isDark = resolved === 'dark'

  const themeColors = useMemo(() => ({
    containerBg: 'var(--card)',
    containerBorder: 'var(--border)',
    logAreaBg: 'var(--muted)',
    emptyText: 'var(--muted-foreground)',
    shadow: isDark ? '0 12px 32px rgba(0,0,0,0.4)' : '0 12px 32px rgba(0,0,0,0.1)',
  }), [isDark])

  const [visible, setVisible] = useState(true)
  const [minimized, setMinimized] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)

  // Detect open Radix dialogs/drawers — only react when the value changes.
  // Bare DOM-events are skipped: only the actual data-state transition matters.
  useEffect(() => {
    const check = () => {
      const hasOpen = document.querySelector('[data-state="open"]') !== null
      setDrawerOpen((prev) => (prev === hasOpen ? prev : hasOpen))
    }
    const observer = new MutationObserver(check)
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['data-state'],
    })
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
        return sorted.length > 2000 ? sorted.slice(-2000) : sorted
      })
      const payload = res.data
      if (payload.length) {
        latestTsRef.current = payload[payload.length - 1].ts
      }
    } catch {
      // ignore
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
      <Button
        className="fixed right-6 bottom-6 h-11 w-11 rounded-full shadow-md z-[9999] btn-elegant"
        size="icon"
        onClick={() => setVisible(true)}
        aria-label="Show logs"
      >
        <FileText className="h-4 w-4" />
      </Button>
    )
  }

  return (
    <div
      ref={containerRef}
      className="fixed left-0 top-0 z-[9999] flex flex-col overflow-hidden rounded-lg border"
      style={{
        transform: `translate(${position.x}px, ${position.y}px)`,
        willChange: 'transform',
        width: size.width,
        height: minimized ? 44 : size.height,
        minWidth: 320,
        minHeight: minimized ? 44 : 180,
        background: themeColors.containerBg,
        borderColor: themeColors.containerBorder,
        boxShadow: themeColors.shadow,
      }}
    >
      <div
        onMouseDown={handleDragStart}
        className="flex cursor-move items-center justify-between gap-2 px-3 py-2.5 text-background select-none bg-foreground"
      >
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4" />
          <span className="text-sm font-medium">运行日志</span>
          <Badge className="bg-background/20 text-background">{filteredLogs.length}</Badge>
        </div>
        <div className="flex items-center gap-2">
          <Input
            placeholder="过滤..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            onClick={(e) => e.stopPropagation()}
            onMouseDown={(e) => e.stopPropagation()}
            className="h-7 w-[140px] text-xs bg-background/20 border-background/30 text-background placeholder:text-background/50"
          />
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-background hover:text-background hover:bg-background/20"
            onClick={(e) => {
              e.stopPropagation()
              setMinimized((v) => !v)
            }}
            aria-label={minimized ? 'Maximize logs' : 'Minimize logs'}
          >
            {minimized ? <Maximize2 className="h-4 w-4" /> : <Minimize2 className="h-4 w-4" />}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-background hover:text-background hover:bg-background/20"
            onClick={(e) => {
              e.stopPropagation()
              setVisible(false)
            }}
            aria-label="Close logs"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {!minimized && (
        <ScrollArea className="flex-1" style={{ background: themeColors.logAreaBg }}>
          <div className="p-3">
            {filteredLogs.length === 0 ? (
              <div className="text-center mt-16 text-muted-foreground">暂无日志</div>
            ) : (
              filteredLogs.map((entry) => (
                <LogLine key={entry.ts + entry.message} entry={entry} />
              ))
            )}
          </div>
        </ScrollArea>
      )}

      {!minimized && (
        <div
          onMouseDown={handleResizeStart}
          className="absolute right-0 bottom-0 flex h-[18px] w-[18px] cursor-nwse-resize items-end justify-end p-0.5"
        >
          <Minimize2 className="h-3 w-3 text-muted-foreground" />
        </div>
      )}
    </div>
  )
}

export default FloatingLogs
