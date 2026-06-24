import { Button } from '@/components/ui/button'
import { Tip } from '@/lib/tip'
import { useAiStore } from '@/stores/useAiStore'
import { useAiConfig } from '@/hooks/useAiConfig'
import { Sparkles, ChevronUp, Zap } from 'lucide-react'

/**
 * @deprecated Kept for legacy compatibility only. The publish page moved
 * the model/key affordances into the header of `PublishAiSidebar`. New
 * callers should not depend on this toolbar.
 */

interface AiPanelToolbarProps {
  isExpanded: boolean
  onToggle: () => void
  onQuickGenerate?: () => void
  isGenerating?: boolean
}

export function AiPanelToolbar({ isExpanded, onToggle, onQuickGenerate, isGenerating }: AiPanelToolbarProps) {
  const selectedModel = useAiStore((s) => s.selectedModel)
  const { data: aiConfig } = useAiConfig()

  const modelLabel = selectedModel.split('/').pop() || selectedModel
  const keyCount = aiConfig?.key_count ?? 0

  return (
    <div className="flex items-center justify-between px-4 h-full gap-2">
      {/* Left: status — simplified when collapsed */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex items-center gap-1.5 text-sm font-medium shrink-0">
          <Sparkles className="h-4 w-4 text-primary" />
          <span className="hidden sm:inline">AI 助手</span>
        </div>

        {/* Only show detailed info when expanded */}
        {isExpanded && (
          <div className="hidden md:flex items-center gap-2 text-[11px] text-muted-foreground">
            <span className="truncate max-w-[120px]">{modelLabel}</span>
            {keyCount > 0 && (
              <>
                <span className="text-muted-foreground/40">·</span>
                <span className="text-green-600 dark:text-green-400">{keyCount} Keys</span>
              </>
            )}
          </div>
        )}
      </div>

      {/* Right: actions */}
      <div className="flex items-center gap-1.5 shrink-0">
        {onQuickGenerate && (
          <Tip text={isGenerating ? '生成中...' : '增强提示词 → 生成 → 自动填写'}>
            <Button
              variant="default"
              size="sm"
              className="h-8 px-3 text-[11px] gap-1"
              onClick={onQuickGenerate}
              disabled={isGenerating}
            >
              <Zap className={`h-3.5 w-3.5 ${isGenerating ? 'animate-pulse' : ''}`} />
              <span className="hidden sm:inline">一键全流程</span>
            </Button>
          </Tip>
        )}

        <Tip text={isExpanded ? '收起面板' : '展开 AI 面板'}>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 px-2 text-[11px]"
            onClick={onToggle}
            aria-label={isExpanded ? '收起 AI 面板' : '展开 AI 面板'}
          >
            {isExpanded ? (
              <>
                <ChevronUp className="h-4 w-4 mr-1 rotate-180" />
                <span className="hidden sm:inline">收起</span>
              </>
            ) : (
              <>
                <ChevronUp className="h-4 w-4 mr-1" />
                <span className="hidden sm:inline">展开</span>
              </>
            )}
          </Button>
        </Tip>
      </div>
    </div>
  )
}
