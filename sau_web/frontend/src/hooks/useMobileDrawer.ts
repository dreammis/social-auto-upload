import { useCallback, useEffect, useState } from 'react'

/** Below this width the drawer behaves like a mobile modal. Default 768 (md breakpoint). */
const DEFAULT_BREAKPOINT = 768

interface UseMobileDrawerOptions {
  /** Below this width the drawer behaves like a mobile modal. Default 768. */
  breakpoint?: number
}

interface UseMobileDrawerResult {
  /** True when the viewport is below `breakpoint`. */
  isMobile: boolean
  /** True when the drawer is open. Only meaningful when `isMobile` is true. */
  isOpen: boolean
  /** Open the drawer. */
  open: () => void
  /** Close the drawer. */
  close: () => void
  /** Toggle the drawer. */
  toggle: () => void
}

/**
 * Tracks viewport-vs-breakpoint + drawer open state, and auto-collapses the
 * drawer when the user resizes from mobile to desktop so the sticky
 * PublishAiSidebar takes over.
 *
 * Extracted from the old `AiPanel` after the publish-page switched to a
 * CSS-Grid layout with the AI sidebar as an inline right column on desktop.
 */
export function useMobileDrawer({
  breakpoint = DEFAULT_BREAKPOINT,
}: UseMobileDrawerOptions = {}): UseMobileDrawerResult {
  const [isOpen, setIsOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(
    typeof window !== 'undefined' ? window.innerWidth < breakpoint : false,
  )

  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth < breakpoint)
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [breakpoint])

  // Auto-collapse when crossing the breakpoint into desktop.
  useEffect(() => {
    if (!isMobile && isOpen) setIsOpen(false)
  }, [isMobile, isOpen])

  const open = useCallback(() => setIsOpen(true), [])
  const close = useCallback(() => setIsOpen(false), [])
  const toggle = useCallback(() => setIsOpen((v) => !v), [])

  return { isMobile, isOpen, open, close, toggle }
}
