import { useEffect, useMemo } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { useAiModels } from '@/hooks/useAiGeneration'
import { useAiStore } from '@/stores/useAiStore'
import { Loader2, Wifi, WifiOff, Type, ImageIcon, Video, Mic, FileText } from 'lucide-react'

interface ModelItem {
  id: string
  name: string
  tags?: string[]
  context_length?: number
}

const TAG_CONFIG: Record<string, { icon: typeof Type; label: string; color: string }> = {
  text: { icon: Type, label: '文字', color: 'bg-blue-500/10 text-blue-600' },
  image: { icon: ImageIcon, label: '图片', color: 'bg-green-500/10 text-green-600' },
  video: { icon: Video, label: '视频', color: 'bg-purple-500/10 text-purple-600' },
  audio: { icon: Mic, label: '音频', color: 'bg-orange-500/10 text-orange-600' },
  file: { icon: FileText, label: '文件', color: 'bg-gray-500/10 text-gray-600' },
}

function ModelTags({ tags }: { tags?: string[] }) {
  if (!tags || tags.length === 0) return null
  return (
    <div className="flex gap-0.5 ml-auto shrink-0">
      {tags.map((tag) => {
        const cfg = TAG_CONFIG[tag]
        if (!cfg) return null
        const Icon = cfg.icon
        return (
          <Badge key={tag} variant="secondary" className={`h-4 px-1 text-[9px] ${cfg.color}`}>
            <Icon className="h-2.5 w-2.5" />
          </Badge>
        )
      })}
    </div>
  )
}

export function ModelSelector() {
  const { data, isLoading, isRefetching } = useAiModels()
  const models: ModelItem[] = useMemo(() => data?.models ?? [], [data?.models])
  const source = data?.source ?? 'unknown'
  const selectedModel = useAiStore((s) => s.selectedModel)
  const setSelectedModel = useAiStore((s) => s.setSelectedModel)
  const setModelTags = useAiStore((s) => s.setModelTags)

  useEffect(() => {
    if (models.length > 0 && !models.some((m) => m.id === selectedModel)) {
      setSelectedModel(models[0].id)
    }
  }, [models, selectedModel, setSelectedModel])

  useEffect(() => {
    const tags = models.find((m) => m.id === selectedModel)?.tags ?? ['text']
    setModelTags(tags)
  }, [models, selectedModel, setModelTags])

  const selectedTags = models.find((m) => m.id === selectedModel)?.tags

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label className="text-sm font-medium">AI 模型</Label>
        <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
          {isRefetching ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : source === 'live' ? (
            <Wifi className="h-3 w-3 text-green-500" />
          ) : (
            <WifiOff className="h-3 w-3 text-amber-500" />
          )}
          <span>{source === 'live' ? `${models.length} 个免费模型` : '离线列表'}</span>
        </div>
      </div>
      <Select value={selectedModel} onValueChange={setSelectedModel} disabled={isLoading}>
        <SelectTrigger className="w-full">
          <SelectValue placeholder={isLoading ? '加载模型列表...' : '选择模型'} />
        </SelectTrigger>
        <SelectContent>
          {models.map((m) => (
            <SelectItem key={m.id} value={m.id}>
              <div className="flex items-center gap-2 w-full">
                <span className="truncate">{m.name}</span>
                <ModelTags tags={m.tags} />
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {selectedTags && selectedTags.length > 0 && (
        <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
          <span>支持:</span>
          {selectedTags.map((tag) => {
            const cfg = TAG_CONFIG[tag]
            if (!cfg) return null
            const Icon = cfg.icon
            return (
              <span key={tag} className="flex items-center gap-0.5">
                <Icon className="h-3 w-3" />
                {cfg.label}
              </span>
            )
          })}
        </div>
      )}
    </div>
  )
}
