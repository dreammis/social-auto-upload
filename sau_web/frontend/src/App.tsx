import { useCallback, useEffect, useRef, useState } from 'react'
import { BrowserRouter, Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import FloatingLogs from './components/FloatingLogs'
import { ThemeToggle } from './components/ThemeToggle'
import { ThemeProvider } from './components/ThemeProvider'
import { ToastProvider } from '@/components/ui/toast'
import { CommandPalette } from './components/CommandPalette'
import { ErrorBoundary } from './components/ErrorBoundary'
import { NotFound } from './components/NotFound'
import { OnboardingTour, resetOnboardingTour } from './components/OnboardingTour'
import { cn } from '@/lib/utils'
import {
  BarChart3,
  FileText,
  HelpCircle,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  Send,
  Users,
  Zap,
} from 'lucide-react'

import AccountsPage from '@/features/accounts/AccountsPage'
import PublishPage from './Pages/PublishPage'
import LogsPage from './Pages/LogsPage'
import TasksPage from './Pages/TasksPage'

const MOBILE_BREAKPOINT = 768
const COLLAPSE_BREAKPOINT = 1024
const SIDEBAR_STORAGE_KEY = 'sau-sidebar-collapsed'

function getIsMobile() {
  if (typeof window === 'undefined') return false
  return window.innerWidth <= MOBILE_BREAKPOINT
}

function getShouldAutoCollapse() {
  if (typeof window === 'undefined') return false
  return window.innerWidth > MOBILE_BREAKPOINT && window.innerWidth <= COLLAPSE_BREAKPOINT
}

function useViewport() {
  const [isMobile, setIsMobile] = useState(getIsMobile)
  const [shouldAutoCollapse, setShouldAutoCollapse] = useState(getShouldAutoCollapse)

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT)
      setShouldAutoCollapse(
        window.innerWidth > MOBILE_BREAKPOINT && window.innerWidth <= COLLAPSE_BREAKPOINT,
      )
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return { isMobile, shouldAutoCollapse }
}

const navItems = [
  { path: '/', label: '账号管理', icon: Users },
  { path: '/publish', label: '发布中心', icon: Send },
  { path: '/tasks', label: '任务列表', icon: BarChart3 },
  { path: '/logs', label: '运行日志', icon: FileText },
]

// TODO re-add suspense around non-page chrome (command palette, floating logs, etc.) if needed.

