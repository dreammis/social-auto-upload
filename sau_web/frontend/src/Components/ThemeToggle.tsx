import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { Sun, Moon } from 'lucide-react'
import { useTheme } from './ThemeProvider'
import { Button } from '@/components/ui/button'

export function ThemeToggle() {
  const { resolved, setTheme } = useTheme()

  const isDark = resolved === 'dark'

  const toggle = () => {
    setTheme(isDark ? 'light' : 'dark')
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          onClick={toggle}
          aria-label={isDark ? '切换到浅色模式' : '切换到深色模式'}
          className="btn-elegant h-8 w-8"
        >
          {isDark ? (
            <Moon className="h-4 w-4" />
          ) : (
            <Sun className="h-4 w-4" />
          )}
        </Button>
      </TooltipTrigger>
      <TooltipContent>
        <p>{isDark ? '切换到浅色' : '切换到深色'}</p>
      </TooltipContent>
    </Tooltip>
  )
}
