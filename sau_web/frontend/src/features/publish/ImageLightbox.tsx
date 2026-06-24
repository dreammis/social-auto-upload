import { memo, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { ChevronLeft, ChevronRight, X } from 'lucide-react'

type ImageLightboxProps = {
  imageUrls: string[]
  /** null = closed; 0..n = which image is focused */
  openIndex: number | null
  onClose: () => void
  onPrev: () => void
  onNext: () => void
}

/**
 * Full-screen modal viewer. Triggered by clicking a thumbnail in the parent
 * form. Parent owns openIndex state so the URL array and the active index
 * are co-located with the rest of the upload lifecycle (add/remove).
 *
 * Keystroke handling:
 *   - Esc closes
 *   - ← / → navigate prev/next (clamped by parent callbacks)
 */
export const ImageLightbox = memo(function ImageLightbox({
  imageUrls,
  openIndex,
  onClose,
  onPrev,
  onNext,
}: ImageLightboxProps) {
  const overlayRef = useRef<HTMLDivElement>(null)

  // Focus on open so keyboard navigation works immediately.
  useEffect(() => {
    if (openIndex !== null) {
      requestAnimationFrame(() => overlayRef.current?.focus())
    }
  }, [openIndex])

  return (
    <AnimatePresence>
      {openIndex !== null && (
        <motion.div
          ref={overlayRef}
          tabIndex={-1}
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center outline-none"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          onClick={onClose}
          onKeyDown={(e) => {
            if (e.key === 'Escape') onClose()
            if (e.key === 'ArrowLeft') onPrev()
            if (e.key === 'ArrowRight') onNext()
          }}
        >
          <button
            className="absolute top-4 right-4 h-10 w-10 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors z-10"
            onClick={onClose}
            aria-label="关闭预览"
          >
            <X className="h-5 w-5" />
          </button>

          <div className="absolute top-4 left-1/2 -translate-x-1/2 px-3 py-1.5 rounded-full bg-white/10 text-white text-sm font-medium backdrop-blur-sm">
            {openIndex + 1} / {imageUrls.length}
          </div>

          {openIndex > 0 && (
            <button
              className="absolute left-4 top-1/2 -translate-y-1/2 h-12 w-12 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors"
              onClick={(e) => {
                e.stopPropagation()
                onPrev()
              }}
              aria-label="上一张"
            >
              <ChevronLeft className="h-6 w-6" />
            </button>
          )}

          {openIndex < imageUrls.length - 1 && (
            <button
              className="absolute right-4 top-1/2 -translate-y-1/2 h-12 w-12 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors"
              onClick={(e) => {
                e.stopPropagation()
                onNext()
              }}
              aria-label="下一张"
            >
              <ChevronRight className="h-6 w-6" />
            </button>
          )}

          <motion.img
            key={openIndex}
            src={imageUrls[openIndex]}
            alt={`图片 ${openIndex + 1}`}
            className="max-h-[85vh] max-w-[90vw] object-contain rounded-lg shadow-2xl select-none"
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 350, damping: 30 }}
            onClick={(e) => e.stopPropagation()}
          />
        </motion.div>
      )}
    </AnimatePresence>
  )
})
