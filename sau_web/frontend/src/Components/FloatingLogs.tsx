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

/** Maximum number of log entries to keep in memory */
const MAX_LOGS = 2000

function getInitialPosition(): Position {
  if (typeof window === 'undefined') return { x: 24, y: 24 }
  // Default to the bottom-LEFT corner so the panel never sits on top of the
  // primary CTA (which lives bottom-right). The user can drag the panel
  // anywhere on screen.
  return { x: 24, y: Math.max(80, window.innerHeight - 420) }
}

function getInitialSize(): Size {
  return { width: 520, height: 380 }
}

// ── Persistence: user's preferred position / size sticks across reloads. ─
const POS_STORAGE_KEY = 'sau-floating-logs-pos'
const SIZE_STORAGE_KEY = 'sau-floating-logs-size'

function clampToViewport(pos: Position, size: Size): Position {
  if (typeof window === 'undefined') return pos
  const margin = 8
  const maxX = Math.max(margin, window.innerWidth - size.width - margin)
  const maxY = Math.max(margin, window.innerHeight - size.height - margin)
  return {
    x: Math.min(Math.max(pos.x, margin), maxX),
    y: Math.min(Math.max(pos.y, margin), maxY),
  }
}

function loadInitialGeometry(): { position: Position; size: Size } {
  const size = getInitialSize()
  const position = getInitialPosition()
  if (typeof window === 'undefined') return { position, size }
  try {
    const rawSize = window.localStorage.getItem(SIZE_STORAGE_KEY)
    if (rawSize) {
      const parsed = JSON.parse(rawSize) as Partial<Size>
      if (typeof parsed.width === 'number' && typeof parsed.height === 'number') {
        size.width = Math.max(320, Math.min(parsed.width, window.innerWidth - 16))
        size.height = Math.max(180, Math.min(parsed.height, window.innerHeight - 16))
      }
    }
    const rawPos = window.localStorage.getItem(POS_STORAGE_KEY)
    if (rawPos) {
      const parsed = JSON.parse(rawPos) as Partial<Position>
      if (typeof parsed.x === 'number' && typeof parsed.y === 'number') {
        position.x = parsed.x
        position.y = parsed.y
      }
    }
  } catch {
    // corrupted JSON / quota error / private browser → fall back to defaults
  }
  return { position: clampToViewport(position, size), size }
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

  // Persist visible/minimized state across reloads
  const [visible, setVisible] = useState(() => {
    if (typeof window === 'undefined') return true
    try {
      const stored = window.localStorage.getItem('sau-floating-logs-visible')
      return stored !== null ? stored === 'true' : true
    } catch {
      return true
    }
  })

  const [minimized, setMinimized] = useState(() => {
    if (typeof window === 'undefined') return false
    try {
      const stored = window.localStorage.getItem('sau-floating-logs-minimized')
      return stored !== null ? stored === 'true' : false
    } catch {
      return false
    }
  })
  const [drawerOpen, setDrawerOpen] = useState(false)

  // Detect open Radix dialogs/drawers using targeted MutationObserver.
  //
  // We observe only the document.body for attribute changes on elements
  // with data-state attribute, which is much more efficient than polling
  // or observing the entire DOM tree.
  useEffect(() => {
    const sync = (next: boolean) => setDrawerOpen((cur) => (cur === next ? cur : next))

    // Initial check
    sync(document.querySelector('[data-state="open"]') !== null)

    // Create observer for data-state attribute changes
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === 'attributes' && mutation.attributeName === 'data-state') {
          const target = mutation.target as HTMLElement
          if (target.matches('[data-state]')) {
            sync(document.querySelector('[data-state="open"]') !== null)
            break
          }
        }
      }
    })

    // Observe only attribute changes on elements with data-state
    observer.observe(document.body, {
      attributes: true,
      attributeFilter: ['data-state'],
      subtree: true,
    })

    return () => observer.disconnect()
  }, [])

  // Persist visible/minimized state to localStorage
  useEffect(() => {
    try {
      window.localStorage.setItem('sau-floating-logs-visible', String(visible))
    } catch {
      /* private mode / quota exceeded — silently ignore */
    }
  }, [visible])

  useEffect(() => {
    try {
      window.localStorage.setItem('sau-floating-logs-minimized', String(minimized))
    } catch {
      /* private mode / quota exceeded — silently ignore */
    }
  }, [minimized])

  const [filter, setFilter] = useState('')
  const [logs, setLogs] = useState<LogEntry[]>([])
  const initialGeometry = useMemo(loadInitialGeometry, [])
  const [size, setSize] = useState<Size>(initialGeometry.size)
  const [position, setPosition] = useState<Position>(initialGeometry.position)

  // Button position for the collapsed state
  const [buttonPosition, setButtonPosition] = useState<Position>(() => {
    if (typeof window === 'undefined') return { x: 24, y: 24 }
    try {
      const stored = window.localStorage.getItem('sau-floating-logs-btn-pos')
      if (stored) {
        const parsed = JSON.parse(stored) as { x?: number; y?: number }
        if (typeof parsed.x === 'number' && typeof parsed.y === 'number') {
          return clampToViewport({ x: parsed.x, y: parsed.y }, { width: 44, height: 44 })
        }
      }
    } catch {
      // ignore
    }
    return { x: 24, y: Math.max(80, window.innerHeight - 80) }
  })

  const buttonDraggingRef = useRef(false)
  const buttonDragOffset = useRef<Position>({ x: 0, y: 0 })
  const buttonPendingPos = useRef<Position>({ x: 0, y: 0 })
  const buttonRef = useRef<HTMLButtonElement>(null)

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
    const maxRetries = 3
    let retryCount = 0

    const fetchLogs = async (): Promise<void> => {
      try {
        const res = await api.getLogs(latestTsRef.current || undefined)
      setLogs((prev) => {
        // Merge new logs with existing ones
        const map = new Map(prev.map((item) => [item.ts, item]))
        for (const item of res.data) {
          map.set(item.ts, item)
        }

        // Always sort once, then slice if needed
        const sorted = Array.from(map.values()).sort((a, b) => a.ts.localeCompare(b.ts))
        return sorted.length > MAX_LOGS ? sorted.slice(-MAX_LOGS) : sorted
      })
        const payload = res.data
        if (payload.length) {
          latestTsRef.current = payload[payload.length - 1].ts
        }
      } catch (error) {
        retryCount++
        if (retryCount < maxRetries) {
          // Exponential backoff: 1s, 2s, 4s
          const delay = Math.pow(2, retryCount - 1) * 1000
          await new Promise((resolve) => setTimeout(resolve, delay))
          return fetchLogs()
        }
        // Silently fail after max retries to avoid disrupting the UI
      }
    }

    await fetchLogs()
  }, [])

  useEffect(() => {
    loadLogs()

    let timer: ReturnType<typeof setInterval> | null = null

    const startPolling = () => {
      if (timer) clearInterval(timer)
      timer = setInterval(loadLogs, 2000)
    }

    const stopPolling = () => {
      if (timer) {
        clearInterval(timer)
        timer = null
      }
    }

    const handleVisibilityChange = () => {
      if (document.hidden) {
        stopPolling()
      } else {
        loadLogs() // Immediate fetch when page becomes visible
        startPolling()
      }
    }

    // Start polling if page is visible
    if (!document.hidden) {
      startPolling()
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      stopPolling()
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [loadLogs])

  // Persist drag-drop position + resize across reloads. ``try/catch`` keeps
  // private-mode browsers and quota errors from breaking the panel.
  useEffect(() => {
    try {
      window.localStorage.setItem(POS_STORAGE_KEY, JSON.stringify(position))
    } catch {
      /* private mode / quota exceeded — silently ignore */
    }
  }, [position])

  useEffect(() => {
    try {
      window.localStorage.setItem(SIZE_STORAGE_KEY, JSON.stringify(size))
    } catch {
      /* private mode / quota exceeded — silently ignore */
    }
  }, [size])

  // Re-clamp position when the viewport shrinks/grows so a dock change or
  // rotation doesn't strand the panel off-screen. Functional setState bails
  // out when the clamped coords are identical, keeping resize ticks cheap.
  useEffect(() => {
    const handleResize = () => {
      setPosition((cur) => {
        const next = clampToViewport(cur, size)
        return next.x === cur.x && next.y === cur.y ? cur : next
      })
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [size])

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

  // Button drag handlers
  const handleButtonDragStart = (e: React.MouseEvent) => {
    e.preventDefault()
    buttonDraggingRef.current = true
    buttonPendingPos.current = buttonPosition
    buttonDragOffset.current = {
      x: e.clientX - buttonPosition.x,
      y: e.clientY - buttonPosition.y,
    }
  }

  // Persist button position to localStorage
  useEffect(() => {
    try {
      window.localStorage.setItem('sau-floating-logs-btn-pos', JSON.stringify(buttonPosition))
    } catch {
      /* private mode / quota exceeded — silently ignore */
    }
  }, [buttonPosition])

  // Re-clamp button position when viewport changes
  useEffect(() => {
    const handleResize = () => {
      setButtonPosition((cur) => {
        const next = clampToViewport(cur, { width: 44, height: 44 })
        return next.x === cur.x && next.y === cur.y ? cur : next
      })
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // Button drag mouse events
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!buttonDraggingRef.current) return

      buttonPendingPos.current = {
        x: e.clientX - buttonDragOffset.current.x,
        y: e.clientY - buttonDragOffset.current.y,
      }

      if (buttonRef.current) {
        buttonRef.current.style.transform = `translate(${buttonPendingPos.current.x}px, ${buttonPendingPos.current.y}px)`
      }
    }

    const handleMouseUp = () => {
      if (buttonDraggingRef.current) {
        buttonDraggingRef.current = false
        setButtonPosition(clampToViewport(buttonPendingPos.current, { width: 44, height: 44 }))
      }
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [])

  const filteredLogs = filter
    ? logs.filter((item) => item.message.toLowerCase().includes(filter.toLowerCase()))
    : logs

  if (!visible || drawerOpen) {
    return (
      <Button
        ref={buttonRef}
        className="fixed left-0 top-0 h-11 w-11 rounded-full shadow-md z-[9999] btn-elegant cursor-move"
        size="icon"
        style={{
          transform: `translate(${buttonPosition.x}px, ${buttonPosition.y}px)`,
          willChange: 'transform',
        }}
        onMouseDown={handleButtonDragStart}
        onClick={() => {
          // Only open if not dragging
          if (!buttonDraggingRef.current) {
            setVisible(true)
          }
        }}
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
