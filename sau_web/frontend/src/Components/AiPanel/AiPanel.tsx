import { useState, useRef, useCallback, useEffect, type ReactNode } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { X } from 'lucide-react'
import { AiPanelToolbar } from './AiPanelToolbar'

const COLLAPSED_HEIGHT = 48

/**
 * @deprecated Kept for legacy compatibility. The publish page now uses the
 * inline `PublishAiSidebar` on md+ and `MobileAiDrawer` (which mirrors only
 * the mobile modal portion of this component) below md. New code should
 * compose `AiSidebar` directly inside `PublishAiSidebar` / `MobileAiDrawer`
 * with `useMobileDrawer` for open state.
 *
 * Tests in `AiPanel.test.tsx` still cover this component until the
 * deprecation window closes.
 */
const MIN_EXPANDED_HEIGHT = 220
const MAX_HEIGHT_RATIO = 0.72
const MOBILE_BREAKPOINT = 640

interface AiPanelProps {
  children: ReactNode
  defaultExpanded?: boolean
  onQuickGenerate?: () => void
  isGenerating?: boolean
}

export function AiPanel({
  children,
  defaultExpanded = false,
  onQuickGenerate,
  isGenerating,
}: AiPanelProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)
  const [panelHeight, setPanelHeight] = useState(420)
  const [isMobile, setIsMobile] = useState(
    typeof window !== 'undefined' ? window.innerWidth < MOBILE_BREAKPOINT : false,
  )
  const isDragging = useRef(false)
  const startY = useRef(0)
  const startHeight = useRef(0)
  const maxHeight = useRef(
    typeof window !== 'undefined' ? window.innerHeight * MAX_HEIGHT_RATIO : 500,
  )

  // Detect mobile breakpoint on resize
  useEffect(() => {
    const handler = () => {
      setIsMobile(window.innerWidth < MOBILE_BREAKPOINT)
      maxHeight.current = window.innerHeight * MAX_HEIGHT_RATIO
      setPanelHeight((h) => Math.min(h, maxHeight.current))
    }
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [])

  // Drag handler
  const handleDragStart = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault()
      isDragging.current = true
      startY.current = e.clientY
      startHeight.current = panelHeight
      document.body.style.cursor = 'ns-resize'
      document.body.style.userSelect = 'none'
    },
    [panelHeight],
  )

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging.current) return
      const delta = startY.current - e.clientY
      const newHeight = Math.max(
        MIN_EXPANDED_HEIGHT,
        Math.min(maxHeight.current, startHeight.current + delta),
      )
      setPanelHeight(newHeight)
    }

    const handleMouseUp = () => {
      if (isDragging.current) {
        isDragging.current = false
        document.body.style.cursor = ''
        document.body.style.userSelect = ''
      }
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [])

  const toggle = useCallback(() => {
    setIsExpanded((v) => !v)
  }, [])

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40">
      {/* Toolbar — always visible */}
      <div
        className="border-t bg-background/95 backdrop-blur-sm shadow-lg flex items-center"
        style={{ height: COLLAPSED_HEIGHT }}
      >
        <AiPanelToolbar
          isExpanded={isExpanded}
          onToggle={toggle}
          onQuickGenerate={onQuickGenerate}
          isGenerating={isGenerating}
        />
      </div>

      {/* Desktop: bottom drawer (always mounted so state is preserved) */}
      {!isMobile && (
      <motion.div
        initial={false}
        animate={{
          height: isExpanded ? panelHeight : 0,
          opacity: isExpanded ? 1 : 0,
        }}
        transition={{ duration: 0.25, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="border-t bg-background shadow-xl flex flex-col overflow-hidden"
      >
        {/* Drag handle */}
        <div
          className="flex-shrink-0 flex items-center justify-center cursor-ns-resize hover:bg-muted/30 transition-colors group py-1.5"
          onMouseDown={handleDragStart}
        >
          <div className="w-12 h-1 rounded-full bg-muted-foreground/20 group-hover:bg-muted-foreground/40 transition-colors" />
        </div>

        {/* Scrollable content area */}
        <div className="flex-1 overflow-y-auto px-4 pb-4">
          {children}
        </div>
      </motion.div>
      )}

      {/* Mobile: full-screen Modal overlay */}
      <AnimatePresence>
        {isMobile && isExpanded && (
          <>
            <motion.div
              key="modal-backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 z-50 bg-black/60"
              onClick={toggle}
              data-testid="modal-backdrop"
            />
            <motion.div
              key="modal-panel"
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              transition={{ duration: 0.25, ease: [0.25, 0.46, 0.45, 0.94] }}
              className="fixed inset-x-0 top-8 bottom-0 z-50 bg-background rounded-t-2xl shadow-2xl flex flex-col"
              data-testid="modal-panel"
            >
              {/* Header with close button */}
              <div className="flex-shrink-0 flex items-center justify-between px-4 py-3 border-b">
                <span className="text-sm font-semibold">AI 内容生成</span>
                <button
                  onClick={toggle}
                  className="p-1 rounded-md hover:bg-muted transition-colors"
                  data-testid="modal-close"
                  aria-label="关闭"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
              {/* Content */}
              <div className="flex-1 overflow-y-auto px-4 pb-4" data-testid="modal-content">
                {children}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}
