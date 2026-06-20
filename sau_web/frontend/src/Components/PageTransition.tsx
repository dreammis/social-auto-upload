import { type ReactNode } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { useLocation } from 'react-router-dom'

type PageTransitionProps = {
  children: ReactNode
}

const pageVariants = {
  initial: {
    opacity: 0,
    y: 6,
  },
  animate: {
    opacity: 1,
    y: 0,
  },
  exit: {
    opacity: 0,
    y: -4,
  },
}

const pageTransition = {
  duration: 0.12,
  ease: [0.25, 0.1, 0.25, 1] as [number, number, number, number],
}

/**
 * Wraps route content with AnimatePresence for smooth route transitions.
 * Uses location.pathname as the key so AnimatePresence detects route changes.
 * Uses fast tween animation (~120ms) for snappy feel.
 */
export function PageTransition({ children }: PageTransitionProps) {
  const location = useLocation()

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        variants={pageVariants}
        initial="initial"
        animate="animate"
        exit="exit"
        transition={pageTransition}
        style={{ willChange: 'transform, opacity' }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  )
}
