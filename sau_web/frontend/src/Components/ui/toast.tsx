import * as React from "react"
import { X, CheckCircle, XCircle, AlertTriangle, Info } from "lucide-react"
import { cn } from "@/lib/utils"
import { toneBorderClass, toneChipClasses } from "@/lib/tone"

type ToastType = "default" | "success" | "error" | "warning" | "info"

interface Toast {
  id: string
  message: string
  type: ToastType
}

interface ToastContextType {
  toasts: Toast[]
  addToast: (message: string, type?: ToastType) => void
  removeToast: (id: string) => void
}

const ToastContext = React.createContext<ToastContextType | undefined>(undefined)

const EXIT_DURATION = 300 // ms, matches the CSS animation duration

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<Toast[]>([])
  const [exitingIds, setExitingIds] = React.useState<Set<string>>(new Set())
  const timersRef = React.useRef<Set<ReturnType<typeof setTimeout>>>(new Set())

  const removeToast = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
    setExitingIds((prev) => {
      const next = new Set(prev)
      next.delete(id)
      return next
    })
  }, [])

  const dismissToast = React.useCallback((id: string) => {
    setExitingIds((prev) => new Set(prev).add(id))
    const timer = setTimeout(() => {
      timersRef.current.delete(timer)
      removeToast(id)
    }, EXIT_DURATION)
    timersRef.current.add(timer)
  }, [removeToast])

  const addToast = React.useCallback((message: string, type: ToastType = "default") => {
    const id = Math.random().toString(36).substring(2, 9)
    setToasts((prev) => [...prev, { id, message, type }])
    const timer = setTimeout(() => {
      timersRef.current.delete(timer)
      dismissToast(id)
    }, 3000)
    timersRef.current.add(timer)
  }, [dismissToast])

  React.useEffect(() => {
    return () => {
      timersRef.current.forEach((t) => clearTimeout(t))
      timersRef.current.clear()
    }
  }, [])

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <ToastContainer toasts={toasts} exitingIds={exitingIds} dismissToast={dismissToast} />
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = React.useContext(ToastContext)
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider")
  }
  return context
}

function ToastContainer({
  toasts,
  exitingIds,
  dismissToast,
}: {
  toasts: Toast[]
  exitingIds: Set<string>
  dismissToast: (id: string) => void
}) {
  return (
    <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2">
      {toasts.map((toast) => (
        <ToastItem
          key={toast.id}
          toast={toast}
          exiting={exitingIds.has(toast.id)}
          onClose={() => dismissToast(toast.id)}
        />
      ))}
    </div>
  )
}

function ToastIcon({ type }: { type: ToastType }) {
  const iconClass = "h-5 w-5 shrink-0"
  switch (type) {
    case "success":
      return <CheckCircle className={iconClass} />
    case "error":
      return <XCircle className={iconClass} />
    case "warning":
      return <AlertTriangle className={iconClass} />
    case "info":
      return <Info className={iconClass} />
    default:
      return null
  }
}

function ToastItem({
  toast,
  exiting,
  onClose,
}: {
  toast: Toast
  exiting: boolean
  onClose: () => void
}) {
  // DESIGN.md status tokens composed via `@/lib/tone`. Shared with
  // <Badge variant="..."> and <Alert variant="...">: a single tonal
  // vocabulary across the toast / badge / alert primitive surface.
  const typeStyles: Record<ToastType, string> = {
    default: "bg-background border",
    success: cn(toneChipClasses("success"), toneBorderClass("success")),
    error: cn(toneChipClasses("error"), toneBorderClass("error")),
    warning: cn(toneChipClasses("warning"), toneBorderClass("warning")),
    info: cn(toneChipClasses("info"), toneBorderClass("info")),
  }

  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-lg border p-4 shadow-lg duration-300",
        exiting
          ? "animate-out fade-out slide-out-to-right-full"
          : "animate-in slide-in-from-right-full fade-in",
        typeStyles[toast.type]
      )}
    >
      <ToastIcon type={toast.type} />
      <span className="text-sm flex-1">{toast.message}</span>
      <button
        onClick={onClose}
        className="opacity-70 hover:opacity-100 transition-opacity shrink-0"
        aria-label="关闭通知"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  )
}
