import * as React from "react"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"

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

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<Toast[]>([])

  const addToast = React.useCallback((message: string, type: ToastType = "default") => {
    const id = Math.random().toString(36).substring(2, 9)
    setToasts((prev) => [...prev, { id, message, type }])
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 3000)
  }, [])

  const removeToast = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <ToastContainer toasts={toasts} removeToast={removeToast} />
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

function ToastContainer({ toasts, removeToast }: { toasts: Toast[]; removeToast: (id: string) => void }) {
  return (
    <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onClose={() => removeToast(toast.id)} />
      ))}
    </div>
  )
}

function ToastItem({ toast, onClose }: { toast: Toast; onClose: () => void }) {
  const typeStyles: Record<ToastType, string> = {
    default: "bg-background border",
    success: "bg-emerald-50 border-emerald-200 text-emerald-800 dark:bg-emerald-950 dark:border-emerald-800 dark:text-emerald-200",
    error: "bg-red-50 border-red-200 text-red-800 dark:bg-red-950 dark:border-red-800 dark:text-red-200",
    warning: "bg-amber-50 border-amber-200 text-amber-800 dark:bg-amber-950 dark:border-amber-800 dark:text-amber-200",
    info: "bg-blue-50 border-blue-200 text-blue-800 dark:bg-blue-950 dark:border-blue-800 dark:text-blue-200",
  }

  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-lg border p-4 shadow-lg animate-in slide-in-from-right-full fade-in duration-300",
        typeStyles[toast.type]
      )}
    >
      <span className="text-sm">{toast.message}</span>
      <button onClick={onClose} className="ml-auto opacity-70 hover:opacity-100">
        <X className="h-4 w-4" />
      </button>
    </div>
  )
}

// Legacy API compatibility
export const message = {
  success: (msg: string) => {
    const event = new CustomEvent('toast', { detail: { message: msg, type: 'success' } })
    window.dispatchEvent(event)
  },
  error: (msg: string) => {
    const event = new CustomEvent('toast', { detail: { message: msg, type: 'error' } })
    window.dispatchEvent(event)
  },
  warning: (msg: string) => {
    const event = new CustomEvent('toast', { detail: { message: msg, type: 'warning' } })
    window.dispatchEvent(event)
  },
  info: (msg: string) => {
    const event = new CustomEvent('toast', { detail: { message: msg, type: 'info' } })
    window.dispatchEvent(event)
  },
}
