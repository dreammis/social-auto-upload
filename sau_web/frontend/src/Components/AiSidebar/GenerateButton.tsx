import { Button } from '@/components/ui/button'
import { Loader2, Sparkles, RefreshCw } from 'lucide-react'

interface GenerateButtonProps {
  isGenerating: boolean
  hasGenerated: boolean
  onClick: () => void
}

export function GenerateButton({ isGenerating, hasGenerated, onClick }: GenerateButtonProps) {
  if (isGenerating) {
    return (
      <Button disabled className="w-full" size="lg">
        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
        生成中...
      </Button>
    )
  }

  if (hasGenerated) {
    return (
      <Button onClick={onClick} variant="outline" className="w-full" size="lg">
        <RefreshCw className="h-4 w-4 mr-2" />
        重新生成
      </Button>
    )
  }

  return (
    <Button onClick={onClick} className="w-full" size="lg">
      <Sparkles className="h-4 w-4 mr-2" />
      一键生成
    </Button>
  )
}
