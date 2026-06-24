import { memo, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import {
  Alert,
  AlertDescription,
  AlertTitle,
  Button,
} from '@/components/ui/index'
import { CheckCircle } from 'lucide-react'
import type { SubmitSuccessInfo } from '@/stores/publishStore'

const springTransition = { type: 'spring' as const, stiffness: 400, damping: 30 }

type PublishSuccessBannerProps = {
  info: SubmitSuccessInfo | null
  onGoToTasks: () => void
}

/**
 * Top-of-page success alert with a spring entrance. Memoized so that mode
 * toggles inside PublishPage's tabs (which trigger parent re-renders
 * unrelated to a recent submission) don't re-trigger the alert's animation.
 */
export const PublishSuccessBanner = memo(function PublishSuccessBanner({
  info,
  onGoToTasks,
}: PublishSuccessBannerProps) {
  // ponytail: fire confetti once when info appears. ref gate prevents
  // re-trigger on remount (e.g. navigating away and back).
  const firedRef = useRef(false)
  useEffect(() => {
    if (!info || firedRef.current) return
    firedRef.current = true
    const duration = 1500
    const end = Date.now() + duration
    import('canvas-confetti').then(({ default: confetti }) => {
      const frame = () => {
        confetti({ particleCount: 3, angle: 60, spread: 55, origin: { x: 0, y: 0.6 } })
        confetti({ particleCount: 3, angle: 120, spread: 55, origin: { x: 1, y: 0.6 } })
        if (Date.now() < end) requestAnimationFrame(frame)
      }
      frame()
    })
  }, [info])

  return (
    <AnimatePresence>
      {info && (
        <motion.div
          initial={{ opacity: 0, y: -24, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -12, scale: 0.97 }}
          transition={springTransition}
        >
          <Alert variant="success">
            <CheckCircle className="h-4 w-4" />
            <AlertTitle>提交成功</AlertTitle>
            <AlertDescription className="flex items-center justify-between">
              <span>
                <strong>{info.count}</strong> 个{info.mode}上传任务已提交！
              </span>
              <Button size="sm" onClick={onGoToTasks}>
                查看任务状态 →
              </Button>
            </AlertDescription>
          </Alert>
        </motion.div>
      )}
    </AnimatePresence>
  )
})
