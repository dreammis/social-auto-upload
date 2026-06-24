import type { ReactNode } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { Sparkles, X } from 'lucide-react'

interface MobileAiDrawerProps {
  /** Whether the drawer is open. The drawer is mounted in the DOM only when this is true (via AnimatePresence). */
  open: boolean
  /** Called when the user taps the backdrop, the close button, or presses Escape-equivalent gesture. */
  onClose: () => void
  children: ReactNode
}

/**
 * Bottom-sheet modal for the AI assistant on viewports below the lg breakpoint.
 *
 * Mirrors the original `AiPanel` mobile UX (slide-up, rounded top corners,
 * partial backdrop band above the content so the user keeps page context).
 * On desktop the inline `PublishAiSidebar` takes over and this component is
 * never rendered.
 *
 * Note: we render Motion-based markup here rather than the Radix Sheet so
 * that we can keep the exact visual (and timing) of the previous mobile
 * drawer — the Sheet's built-in close-button conflicts with our custom
 * header bar at the top of the sheet.
 */
export function MobileAiDrawer({ open, onClose, children }: MobileAiDrawerProps) {
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            key="mobile-ai-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 bg-black/60"
            onClick={onClose}
            data-testid="mobile-ai-backdrop"
          />
          <motion.div
            key="mobile-ai-panel"
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ duration: 0.28, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="fixed inset-x-0 top-4 bottom-0 z-50 bg-background rounded-t-2xl shadow-2xl flex flex-col"
            data-testid="mobile-ai-panel"
            role="dialog"
            aria-modal="true"
            aria-label="AI 助手"
          >
            {/* Header — slim, matches desktop right-column chrome */}
            <div className="flex-shrink-0 flex items-center justify-between px-4 h-11 border-b border-border/60">
              <span className="flex items-center gap-1.5 text-[13px] font-semibold tracking-tight">
                <Sparkles className="h-3.5 w-3.5 text-primary" />
                AI 助手
              </span>
              <button
                onClick={onClose}
                className="p-1.5 rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                data-testid="mobile-ai-close"
                aria-label="关闭"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            {/* Scrollable content */}
            <div className="flex-1 overflow-y-auto">{children}</div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