function AppShell() {
  const { isMobile, shouldAutoCollapse } = useViewport()
  const location = useLocation()
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    if (typeof window === 'undefined') return false
    const stored = localStorage.getItem(SIDEBAR_STORAGE_KEY)
    if (stored !== null) return stored === 'true'
    return getShouldAutoCollapse()
  })
  const sidebarRef = useRef<HTMLElement>(null)

  const prevAutoRef = useRef(shouldAutoCollapse)
  useEffect(() => {
    if (prevAutoRef.current !== shouldAutoCollapse) {
      setSidebarCollapsed(shouldAutoCollapse)
      prevAutoRef.current = shouldAutoCollapse
    }
  }, [shouldAutoCollapse])

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => {
      const next = !prev
      localStorage.setItem(SIDEBAR_STORAGE_KEY, String(next))
      return next
    })
  }, [])

  const navigate = useNavigate()
  const [paletteOpen, setPaletteOpen] = useState(false)

  // Global keyboard shortcuts. ⌘K / Ctrl-K opens the command palette from any
  // focus state; "/" and "n" are gated on `isTyping` so they only fire when
  // the user is not actively typing into an input/textarea/contenteditable.
  //   "/" → focus the current page's [data-search-input]
  //   "n" → navigate to /publish
  // Both `setPaletteOpen` (from `useState`) and `navigate` (from `useNavigate`)
  // are stable across renders, so an empty dependency array is correct.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (
        (e.metaKey || e.ctrlKey) &&
        e.key.toLowerCase() === 'k' &&
        !e.shiftKey &&
        !e.altKey
      ) {
        e.preventDefault()
        setPaletteOpen((v) => !v)
        return
      }

      const target = e.target as HTMLElement | null
      const tag = target?.tagName?.toLowerCase()
      const isTyping =
        tag === 'input' || tag === 'textarea' || target?.isContentEditable === true
      if (isTyping) return

      if (e.key === '/' && !e.metaKey && !e.ctrlKey && !e.altKey && !e.shiftKey) {
        e.preventDefault()
        const el = document.querySelector<HTMLInputElement>('[data-search-input]')
        el?.focus()
        return
      }

      if (e.key === 'n' && !e.metaKey && !e.ctrlKey && !e.altKey && !e.shiftKey) {
        e.preventDefault()
        navigate('/publish')
        return
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- setPaletteOpen and navigate are both stable
  }, [])

  // Top header omits the page label — sidebar nav + in-content PageHeader already convey identity (avoids triple "账号管理" on the Accounts route).
  if (isMobile) {
    return (
      <div className="flex flex-col min-h-screen bg-background">
        <header className="sticky top-0 z-50 flex h-14 items-center justify-between border-b bg-background/80 backdrop-blur-xl px-4">
          <div className="flex items-center gap-3">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-foreground">
              <Zap className="h-3.5 w-3.5 text-background" />
            </div>
          </div>
          <ThemeToggle />
        </header>

        <main className="flex-1 p-4 pb-20">
          <Routes location={location}>
            <Route path="/" element={<AccountsPage />} />
            <Route path="/publish" element={<PublishPage />} />
            <Route path="/logs" element={<LogsPage />} />
            <Route path="/tasks" element={<TasksPage />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>

        <FloatingLogs />

        <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />

        <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-border/30 bg-background/80 backdrop-blur-xl">
          <div className="flex items-center justify-around py-2 px-2 pb-[max(0.5rem,env(safe-area-inset-bottom))]">
            {navItems.map((item) => {
              const active = location.pathname === item.path
              const Icon = item.icon
              return (
                <Link
                  key={item.path}
                  className={cn(
                    "flex flex-col items-center gap-1 px-3 py-1.5 text-[10px] transition-all duration-150 rounded-xl",
                    active
                      ? "text-foreground"
                      : "text-muted-foreground"
                  )}
                  to={item.path}
                >
                  <div className={cn(
                    "flex h-9 w-9 items-center justify-center rounded-xl transition-all duration-150",
                    active
                      ? "bg-foreground text-background shadow-sm"
                      : "bg-muted/50"
                  )}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <span className={cn(active ? "font-medium" : "")}>{item.label}</span>
                </Link>
              )
            })}
          </div>
        </nav>
      </div>
    )
  }

  const isCollapsed = sidebarCollapsed
  const isTabletMode = shouldAutoCollapse

  return (
    <div className="flex min-h-screen bg-background">
      {isTabletMode && !isCollapsed && (
        <div
          className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm transition-all"
          onClick={toggleSidebar}
        />
      )}

      <aside
        ref={sidebarRef}
        className={cn(
          "flex flex-col border-r border-border/40 transition-all duration-300 ease-[cubic-bezier(0.4,0,0.2,1)] bg-sidebar",
          isCollapsed ? "w-[60px]" : "w-[220px]",
          isTabletMode && !isCollapsed && "fixed inset-y-0 left-0 z-50 shadow-2xl"
        )}
      >
        {/* Logo */}
        <div className={cn(
          "flex items-center h-14 border-b border-border/30",
          isCollapsed ? "justify-center px-2" : "px-4 gap-3"
        )}>
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-foreground text-background flex-shrink-0">
            <Zap className="h-4 w-4" strokeWidth={2.5} />
          </div>
          {!isCollapsed && (
            <div className="flex flex-col min-w-0 flex-1">
              <span className="text-[13px] font-semibold tracking-tight text-foreground">SAU Shell</span>
              <span className="text-[10px] text-muted-foreground/60">Social Auto Upload</span>
            </div>
          )}
          {!isCollapsed && (
            <button
              className="h-7 w-7 flex items-center justify-center rounded-md text-muted-foreground hover:text-foreground hover:bg-foreground/5 transition-colors"
              onClick={toggleSidebar}
              aria-label="Collapse sidebar"
            >
              <PanelLeftClose className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Collapse button */}
        {isCollapsed && (
          <div className="flex justify-center py-3">
            <button
              className="h-8 w-8 flex items-center justify-center rounded-lg text-muted-foreground hover:text-foreground hover:bg-foreground/5 transition-colors"
              onClick={toggleSidebar}
              aria-label="Expand sidebar"
            >
              <PanelLeftOpen className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Navigation */}
        <ScrollArea className="flex-1 py-3">
          <nav className={cn("flex flex-col", isCollapsed ? "px-2" : "px-3")}>
            {/* Section label */}
            {!isCollapsed && (
              <div className="px-2 mb-1.5">
                <span className="text-[10px] font-medium text-muted-foreground/50 uppercase tracking-widest">
                  导航
                </span>
              </div>
            )}
            <div className="flex flex-col gap-0.5">
              {navItems.map((item) => {
                const active = location.pathname === item.path
                const Icon = item.icon
                return (
                  <Link
                    key={item.path}
                    className={cn(
                      "group relative flex items-center rounded-lg text-[13px] font-medium transition-all duration-150",
                      isCollapsed ? "justify-center px-2 py-2 mx-0.5" : "px-2.5 py-2 mx-0.5 gap-2.5",
                      active
                        ? "bg-foreground/[0.08] text-foreground"
                        : "text-muted-foreground hover:text-foreground hover:bg-foreground/[0.04]",
                    )}
                    to={item.path}
                    onClick={isTabletMode ? () => setSidebarCollapsed(true) : undefined}
                    data-tour={item.path === '/publish' ? 'nav-publish' : undefined}
                  >
                    {/* Active indicator */}
                    {active && (
                      <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-4 rounded-r-full bg-foreground" />
                    )}
                    <Icon className={cn(
                      "h-4 w-4 shrink-0 transition-colors duration-150",
                      active ? "text-foreground" : "text-muted-foreground group-hover:text-foreground"
                    )} />
                    {!isCollapsed && (
                      <span className={cn(
                        "truncate transition-colors duration-150",
                        active && "font-medium"
                      )}>
                        {item.label}
                      </span>
                    )}
                    {/* Tooltip for collapsed state */}
                    {isCollapsed && (
                      <div className="absolute left-full ml-3 px-2.5 py-1.5 rounded-lg bg-foreground text-background text-xs font-medium opacity-0 group-hover:opacity-100 pointer-events-none transition-all duration-150 whitespace-nowrap z-50 shadow-lg scale-95 group-hover:scale-100">
                        {item.label}
                        <div className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-1 w-2 h-2 bg-foreground rotate-45" />
                      </div>
                    )}
                  </Link>
                )
              })}
            </div>
          </nav>
        </ScrollArea>

        {/* Footer */}
        <div className={cn(
          "border-t border-border/30",
          isCollapsed ? "p-2" : "p-3"
        )}>
          {isCollapsed ? (
            <div className="flex flex-col items-center gap-2">
              <div className="h-8 w-8 rounded-full bg-muted/50 flex items-center justify-center">
                <span className="text-xs font-medium text-muted-foreground">S</span>
              </div>
              <ThemeToggle />
              <button
                onClick={resetOnboardingTour}
                className="h-8 w-8 flex items-center justify-center rounded-lg text-muted-foreground hover:text-foreground hover:bg-foreground/5 transition-colors"
                aria-label="重新引导"
                title="重新引导"
              >
                <HelpCircle className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2.5 px-1">
              <div className="h-8 w-8 rounded-full bg-muted/50 flex items-center justify-center flex-shrink-0">
                <span className="text-xs font-medium text-muted-foreground">S</span>
              </div>
              <div className="flex flex-col min-w-0 flex-1">
                <span className="text-xs font-medium text-foreground truncate">SAU Admin</span>
                <span className="text-[10px] text-muted-foreground/60">v1.0.0</span>
              </div>
              <button
                onClick={resetOnboardingTour}
                className="h-7 px-2 flex items-center gap-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-foreground/5 transition-colors text-xs"
                aria-label="重新引导"
                title="重新触发新手引导"
              >
                <HelpCircle className="h-3.5 w-3.5" />
                <span>重新引导</span>
              </button>
              <ThemeToggle />
            </div>
          )}
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex flex-1 flex-col min-w-0">
        <header className="flex h-14 items-center justify-end gap-2 border-b border-border/50 bg-background/80 backdrop-blur-xl px-6">
          {isTabletMode && (
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={toggleSidebar} aria-label="Toggle sidebar">
              <Menu className="h-4 w-4" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setPaletteOpen(true)}
            className="gap-2 text-muted-foreground hover:text-foreground btn-elegant"
          >
            <Search className="h-3.5 w-3.5" />
            <span>搜索</span>
            <kbd className="ml-1 hidden sm:inline-flex h-5 items-center px-1.5 rounded border border-border/40 bg-muted/40 text-[10px] font-mono text-muted-foreground">
              ⌘K
            </kbd>
          </Button>
        </header>

        <main className="flex-1 overflow-auto">
          <Routes location={location}>
            <Route path="/" element={<AccountsPage />} />
            <Route path="/publish" element={<PublishPage />} />
            <Route path="/logs" element={<LogsPage />} />
            <Route path="/tasks" element={<TasksPage />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
      </div>
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
      <FloatingLogs />
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider defaultTheme="system" storageKey="sau-ui-theme">
        <TooltipProvider>
          <ToastProvider>
            <OnboardingTour>
              <ErrorBoundary>
                <AppShell />
              </ErrorBoundary>
            </OnboardingTour>
          </ToastProvider>
        </TooltipProvider>
      </ThemeProvider>
    </BrowserRouter>
  )
}

export default App
