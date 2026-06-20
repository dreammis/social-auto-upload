import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react'
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import {
  BarChartOutlined,
  FileTextOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  ProjectOutlined,
  SendOutlined,
  TeamOutlined,
} from '@ant-design/icons'
import FloatingLogs from './Components/FloatingLogs'
import { PageLoading } from './Components/PageLoading'
import { PageTransition } from './Components/PageTransition'
import { ThemeToggle } from './Components/ThemeToggle'
import './App.css'
import './index.css'

// Lazy-loaded page components — split into separate chunks
const AccountsPage = lazy(() => import('./Pages/AccountsPage'))
const PublishPage = lazy(() => import('./Pages/PublishPage'))
const LogsPage = lazy(() => import('./Pages/LogsPage'))
const TasksPage = lazy(() => import('./Pages/TasksPage'))
const ProposalsPage = lazy(() => import('./Pages/ProposalsPage'))

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
  { path: '/', label: '账号管理', icon: <TeamOutlined /> },
  { path: '/publish', label: '发布中心', icon: <SendOutlined /> },
  { path: '/proposals', label: '变更提案', icon: <ProjectOutlined /> },
  { path: '/logs', label: '运行日志', icon: <FileTextOutlined /> },
  { path: '/tasks', label: '任务列表', icon: <BarChartOutlined /> },
]

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

  // Auto-collapse on tablet, auto-expand on desktop (only on actual viewport changes)
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

  const current = navItems.find((item) => item.path === location.pathname)
  const pageTitle = current?.label ?? 'SAU Shell'

  // ---- Mobile layout ----
  if (isMobile) {
    return (
      <div className="app-shell app-shell-mobile">
        <header className="app-mobile-header" style={{ background: '#001529', color: '#fff' }}>
          <div className="app-mobile-header-title">
            <span style={{ fontSize: 14, opacity: 0.7 }}>{current?.icon}</span>
            <span>{pageTitle}</span>
          </div>
          <ThemeToggle />
        </header>

        <main className="app-main app-mobile-main" style={{ background: '#f5f5f5' }}>
          <PageTransition>
            <Suspense fallback={<PageLoading />}>
              <Routes location={location}>
                <Route path="/" element={<AccountsPage />} />
                <Route path="/publish" element={<PublishPage />} />
                <Route path="/logs" element={<LogsPage />} />
                <Route path="/tasks" element={<TasksPage />} />
                <Route path="/proposals" element={<ProposalsPage />} />
              </Routes>
            </Suspense>
          </PageTransition>
        </main>

        <FloatingLogs />

        <nav className="app-mobile-nav" style={{ background: '#fff', borderTopColor: '#e8e8e8' }}>
          {navItems.map((item) => {
            const active = location.pathname === item.path
            return (
              <Link
                key={item.path}
                className="app-mobile-nav-link"
                to={item.path}
                style={{
                  color: active ? '#1677ff' : '#999',
                  fontWeight: active ? 600 : 400,
                  background: active ? 'rgba(22,119,255,0.08)' : 'transparent',
                }}
              >
                <span className="nav-icon">{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            )
          })}
        </nav>
      </div>
    )
  }

  // ---- Desktop / Tablet layout ----
  const isCollapsed = sidebarCollapsed
  const isTabletMode = shouldAutoCollapse

  return (
    <div className="app-shell" style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Backdrop overlay for tablet mode when sidebar is expanded */}
      {isTabletMode && !isCollapsed && (
        <div
          className="sidebar-backdrop visible"
          onClick={toggleSidebar}
        />
      )}

      {/* Sidebar */}
      <aside
        ref={sidebarRef}
        className={`app-sidebar${isCollapsed ? ' collapsed' : ' expanded'}`}
        style={{
          background: '#001529',
          color: '#fff',
          // On tablet, position sidebar as fixed overlay when expanded
          ...(isTabletMode && !isCollapsed
            ? { position: 'fixed', left: 0, top: 0, bottom: 0, zIndex: 45 }
            : {}),
        }}
      >
        {/* Logo + collapse toggle */}
        <div className="app-sidebar-logo" style={{ justifyContent: isCollapsed ? 'center' : undefined }}>
          <div className="app-sidebar-logo-icon">S</div>
          {!isCollapsed && <div className="app-sidebar-logo-text">SAU Shell</div>}
          <button
            className="app-sidebar-toggle"
            onClick={toggleSidebar}
            title={isCollapsed ? '展开侧边栏' : '折叠侧边栏'}
            style={isCollapsed ? { margin: '0 auto' } : { marginLeft: 'auto' }}
          >
            {isCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          </button>
        </div>

        {/* Navigation */}
        <div className="app-nav-section">
          {navItems.map((item) => {
            const active = location.pathname === item.path
            return (
              <Link
                key={item.path}
                className={`app-nav-link${active ? ' active' : ''}`}
                to={item.path}
                onClick={isTabletMode ? () => setSidebarCollapsed(true) : undefined}
              >
                <span className="nav-icon">{item.icon}</span>
                {!isCollapsed && <span className="nav-label">{item.label}</span>}
              </Link>
            )
          })}
        </div>

        {/* Footer */}
        <div className="app-sidebar-footer" style={{ flexDirection: isCollapsed ? 'column' : 'row' }}>
          {!isCollapsed && <span className="footer-version">v1.0</span>}
          <ThemeToggle />
        </div>
      </aside>

      {/* Right side: header + content */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          flex: 1,
          minWidth: 0,
          ...(isTabletMode && !isCollapsed ? { marginLeft: 64 } : {}),
        }}
      >
        {/* Top header bar */}
        <header
          className="app-header"
          style={{
            background: '#fff',
            borderColor: '#e8e8e8',
          }}
        >
          <div className="app-header-title">
            {/* Sidebar toggle for tablet mode */}
            {isTabletMode && (
              <button
                className="app-sidebar-toggle"
                onClick={toggleSidebar}
                title={isCollapsed ? '展开侧边栏' : '折叠侧边栏'}
                style={{
                  color: '#555',
                  background: 'transparent',
                  marginRight: 4,
                  width: 32,
                  height: 32,
                }}
              >
                {isCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              </button>
            )}
            <span style={{ color: '#1677ff' }}>{current?.icon}</span>
            <span>{pageTitle}</span>
          </div>
          <div className="app-header-actions">
            <ThemeToggle />
          </div>
        </header>

        {/* Main content */}
        <main className="app-content" style={{ background: '#f5f5f5' }}>
          <PageTransition>
            <Suspense fallback={<PageLoading />}>
              <Routes location={location}>
                <Route path="/" element={<AccountsPage />} />
                <Route path="/publish" element={<PublishPage />} />
                <Route path="/logs" element={<LogsPage />} />
                <Route path="/tasks" element={<TasksPage />} />
                <Route path="/proposals" element={<ProposalsPage />} />
              </Routes>
            </Suspense>
          </PageTransition>
        </main>
      </div>
      <FloatingLogs />
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  )
}

export default App
