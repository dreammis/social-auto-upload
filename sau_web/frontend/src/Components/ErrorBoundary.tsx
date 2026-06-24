import React from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { toneBgClass, toneTextClass } from '@/lib/tone'

interface Props {
  children: React.ReactNode
}

interface State {
  hasError: boolean
  error?: Error
}

// Linear DESIGN.md — error fallback renders inside the same card/button
// system as the rest of the app, so a crash doesn't drop the visual floor
// to bare HTML. Error text is monospace (JetBrains Mono via .font-mono) and
// error tone uses the status-error token (composed via `@/lib/tone`).
export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo)
  }

  handleReload = () => {
    this.setState({ hasError: false, error: undefined })
    window.location.reload()
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-background p-6">
          <div className="card-refined w-full max-w-md p-8 text-center">
            <div className={cn("mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-2xl", toneBgClass('error'))}>
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className={cn("h-6 w-6", toneTextClass('error'))}
                aria-hidden
              >
                <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
            </div>
            <h2 className="text-lg font-semibold tracking-tight text-foreground">
              页面出错了
            </h2>
            <p className="mt-1.5 text-sm text-muted-foreground">
              应用遇到了一个错误，刷新页面通常可以解决。
            </p>
            {this.state.error && (
              <pre className="mt-4 max-h-32 overflow-auto rounded-lg bg-muted p-3 text-left font-mono text-xs text-muted-foreground">
                {this.state.error.message}
              </pre>
            )}
            <div className="mt-6 flex items-center justify-center gap-2">
              <Button onClick={this.handleReload}>刷新页面</Button>
            </div>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
