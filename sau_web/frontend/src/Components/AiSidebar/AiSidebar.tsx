import { useState, useRef, useCallback, useEffect, useMemo } from 'react'
import { createPortal } from 'react-dom'
import type { RefObject } from 'react'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'
import { Tip } from '@/lib/tip'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import {
  Sparkles, Info, History, Save, Wand2, Trash2,
  ChevronDown, ChevronUp, Settings, Key, Eye, EyeOff,
  Check, X, Paperclip, Image as ImageIcon, Zap, BookOpen,
  Copy, RotateCcw, Upload, Pencil, CheckCheck, AlertTriangle,
} from 'lucide-react'
import { ModelSelector } from './ModelSelector'
import { GenerateButton } from './GenerateButton'
import { useAiStore } from '@/stores/useAiStore'
import { useAiHistoryStore, type HistoryEntry } from '@/stores/useAiHistory'
import { useAiTemplatesStore } from '@/stores/useAiTemplates'
import { useChatStore } from '@/stores/useChatStore'
import { ChatArea } from '@/components/AiPanel/ChatArea'
import { MarkdownContent } from '@/components/AiPanel/ChatArea'
import { useChatActions } from '@/lib/chat/useChatActions'
import { useAiConfig, useSetAiConfig, useDeleteAiConfig, useAiKeys } from '@/hooks/useAiConfig'
import { useToast } from '@/components/ui/toast'
import { api } from '@/api/client'
import type { FormHandle } from '@/lib/chat/chatFormBridge'

export type AiGenerationResult = {
  title: string
  desc: string
  tags: string
}

interface AiSidebarProps {
  mode: 'video' | 'note'
  platform?: string
  onGenerated: (result: AiGenerationResult) => void
  /** Active publish-form ref. */
  formRef: RefObject<FormHandle | null>
}

const OPTIMIZE_MODEL = 'google/gemma-3-1b-it:free'

function buildOptimizePrompt(mode: 'video' | 'note', part: string, currentValue: string, context: string): string {
  const partNames: Record<string, string> = { title: '标题', desc: mode === 'video' ? '描述' : '内容', tags: '标签' }
  const label = partNames[part] || part
  return `你是一个文案优化助手。请对以下${label}进行润色优化。

严格规则：
1. 只基于原文优化，不得添加原文中没有的新信息、新观点或新内容
2. 可以优化：用词精准度、语句流畅度、排版格式、标点符号
3. 不得改变原文的核心含义和关键信息
4. 去除明显的 AI 生成痕迹，使文案读起来像人工撰写
5. 只返回优化后的${label}内容，不要添加任何解释、前缀或后缀

当前${label}：
${currentValue}

上下文（完整文案）：
${context}`
}

function parseResult(content: string): AiGenerationResult {
  const titleMatch = content.match(/^标题[：:]\s*(.+)/m)
  const descMatch = content.match(/^描述[：:]\s*([\s\S]+?)(?=^标签[：:]|$)/m)
  const contentMatch = content.match(/^内容[：:]\s*([\s\S]+?)(?=^标签[：:]|$)/m)
  const tagsMatch = content.match(/^标签[：:]\s*(.+)/m)

  return {
    title: titleMatch?.[1]?.trim() || '',
    desc: (descMatch?.[1] || contentMatch?.[1] || '').trim(),
    tags: tagsMatch?.[1]?.trim() || '',
  }
}

export function AiSidebar({ mode, platform, onGenerated, formRef }: AiSidebarProps) {
  const [customInstruction, setCustomInstruction] = useState('')
  const [prevInstruction, setPrevInstruction] = useState('')
  const [showHistory, setShowHistory] = useState(false)
  const [showTemplates, setShowTemplates] = useState(false)
  const [saveTemplateName, setSaveTemplateName] = useState('')
  const [showSaveInput, setShowSaveInput] = useState(false)
  const [optimizing, setOptimizing] = useState<string | null>(null)
  const [isEnhancing, setIsEnhancing] = useState(false)
  const [showKeyInput, setShowKeyInput] = useState(false)
  const [keyInput, setKeyInput] = useState('')
  const [showBatchImport, setShowBatchImport] = useState(false)
  const [batchInput, setBatchInput] = useState('')
  const [batchImporting, setBatchImporting] = useState(false)
  const [showKey, setShowKey] = useState(false)
  const [showKeyList, setShowKeyList] = useState(false)
  const [currentKeyInfo, setCurrentKeyInfo] = useState<{ id: number; masked: string } | null>(null)
  const [attachedFiles, setAttachedFiles] = useState<Array<{ name: string; dataUrl: string; type: string; poster?: string; frames?: string[] }>>([])
  const [previewIndex, setPreviewIndex] = useState<number | null>(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<{ type: 'key' | 'key_single' | 'history'; id?: string | number } | null>(null)
  const [editingField, setEditingField] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  /**
   * User-edit overrides keyed by assistant message id. `lastResult` is
   * derived from the store's last assistant message; without this map
   * an inline edit would vanish on the next render and never propagate
   * via re-applies. Edits live until the next assistant message commits
   * a new content blob (which lands as a different message id).
   */
  const [editsByMessageId, setEditsByMessageId] = useState<Record<string, AiGenerationResult>>({})
  const [isFullFlow, setIsFullFlow] = useState(false)
  const [fullFlowStep, setFullFlowStep] = useState<'enhance' | 'generate' | 'fill' | null>(null)
  const [dismissRateLimitAlert, setDismissRateLimitAlert] = useState(false)
  const isFullFlowRef = useRef(isFullFlow)
  isFullFlowRef.current = isFullFlow
  const fullFlowStepRef = useRef(fullFlowStep)
  fullFlowStepRef.current = fullFlowStep
  const fileInputRef = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const customInstructionRef = useRef(customInstruction)
  customInstructionRef.current = customInstruction

  const selectedModel = useAiStore((s) => s.selectedModel)
  const modelTags = useAiStore((s) => s.modelTags)
  const { addToast } = useToast()
  const { entries, addEntry, removeEntry } = useAiHistoryStore()
  const { templates, addTemplate, removeTemplate } = useAiTemplatesStore()
  const { data: aiConfig, isLoading: configLoading } = useAiConfig()
  const { data: aiKeys, isLoading: keysLoading, refetch: refetchKeys } = useAiKeys()
  const setKeyMutation = useSetAiConfig()
  const deleteKeyMutation = useDeleteAiConfig()

  // ── Chat store reads (replaces local isStreaming/streamingText/lastError) ──
  const jobStatus = useChatStore((s) => s.jobStatus)
  const streamingDraft = useChatStore((s) => s.streamingDraft)
  const chatError = useChatStore((s) => s.error)
  const activeSessionId = useChatStore((s) => s.activeSessionId)
  const lastAssistantMessage = useChatStore((s) => {
    const sid = s.activeSessionId
    if (!sid) return null
    const msgs = s.sessions[sid]?.messages ?? []
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === 'assistant') return msgs[i]
    }
    return null
  })
  const lastResult = useMemo<AiGenerationResult | null>(
    () => {
      if (!lastAssistantMessage) return null
      const base = parseResult(lastAssistantMessage.content)
      // Apply user-edit override if present for this message id.
      return editsByMessageId[lastAssistantMessage.id] ?? base
    },
    [lastAssistantMessage, editsByMessageId],
  )
  const hasGenerated = lastAssistantMessage !== null
  const isStreaming =
    jobStatus === 'generating' && (streamingDraft.length > 0 || activeSessionId !== null)

  // ── Chat actions: owns SSE stream + commit + auto-apply ──
  const chatActions = useChatActions({
    formRef,
    mode,
    platform,
    model: selectedModel,
    parseResponse: parseResult,
  })

  const hasMedia = attachedFiles.length > 0
  const hasVisionSupport = modelTags.includes('image') || modelTags.includes('video')
  const showVisionWarning = hasMedia && !hasVisionSupport

  const extractVideoFrames = useCallback((dataUrl: string, frameCount = 4): Promise<{ poster: string; frames: string[] }> => {
    return new Promise((resolve) => {
      const video = document.createElement('video')
      video.preload = 'auto'
      video.muted = true
      video.playsInline = true
      video.crossOrigin = 'anonymous'

      video.onloadedmetadata = () => {
        const duration = video.duration
        const frames: string[] = []
        let captured = 0
        const interval = duration / (frameCount + 1)

        const captureFrame = (time: number) => {
          video.currentTime = time
        }

        video.onseeked = () => {
          const canvas = document.createElement('canvas')
          const scale = Math.min(1, 512 / Math.max(video.videoWidth, video.videoHeight))
          canvas.width = video.videoWidth * scale
          canvas.height = video.videoHeight * scale
          const ctx = canvas.getContext('2d')
          if (ctx) {
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
            frames.push(canvas.toDataURL('image/jpeg', 0.6))
          }
          captured++
          if (captured < frameCount) {
            captureFrame(interval * (captured + 1))
          } else {
            resolve({ poster: frames[0] || '', frames })
            URL.revokeObjectURL(video.src)
          }
        }

        captureFrame(interval)
      }

      video.onerror = () => resolve({ poster: '', frames: [] })
      video.src = dataUrl
    })
  }, [])

  const processFiles = useCallback(async (fileList: FileList | File[]) => {
    const MAX_SIZE = 50 * 1024 * 1024
    for (const file of Array.from(fileList)) {
      if (file.size > MAX_SIZE) {
        addToast(`${file.name} 超过 50MB 限制`, 'error')
        continue
      }
      const dataUrl = await new Promise<string>((resolve) => {
        const reader = new FileReader()
        reader.onload = () => resolve(reader.result as string)
        reader.readAsDataURL(file)
      })
      if (file.type.startsWith('video/')) {
        addToast(`正在提取 ${file.name} 关键帧...`, 'info')
        const { poster, frames } = await extractVideoFrames(dataUrl)
        setAttachedFiles((prev) => [...prev, { name: file.name, dataUrl, type: file.type, poster, frames }])
      } else {
        setAttachedFiles((prev) => [...prev, { name: file.name, dataUrl, type: file.type }])
      }
    }
  }, [addToast, extractVideoFrames])

  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) await processFiles(e.target.files)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }, [processFiles])

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    if (e.dataTransfer.files.length > 0) await processFiles(e.dataTransfer.files)
  }, [processFiles])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }, [])

  const removeFile = useCallback((index: number) => {
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index))
  }, [])

  const collectImages = useCallback(() => {
    const supportsVideo = modelTags.includes('video')
    const images: string[] = []
    for (const f of attachedFiles) {
      if (f.type.startsWith('video/')) {
        if (supportsVideo) images.push(f.dataUrl)
        else if (f.frames?.length) images.push(...f.frames)
      } else if (f.type.startsWith('image/')) {
        images.push(f.dataUrl)
      }
    }
    return images
  }, [attachedFiles, modelTags])

  const handleEnhancePrompt = async () => {
    if (!customInstruction.trim() && attachedFiles.length === 0) {
      addToast('请输入文字或上传图片', 'warning')
      return
    }
    setPrevInstruction(customInstruction)
    setIsEnhancing(true)
    setCurrentKeyInfo(null)
    let enhanced = ''
    try {
      const images = collectImages()
      await api.enhancePrompt(
        { text: customInstruction, images, model: selectedModel, platform },
        (chunk) => { enhanced += chunk; setCustomInstruction(enhanced) },
        (final) => { setCustomInstruction(final || enhanced); setIsEnhancing(false); setCurrentKeyInfo(null); addToast('提示词已增强', 'success') },
        (error) => { setIsEnhancing(false); setCurrentKeyInfo(null); addToast(error, 'error') },
        (keyId, masked) => { setCurrentKeyInfo({ id: keyId, masked }) },
      )
    } catch (err: unknown) {
      setIsEnhancing(false)
      setCurrentKeyInfo(null)
      addToast(err instanceof Error ? err.message : '网络错误', 'error')
    }
  }

  const handleUndoEnhance = () => {
    if (prevInstruction) {
      setCustomInstruction(prevInstruction)
      setPrevInstruction('')
      addToast('已恢复原文', 'info')
    }
  }

  /**
   * Generate via the multi-turn chat pipeline. The chatActions hook owns
   * the SSE fetch, chunk→store dispatches, and the auto-apply step that
   * routes the parsed result into the form. Errors propagate to the
   * store and surface via the error block below.
   */
  const handleGenerate = useCallback(async () => {
    const currentInstruction = customInstructionRef.current
    if (!currentInstruction.trim() && attachedFiles.length === 0) {
      addToast('请输入说明或上传图片', 'warning')
      return
    }
    setCurrentKeyInfo(null)
    if (isFullFlowRef.current) setFullFlowStep('generate')
    const images = collectImages()
    await chatActions.send(currentInstruction, images)
    // Best-effort history entry. Multi-turn history entry contains the
    // user instruction + the latest committed assistant content.
    const sid = useChatStore.getState().activeSessionId
    const session = sid ? useChatStore.getState().sessions[sid] : null
    const lastAssistant = session
      ? [...session.messages].reverse().find((m) => m.role === 'assistant')
      : null
    if (lastAssistant) {
      const parsed = parseResult(lastAssistant.content)
      addEntry({
        platform: platform || 'unknown',
        model: selectedModel,
        prompt: currentInstruction,
        content: lastAssistant.content,
        parsed,
      })
      if (isFullFlowRef.current) setFullFlowStep('fill')
    }
  }, [attachedFiles, collectImages, chatActions, addToast, addEntry, platform, selectedModel])

  const handleFullFlow = useCallback(async () => {
    if (!customInstruction.trim() && attachedFiles.length === 0) {
      addToast('请输入说明或上传图片', 'warning')
      return
    }
    setIsFullFlow(true)
    setFullFlowStep('enhance')
    try {
      if (customInstruction.trim() || attachedFiles.length > 0) {
        setPrevInstruction(customInstruction)
        setIsEnhancing(true)
        let enhanced = ''
        await api.enhancePrompt(
          { text: customInstruction, images: collectImages(), model: selectedModel, platform },
          (chunk) => { enhanced += chunk; setCustomInstruction(enhanced) },
          (final) => { setCustomInstruction(final || enhanced); setIsEnhancing(false) },
          (error) => { setIsEnhancing(false); throw new Error(error) },
          (keyId, masked) => { setCurrentKeyInfo({ id: keyId, masked }) },
        )
      }
      setFullFlowStep('generate')
      await handleGenerate()
    } catch (err: unknown) {
      setIsEnhancing(false)
      // isStreaming is derived from useChatStore.jobStatus — the
      // chat hook's error path already moved to 'error' status for
      // HTTP failures; cancels are silent.
      setFullFlowStep(null)
      addToast(err instanceof Error ? err.message : '全流程执行失败', 'error')
    } finally {
      setIsFullFlow(false)
      // Keep fill step visible for a moment before clearing
      if (fullFlowStepRef.current !== 'fill') setFullFlowStep(null)
    }
  }, [customInstruction, attachedFiles, collectImages, selectedModel, platform, handleGenerate, addToast])

  const handleStartEdit = useCallback((field: string, value: string) => {
    setEditingField(field)
    setEditValue(value)
  }, [])

  const handleConfirmEdit = useCallback(() => {
    if (!editingField || !lastResult || !lastAssistantMessage) return
    const updated = { ...lastResult }
    if (editingField === 'title') updated.title = editValue
    else if (editingField === 'desc') updated.desc = editValue
    else if (editingField === 'tags') updated.tags = editValue
    // Persist the edit keyed by the assistant message id so the next
    // "全部应用" continues to write the user's value (not the parsed
    // baseline). Override is auto-released the next time a different
    // assistant message commits, since it carries a new id.
    setEditsByMessageId((prev) => ({ ...prev, [lastAssistantMessage.id]: updated }))
    onGenerated(updated)
    addToast('已更新', 'success')
    setEditingField(null)
    setEditValue('')
  }, [editingField, editValue, lastResult, lastAssistantMessage, addToast, onGenerated])

  const handleCancelEdit = useCallback(() => {
    setEditingField(null)
    setEditValue('')
  }, [])

  const handleApplySingle = useCallback((field: string) => {
    if (!lastResult) return
    const partial: AiGenerationResult = { title: '', desc: '', tags: '' }
    if (field === 'title') partial.title = lastResult.title
    else if (field === 'desc') partial.desc = lastResult.desc
    else if (field === 'tags') partial.tags = lastResult.tags
    onGenerated(partial)
    addToast(`已应用${field === 'title' ? '标题' : field === 'desc' ? (mode === 'video' ? '描述' : '内容') : '标签'}`, 'success')
  }, [lastResult, onGenerated, addToast, mode])

  const handleApplyAll = useCallback(() => {
    if (!lastResult) return
    onGenerated(lastResult)
    addToast('已全部应用到表单', 'success')
  }, [lastResult, onGenerated, addToast])

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault()
        if (isStreaming === false && !isEnhancing) handleGenerate()
      }
    }
    el.addEventListener('keydown', handler)
    return () => el.removeEventListener('keydown', handler)
  }, [isStreaming, isEnhancing, handleGenerate])

  const handleRetry = () => {
    chatActions.cancel() // clear any leftover draft
    handleGenerate()
  }

  /**
   * Optimize one field of the last assistant message. Adds another turn
   * to the active chat session; the Auto-apply step in the chat hook
   * writes the new value back into the form. (No separate sync API call.)
   */
  const handleOptimize = async (part: string) => {
    if (!lastResult) return
    const currentValue = part === 'title' ? lastResult.title : part === 'desc' ? lastResult.desc : lastResult.tags
    if (!currentValue) return
    setOptimizing(part)
    try {
      const prompt = buildOptimizePrompt(mode, part, currentValue, JSON.stringify(lastResult))
      await chatActions.send(prompt, collectImages(), OPTIMIZE_MODEL)
      addToast(`${part === 'title' ? '标题' : part === 'desc' ? (mode === 'video' ? '描述' : '内容') : '标签'}已优化`, 'success')
    } catch {
      addToast('优化请求失败', 'error')
    } finally {
      setOptimizing(null)
    }
  }

  const handleCopy = () => {
    if (!lastResult) return
    const parts = [lastResult.title, lastResult.desc, lastResult.tags].filter(Boolean)
    navigator.clipboard.writeText(parts.join('\n')).then(() => addToast('已复制到剪贴板', 'success'))
  }

  const handleApplyHistory = (entry: HistoryEntry) => {
    onGenerated(entry.parsed)
    addToast('已应用历史记录', 'success')
  }

  const handleApplyTemplate = (content: string) => {
    setCustomInstruction(content)
    setShowTemplates(false)
  }

  const handleSaveTemplate = () => {
    if (!saveTemplateName.trim() || !customInstruction.trim()) return
    addTemplate(saveTemplateName.trim(), customInstruction.trim())
    setSaveTemplateName('')
    setShowSaveInput(false)
    addToast('模板已保存', 'success')
  }

  const handleSaveKey = async () => {
    if (!keyInput.trim()) return
    try {
      const res = await setKeyMutation.mutateAsync(keyInput.trim())
      if (res.success) { addToast('API Key 已添加', 'success'); setKeyInput(''); setShowKeyInput(false) }
      else addToast(res.message || '保存失败', 'error')
    } catch { addToast('保存失败', 'error') }
  }

  const handleBatchImport = async () => {
    const lines = batchInput.split(/[\n,]+/).map((l) => l.trim()).filter(Boolean)
    if (lines.length === 0) return
    setBatchImporting(true)
    try {
      const res = await api.batchAddKeys(lines)
      if (res.success) {
        const { added, skipped } = res.data!
        addToast(`批量导入完成：新增 ${added} 个，跳过 ${skipped} 个`, 'success')
        setBatchInput('')
        setShowBatchImport(false)
        refetchKeys()
      } else {
        addToast(res.message || '批量导入失败', 'error')
      }
    } catch {
      addToast('批量导入失败', 'error')
    } finally {
      setBatchImporting(false)
    }
  }

  const confirmDelete = () => {
    if (!deleteTarget) return
    if (deleteTarget.type === 'key') {
      deleteKeyMutation.mutateAsync(undefined).then(() => addToast('API Key 已删除', 'success')).catch(() => addToast('删除失败', 'error'))
    } else if (deleteTarget.type === 'key_single' && deleteTarget.id !== undefined) {
      deleteKeyMutation.mutateAsync(deleteTarget.id as number).then(() => addToast('API Key 已删除', 'success')).catch(() => addToast('删除失败', 'error'))
    } else if (deleteTarget.type === 'history' && deleteTarget.id) {
      removeEntry(deleteTarget.id as string)
    }
    setDeleteTarget(null)
  }

  return (
    <div className="space-y-3.5">

        {/* ── 1. API Key 状态栏 ──────────────────────────────── */}
        <div className="group/keybar flex items-center justify-between rounded-lg border bg-gradient-to-r from-muted/40 to-muted/20 dark:from-muted/50 dark:to-muted/30 px-3 py-2 shadow-sm transition-shadow hover:shadow-md">
          <div className="flex items-center gap-2.5 text-xs text-muted-foreground">
            <Key className="h-3.5 w-3.5 shrink-0" />
            {configLoading || keysLoading ? (
              <span className="flex items-center gap-2">
                <span className="h-2 w-2 animate-pulse rounded-full bg-muted-foreground/30" />
                <span className="h-3 w-20 animate-pulse rounded bg-muted-foreground/20" />
              </span>
            ) : aiConfig?.configured ? (
              <span className="flex items-center gap-2 min-w-0">
                <span className="relative flex h-2 w-2 shrink-0">
                  <span className="absolute inset-0 animate-ping rounded-full bg-green-400/60" />
                  <span className="relative h-2 w-2 rounded-full bg-green-500" />
                </span>
                <span className="truncate">已配置 {aiConfig.key_count || 0} 个 Key</span>
                {aiKeys && aiKeys.length > 0 && aiKeys.some(k => k.rate_limited) && (
                  <Badge variant="outline" className="h-4 shrink-0 border-amber-200 bg-amber-50 px-1 text-[9px] text-amber-700 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-400">
                    {aiKeys.filter(k => k.rate_limited).length} 个限速中
                  </Badge>
                )}
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-red-500" />
                未配置 Key
              </span>
            )}
          </div>
          <div className="flex items-center gap-0.5 opacity-70 transition-opacity group-hover/keybar:opacity-100">
            {configLoading || keysLoading ? (
              <div className="h-6 w-6 animate-pulse rounded-md bg-muted-foreground/20" />
            ) : aiConfig?.configured ? (
              <>
                <Tip text="添加 Key">
                  <Button variant="ghost" size="sm" className="h-7 w-7 rounded-md p-0 hover:bg-primary/10 hover:text-primary" onClick={() => { setShowKeyInput(!showKeyInput); setShowBatchImport(false) }}>
                    <Settings className="h-3.5 w-3.5" />
                  </Button>
                </Tip>
                <Tip text="批量导入 Key">
                  <Button variant="ghost" size="sm" className="h-7 rounded-md px-1.5 text-[10px] font-medium hover:bg-primary/10 hover:text-primary" onClick={() => { setShowBatchImport(!showBatchImport); setShowKeyInput(false) }}>
                    批量
                  </Button>
                </Tip>
                <Tip text="查看 Key 列表">
                  <Button variant="ghost" size="sm" className="h-7 w-7 rounded-md p-0" onClick={() => setShowKeyList(!showKeyList)}>
                    {showKeyList ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                  </Button>
                </Tip>
                <Tip text="删除全部 Key">
                  <Button variant="ghost" size="sm" className="h-7 w-7 rounded-md p-0 text-muted-foreground hover:bg-destructive/10 hover:text-destructive" onClick={() => setDeleteTarget({ type: 'key' })}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </Tip>
              </>
            ) : (
              <Button variant="outline" size="sm" className="h-7 rounded-md px-2.5 text-[10px] font-medium" onClick={() => setShowKeyInput(true)}>
                设置 Key
              </Button>
            )}
          </div>
        </div>

        {showKeyInput && (
          <div className="animate-in fade-in slide-in-from-top-1 space-y-2 rounded-lg border border-primary/20 dark:border-primary/30 bg-primary/5 dark:bg-primary/10 px-2.5 py-2.5 duration-200">
            <div className="flex gap-1.5">
              <div className="relative flex-1">
                <Input type={showKey ? 'text' : 'password'} placeholder="sk-or-v1-xxxxxxxxxxxxxxxx" value={keyInput} onChange={(e) => setKeyInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleSaveKey()} className="h-8 text-xs pr-8 font-mono tracking-tight focus-visible:ring-primary/30" />
                <button className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-muted-foreground transition-colors hover:text-foreground" onClick={() => setShowKey(!showKey)}>
                  {showKey ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                </button>
              </div>
              <Button size="sm" className="h-8 w-8 rounded-md p-0" onClick={handleSaveKey} disabled={setKeyMutation.isPending}><Check className="h-4 w-4" /></Button>
              <Button size="sm" variant="ghost" className="h-8 w-8 rounded-md p-0" onClick={() => { setShowKeyInput(false); setKeyInput('') }}><X className="h-4 w-4" /></Button>
            </div>
            <p className="text-[10px] leading-relaxed text-muted-foreground">
              添加多个 Key 可实现轮询，避免单 Key 限额。从{' '}
              <a href="https://openrouter.ai/keys" target="_blank" rel="noopener" className="font-medium underline underline-offset-2 transition-colors hover:text-primary">openrouter.ai/keys</a>{' '}
              免费获取
            </p>
          </div>
        )}

        {showBatchImport && (
          <div className="animate-in fade-in slide-in-from-top-1 space-y-2 rounded-lg border border-primary/20 dark:border-primary/30 bg-primary/5 dark:bg-primary/10 px-2.5 py-2.5 duration-200">
            <Textarea
              placeholder={"粘贴多个 Key，每行一个或用逗号分隔：\nsk-or-v1-aaa...\nsk-or-v1-bbb...\nsk-or-v1-ccc..."}
              value={batchInput}
              onChange={(e) => setBatchInput(e.target.value)}
              rows={5}
              className="resize-none text-xs font-mono tracking-tight focus-visible:ring-primary/30"
            />
            <div className="flex items-center gap-1.5">
              <Button size="sm" className="h-7 rounded-md px-3 text-[11px]" onClick={handleBatchImport} disabled={batchImporting || !batchInput.trim()}>
                {batchImporting ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : null}
                {batchImporting ? '导入中...' : '批量导入'}
              </Button>
              <Button size="sm" variant="ghost" className="h-7 rounded-md px-2 text-[11px]" onClick={() => { setShowBatchImport(false); setBatchInput('') }}>取消</Button>
              <span className="ml-auto text-[10px] text-muted-foreground">
                {batchInput.split(/[\n,]+/).filter((l) => l.trim()).length} 个 Key
              </span>
            </div>
          </div>
        )}

        {showKeyList && aiKeys && aiKeys.length > 0 && (
          <div className="animate-in fade-in slide-in-from-top-1 space-y-1 rounded-lg border bg-muted/30 px-2 py-2 duration-200">
            <div className="flex items-center justify-between px-1">
              <span className="text-[10px] font-medium text-muted-foreground">Key 轮询池</span>
              <Badge variant="outline" className="h-4 px-1.5 text-[9px] font-normal">{aiKeys.length} 个</Badge>
            </div>
            {aiKeys.map((k, idx) => (
              <div key={k.id} className="group/key flex items-center justify-between rounded-md bg-background/80 px-2.5 py-1.5 transition-colors hover:bg-background">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="w-5 shrink-0 text-center text-[9px] font-medium text-muted-foreground/60">#{idx + 1}</span>
                  <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${k.rate_limited ? 'bg-amber-500' : 'bg-green-500'}`} />
                  <span className="truncate text-[11px] font-mono tracking-tight">{k.masked}</span>
                  {k.rate_limited && <Badge variant="outline" className="h-4 shrink-0 border-amber-200 bg-amber-50 px-1 text-[8px] text-amber-700 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-400">限速中</Badge>}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 shrink-0 rounded-md p-0 opacity-0 transition-all hover:bg-destructive/10 hover:text-destructive group-hover/key:opacity-100"
                  onClick={() => setDeleteTarget({ type: 'key_single', id: k.id })}
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            ))}
          </div>
        )}

        {!configLoading && !keysLoading && !aiConfig?.configured && !showKeyInput && (
          <Alert className="py-2.5"><Info className="h-4 w-4" /><AlertDescription className="text-xs">请先设置 API Key 才能使用 AI 功能</AlertDescription></Alert>
        )}

        {aiKeys && aiKeys.length > 0 && aiKeys.every(k => k.rate_limited) && !dismissRateLimitAlert && (
          <Alert className="relative py-2 border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
              <AlertDescription className="text-xs text-amber-700 dark:text-amber-300 truncate flex-1 min-w-0">
                所有 Key 均已触发限速，请等待冷却后重试，或添加更多 Key
              </AlertDescription>
              <Button
                variant="ghost"
                size="sm"
                className="shrink-0 h-6 w-6 rounded-md p-0 text-amber-600 hover:bg-amber-100 dark:text-amber-400 dark:hover:bg-amber-900/50"
                onClick={() => setDismissRateLimitAlert(true)}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
          </Alert>
        )}

        {/* ── 2. 模型选择 ──────────────────────────────────── */}
        <ModelSelector />

        {showVisionWarning && (
          <Alert className="py-1.5 border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" />
            <AlertDescription className="text-xs text-amber-700 dark:text-amber-300">
              当前模型不支持图片/视频分析，附件将以关键帧形式发送，建议切换到支持 vision 的模型以获得更好效果
            </AlertDescription>
          </Alert>
        )}

        {/* ── 2b. Multi-turn chat history (initially empty) ── */}
        <ChatArea />

        <Separator />

        {/* ── 3. 输入区 ────────────────────────────────────── */}
        <div
          className="space-y-2"
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
        >
          <div className="flex items-center justify-between">
            <Label className="text-sm font-medium">补充说明</Label>
            <span className="text-[10px] text-muted-foreground">Ctrl+Enter 生成</span>
          </div>

          <div className="relative">
            <Textarea
              ref={textareaRef}
              placeholder={mode === 'video' ? '例如：关于美食制作的视频，风格轻松活泼...' : '例如：关于旅行攻略的图文，包含实用建议...'}
              value={customInstruction}
              onChange={(e) => setCustomInstruction(e.target.value)}
              rows={3}
              className={`resize-none text-sm transition-all ${isDragOver ? 'ring-2 ring-primary border-primary' : ''}`}
            />
            {isDragOver && (
              <div className="absolute inset-0 flex items-center justify-center rounded-md bg-primary/10 pointer-events-none">
                <div className="flex flex-col items-center gap-1 text-primary">
                  <Upload className="h-6 w-6" />
                  <span className="text-xs font-medium">松开上传</span>
                </div>
              </div>
            )}
          </div>

          {/* 附件预览 */}
          {attachedFiles.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {attachedFiles.map((file, i) => (
                <div key={i} className="relative group cursor-pointer" onClick={() => setPreviewIndex(i)}>
                  {file.type.startsWith('image/') ? (
                    <img src={file.dataUrl} alt={file.name} className="h-14 w-14 rounded border object-cover transition-opacity hover:opacity-80" />
                  ) : file.type.startsWith('video/') ? (
                    <div className="relative h-14 w-14 overflow-hidden rounded border">
                      {file.poster || file.frames?.[0] ? (
                        <img src={file.poster || file.frames?.[0]} alt={file.name} className="h-full w-full object-cover transition-opacity hover:opacity-80" />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center bg-muted"><ImageIcon className="h-5 w-5 text-muted-foreground" /></div>
                      )}
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-black/60">
                          <svg viewBox="0 0 24 24" fill="white" className="h-2.5 w-2.5 ml-0.5"><polygon points="5,3 19,12 5,21" /></svg>
                        </span>
                      </div>
                      {file.frames && file.frames.length > 1 && (
                        <span className="absolute bottom-0 right-0 rounded-tl bg-black/60 px-0.5 text-[8px] text-white">{file.frames.length}帧</span>
                      )}
                    </div>
                  ) : (
                    <div className="flex h-14 w-14 items-center justify-center rounded border bg-muted"><ImageIcon className="h-5 w-5 text-muted-foreground" /></div>
                  )}
                  <button onClick={(e) => { e.stopPropagation(); removeFile(i) }} className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-destructive-foreground opacity-0 transition-opacity group-hover:opacity-100">
                    <X className="h-2.5 w-2.5" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* 工具栏 */}
          <div className="flex flex-wrap items-center gap-1.5">
            <input ref={fileInputRef} type="file" accept="image/*,video/*" multiple className="hidden" onChange={handleFileSelect} />
            <Tip text="上传图片或视频">
              <Button variant="outline" size="sm" className="h-7 px-2 text-[11px]" onClick={() => fileInputRef.current?.click()}>
                <Paperclip className="h-3 w-3 mr-1" />附件
                {attachedFiles.length > 0 && <Badge variant="secondary" className="ml-1 h-4 px-1 text-[9px]">{attachedFiles.length}</Badge>}
              </Button>
            </Tip>
            <Tip text={isEnhancing ? '增强中...' : 'AI 增强提示词'}>
              <Button variant="secondary" size="sm" className="h-7 px-2 text-[11px]" onClick={handleEnhancePrompt} disabled={isEnhancing || isStreaming}>
                <Zap className={`h-3 w-3 mr-1 ${isEnhancing ? 'animate-pulse' : ''}`} />
                {isEnhancing ? '增强中...' : '增强'}
              </Button>
            </Tip>
            {prevInstruction && !isEnhancing && (
              <Tip text="撤销增强，恢复原文">
                <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={handleUndoEnhance}>
                  <RotateCcw className="h-3 w-3" />
                </Button>
              </Tip>
            )}
            <Tip text="选择预设模板">
              <Button variant="ghost" size="sm" className="h-7 px-2 text-[11px]" onClick={() => setShowTemplates(!showTemplates)}>
                <BookOpen className="h-3 w-3 mr-1" />模板
                {showTemplates ? <ChevronUp className="h-3 w-3 ml-0.5" /> : <ChevronDown className="h-3 w-3 ml-0.5" />}
              </Button>
            </Tip>
            {customInstruction.trim() && !showSaveInput && (
              <Tip text="将当前内容保存为模板">
                <Button variant="ghost" size="sm" className="h-7 px-2 text-[11px] text-muted-foreground" onClick={() => setShowSaveInput(true)}>
                  <Save className="h-3 w-3 mr-1" />存模板
                </Button>
              </Tip>
            )}
          </div>

          {showSaveInput && (
            <div className="flex gap-1.5">
              <input className="flex h-7 flex-1 rounded-md border bg-background px-2 text-xs" placeholder="模板名称" value={saveTemplateName} onChange={(e) => setSaveTemplateName(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleSaveTemplate()} />
              <Button size="sm" className="h-7 px-2 text-xs" onClick={handleSaveTemplate}>保存</Button>
              <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => setShowSaveInput(false)}><X className="h-3.5 w-3.5" /></Button>
            </div>
          )}

          {showTemplates && (
            <div className="flex flex-wrap gap-1.5 rounded-md border bg-muted/30 p-2">
              {templates.map((tpl) => (
                <div key={tpl.id} className="flex items-center gap-0.5">
                  <Badge variant="outline" className="cursor-pointer text-[10px] hover:bg-primary/10" onClick={() => handleApplyTemplate(tpl.content)}>{tpl.name}</Badge>
                  {!tpl.builtin && <button onClick={() => removeTemplate(tpl.id)} className="text-muted-foreground hover:text-destructive"><X className="h-2.5 w-2.5" /></button>}
                </div>
              ))}
            </div>
          )}

        {isEnhancing && (
            <div className="flex items-center gap-2 rounded-lg border border-primary/20 dark:border-primary/30 bg-primary/5 dark:bg-primary/10 px-3 py-2 text-[11px] text-primary">
              <Zap className="h-3.5 w-3.5 animate-pulse" />
              {attachedFiles.length > 0 ? '正在分析图片内容...' : '正在增强提示词...'}
            </div>
          )}
        </div>

        <Separator />

        {/* ── 4. 生成按钮 + 取消 ───────────────────────────── */}
        <div className="space-y-2">
          <div className="flex gap-2">
            <div className="flex-1">
              <GenerateButton isGenerating={isStreaming} hasGenerated={hasGenerated} onClick={handleGenerate} />
            </div>
            {isStreaming ? (
              <Tip text="取消当前生成">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-9 px-3 text-[11px] gap-1.5"
                  onClick={chatActions.cancel}
                >
                  <X className="h-3.5 w-3.5" />
                  取消
                </Button>
              </Tip>
            ) : (
              <Tip text={isFullFlow ? '执行中...' : '增强提示词 → 生成内容 → 自动填写'}>
                <Button
                  variant="default"
                  size="sm"
                  className="h-9 px-3 text-[11px] gap-1.5"
                  onClick={handleFullFlow}
                  disabled={isStreaming || isEnhancing || isFullFlow}
                >
                  <Sparkles className={`h-3.5 w-3.5 ${isFullFlow ? 'animate-pulse' : ''}`} />
                  {isFullFlow ? '全流程中...' : '一键全流程'}
                </Button>
              </Tip>
            )}
          </div>

          {/* Full-flow progress bar */}
          {isFullFlow && fullFlowStep && (
            <div className="animate-in fade-in slide-in-from-top-1 rounded-lg border bg-muted/30 px-3 py-2 duration-200">
              <div className="mb-1.5 flex items-center justify-between text-[10px] text-muted-foreground">
                <span>全流程进度</span>
                <span className="font-medium">
                  {fullFlowStep === 'enhance' ? '1/3' : fullFlowStep === 'generate' ? '2/3' : '3/3'}
                </span>
              </div>
              <div className="flex items-center gap-1">
                {(['enhance', 'generate', 'fill'] as const).map((step, i) => {
                  const stepIndex = fullFlowStep === 'enhance' ? 0 : fullFlowStep === 'generate' ? 1 : 2
                  const isDone = i < stepIndex
                  const isActive = i === stepIndex
                  const labels = { enhance: '增强', generate: '生成', fill: '填写' }
                  return (
                    <div key={step} className="flex items-center gap-1 flex-1 last:flex-none">
                      <div className="flex flex-1 items-center gap-1.5">
                        <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold transition-all duration-300 ${
                          isDone
                            ? 'bg-primary text-primary-foreground'
                            : isActive
                            ? 'bg-primary text-primary-foreground ring-2 ring-primary/30'
                            : 'bg-muted text-muted-foreground'
                        }`}>
                          {isDone ? <Check className="h-3 w-3" /> : i + 1}
                        </span>
                        <span className={`text-[9px] font-medium truncate transition-colors duration-300 ${
                          isDone ? 'text-primary' : isActive ? 'text-foreground' : 'text-muted-foreground'
                        }`}>
                          {labels[step]}
                        </span>
                      </div>
                      {i < 2 && (
                        <div className={`h-0.5 flex-1 rounded-full transition-colors duration-500 ${
                          isDone ? 'bg-primary' : 'bg-muted-foreground/20'
                        }`} />
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>

        {/* ── 5. 流式输出预览 ──────────────────────────────── */}
        {(isStreaming || isEnhancing) && (
          <>
          {streamingDraft && (
          <div className="animate-in fade-in slide-in-from-top-2 rounded-lg border bg-gradient-to-b from-muted/40 to-muted/10 dark:from-muted/50 dark:to-muted/20 p-3.5 duration-300">
            <div className="mb-2.5 flex items-center gap-2">
              <div className="flex items-center gap-1.5">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inset-0 animate-ping rounded-full bg-primary/50" />
                  <span className="relative h-2 w-2 rounded-full bg-primary" />
                </span>
                <span className="text-[11px] font-medium text-muted-foreground">
                  {isEnhancing ? 'AI 增强中' : 'AI 生成中'}
                </span>
              </div>
              {currentKeyInfo && (
                <Badge variant="outline" className="h-5 px-1.5 text-[9px] font-mono font-normal tracking-tight">
                  Key #{currentKeyInfo.id}
                </Badge>
              )}
            </div>
            <div className="relative">
              <p className="max-h-32 overflow-y-auto whitespace-pre-wrap break-words text-sm leading-relaxed">
                {streamingDraft}
                <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse rounded-full bg-primary align-middle" />
              </p>
            </div>
          </div>
          )}
          {!streamingDraft && currentKeyInfo && (
            <div className="flex items-center gap-2 rounded-lg border border-primary/10 dark:border-primary/20 bg-primary/5 dark:bg-primary/10 px-3 py-2 text-[11px] text-muted-foreground">
              <span className="relative flex h-2 w-2">
                <span className="absolute inset-0 animate-ping rounded-full bg-primary/40" />
                <span className="relative h-2 w-2 rounded-full bg-primary" />
              </span>
              正在使用 <Badge variant="outline" className="h-5 px-1.5 text-[9px] font-mono font-normal">Key #{currentKeyInfo.id}</Badge> 连接 AI...
            </div>
          )}
          </>
        )}

        {/* ── 6. 错误重试 ──────────────────────────────────── */}
        {chatError && !isStreaming && (
          <div className="animate-in fade-in flex items-center justify-between rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2.5">
            <div className="flex items-center gap-2 min-w-0">
              <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-destructive" />
              <span className="truncate text-xs text-destructive/80">{chatError}</span>
            </div>
            <Button variant="outline" size="sm" className="h-7 shrink-0 rounded-md px-2.5 text-[10px] text-destructive hover:bg-destructive/10" onClick={handleRetry}>
              <RotateCcw className="h-3 w-3 mr-1" />重试
            </Button>
          </div>
        )}

        {/* ── 7. 生成结果 ──────────────────────────────────── */}
        {lastResult && !isStreaming && (
          <div className="animate-in fade-in slide-in-from-top-2 space-y-2.5 rounded-lg border border-primary/20 dark:border-primary/30 bg-gradient-to-b from-primary/5 dark:from-primary/10 to-transparent p-3.5 duration-300">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold tracking-tight">生成结果</span>
              <div className="flex items-center gap-1">
                <Tip text="全部应用到表单">
                  <Button variant="ghost" size="sm" className="h-5 px-1.5 text-[10px] text-primary" onClick={handleApplyAll}>
                    <CheckCheck className="h-3 w-3 mr-0.5" />全部应用
                  </Button>
                </Tip>
                <Tip text="复制全部内容">
                  <Button variant="ghost" size="sm" className="h-5 w-5 p-0" onClick={handleCopy}><Copy className="h-3 w-3" /></Button>
                </Tip>
                <Tip text="查看历史记录">
                  <Button variant="ghost" size="sm" className="h-5 px-1.5 text-[10px]" onClick={() => setShowHistory(!showHistory)}>
                    <History className="h-3 w-3 mr-1" />历史
                  </Button>
                </Tip>
              </div>
            </div>

            {lastResult.title && (
              <div className="group flex items-center gap-2.5">
                <Badge variant="outline" className="h-5 w-11 shrink-0 justify-center rounded px-0 text-[9px] font-normal text-muted-foreground">标题</Badge>
                {editingField === 'title' ? (
                  <div className="flex flex-1 items-center gap-1">
                    <Input value={editValue} onChange={(e) => setEditValue(e.target.value)} className="h-7 text-xs flex-1 rounded-md" onKeyDown={(e) => { if (e.key === 'Enter') handleConfirmEdit(); if (e.key === 'Escape') handleCancelEdit() }} autoFocus />
                    <Button variant="ghost" size="sm" className="h-7 w-7 rounded-md p-0 text-green-600 hover:bg-green-50 dark:hover:bg-green-950" onClick={handleConfirmEdit}><Check className="h-3.5 w-3.5" /></Button>
                    <Button variant="ghost" size="sm" className="h-7 w-7 rounded-md p-0" onClick={handleCancelEdit}><X className="h-3.5 w-3.5" /></Button>
                  </div>
                ) : (
                  <>
                    <div className="flex-1 truncate text-sm font-medium [&_p]:inline [&_p]:m-0"><MarkdownContent content={lastResult.title} /></div>
                    <div className="flex items-center gap-0.5 opacity-0 transition-all duration-150 group-hover:opacity-100">
                      <Tip text="编辑标题">
                        <Button variant="ghost" size="sm" className="h-6 w-6 rounded-md p-0" onClick={() => handleStartEdit('title', lastResult.title)}>
                          <Pencil className="h-3 w-3" />
                        </Button>
                      </Tip>
                      <Tip text="单独应用标题">
                        <Button variant="ghost" size="sm" className="h-6 w-6 rounded-md p-0 text-primary hover:bg-primary/10" onClick={() => handleApplySingle('title')}>
                          <Check className="h-3 w-3" />
                        </Button>
                      </Tip>
                      <Tip text="优化标题">
                        <Button variant="ghost" size="sm" className="h-6 w-6 rounded-md p-0" onClick={() => handleOptimize('title')} disabled={optimizing === 'title'}>
                          <Wand2 className={`h-3 w-3 ${optimizing === 'title' ? 'animate-spin' : ''}`} />
                        </Button>
                      </Tip>
                    </div>
                  </>
                )}
              </div>
            )}
            {lastResult.desc && (
              <div className="group flex items-start gap-2.5">
                <Badge variant="outline" className="mt-0.5 h-5 w-11 shrink-0 justify-center rounded px-0 text-[9px] font-normal text-muted-foreground">{mode === 'video' ? '描述' : '内容'}</Badge>
                {editingField === 'desc' ? (
                  <div className="flex flex-1 flex-col gap-1.5">
                    <Textarea value={editValue} onChange={(e) => setEditValue(e.target.value)} className="min-h-[60px] text-xs rounded-md" onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleConfirmEdit(); if (e.key === 'Escape') handleCancelEdit() }} autoFocus />
                    <div className="flex items-center gap-1.5">
                      <Button variant="ghost" size="sm" className="h-6 rounded-md px-2 text-[10px] text-green-600 hover:bg-green-50 dark:hover:bg-green-950" onClick={handleConfirmEdit}><Check className="h-3 w-3 mr-0.5" />确认</Button>
                      <Button variant="ghost" size="sm" className="h-6 rounded-md px-2 text-[10px]" onClick={handleCancelEdit}>取消</Button>
                      <span className="ml-auto text-[9px] text-muted-foreground">Ctrl+Enter 确认</span>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="line-clamp-3 flex-1 text-sm leading-relaxed [&_p]:my-0"><MarkdownContent content={lastResult.desc} /></div>
                    <div className="flex shrink-0 items-center gap-0.5 opacity-0 transition-all duration-150 group-hover:opacity-100">
                      <Tip text={`编辑${mode === 'video' ? '描述' : '内容'}`}>
                        <Button variant="ghost" size="sm" className="h-6 w-6 rounded-md p-0" onClick={() => handleStartEdit('desc', lastResult.desc)}>
                          <Pencil className="h-3 w-3" />
                        </Button>
                      </Tip>
                      <Tip text={`单独应用${mode === 'video' ? '描述' : '内容'}`}>
                        <Button variant="ghost" size="sm" className="h-6 w-6 rounded-md p-0 text-primary hover:bg-primary/10" onClick={() => handleApplySingle('desc')}>
                          <Check className="h-3 w-3" />
                        </Button>
                      </Tip>
                      <Tip text={`优化${mode === 'video' ? '描述' : '内容'}`}>
                        <Button variant="ghost" size="sm" className="h-6 w-6 rounded-md p-0" onClick={() => handleOptimize('desc')} disabled={optimizing === 'desc'}>
                          <Wand2 className={`h-3 w-3 ${optimizing === 'desc' ? 'animate-spin' : ''}`} />
                        </Button>
                      </Tip>
                    </div>
                  </>
                )}
              </div>
            )}
            {lastResult.tags && (
              <div className="group flex items-center gap-2.5">
                <Badge variant="outline" className="h-5 w-11 shrink-0 justify-center rounded px-0 text-[9px] font-normal text-muted-foreground">标签</Badge>
                {editingField === 'tags' ? (
                  <div className="flex flex-1 items-center gap-1">
                    <Input value={editValue} onChange={(e) => setEditValue(e.target.value)} className="h-7 text-xs flex-1 rounded-md" onKeyDown={(e) => { if (e.key === 'Enter') handleConfirmEdit(); if (e.key === 'Escape') handleCancelEdit() }} autoFocus />
                    <Button variant="ghost" size="sm" className="h-7 w-7 rounded-md p-0 text-green-600 hover:bg-green-50 dark:hover:bg-green-950" onClick={handleConfirmEdit}><Check className="h-3.5 w-3.5" /></Button>
                    <Button variant="ghost" size="sm" className="h-7 w-7 rounded-md p-0" onClick={handleCancelEdit}><X className="h-3.5 w-3.5" /></Button>
                  </div>
                ) : (
                  <>
                    <span className="flex-1 truncate text-sm">{lastResult.tags}</span>
                    <div className="flex items-center gap-0.5 opacity-0 transition-all duration-150 group-hover:opacity-100">
                      <Tip text="编辑标签">
                        <Button variant="ghost" size="sm" className="h-6 w-6 rounded-md p-0" onClick={() => handleStartEdit('tags', lastResult.tags)}>
                          <Pencil className="h-3 w-3" />
                        </Button>
                      </Tip>
                      <Tip text="单独应用标签">
                        <Button variant="ghost" size="sm" className="h-6 w-6 rounded-md p-0 text-primary hover:bg-primary/10" onClick={() => handleApplySingle('tags')}>
                          <Check className="h-3 w-3" />
                        </Button>
                      </Tip>
                      <Tip text="优化标签">
                        <Button variant="ghost" size="sm" className="h-6 w-6 rounded-md p-0" onClick={() => handleOptimize('tags')} disabled={optimizing === 'tags'}>
                          <Wand2 className={`h-3 w-3 ${optimizing === 'tags' ? 'animate-spin' : ''}`} />
                        </Button>
                      </Tip>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── 8. 历史记录 ──────────────────────────────────── */}
        {showHistory && entries.length > 0 && (
          <div className="animate-in fade-in max-h-40 space-y-1 overflow-y-auto rounded-md border p-2">
            <div className="mb-1 flex items-center justify-between">
              <span className="text-[10px] font-medium text-muted-foreground">历史记录</span>
              <Badge variant="outline" className="h-4 px-1 text-[9px]">{entries.length}</Badge>
            </div>
            {entries.slice(0, 10).map((entry) => (
              <div key={entry.id} className="group flex cursor-pointer items-center gap-1.5 rounded px-1.5 py-1 text-[11px] hover:bg-muted" onClick={() => handleApplyHistory(entry)}>
                <Badge variant="secondary" className="h-3.5 shrink-0 px-1 text-[8px]">{entry.platform}</Badge>
                <span className="flex-1 truncate">{entry.parsed.title || entry.content.slice(0, 30)}</span>
                <span className="shrink-0 text-[9px] text-muted-foreground">{new Date(entry.timestamp).toLocaleTimeString()}</span>
                <button onClick={(e) => { e.stopPropagation(); setDeleteTarget({ type: 'history', id: entry.id }) }} className="shrink-0 text-muted-foreground opacity-0 transition-opacity hover:text-destructive group-hover:opacity-100">
                  <Trash2 className="h-2.5 w-2.5" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* ── 9. 底部提示 ──────────────────────────────────── */}
        <p className="text-center text-[10px] text-muted-foreground">
          AI 生成内容仅供参考，请根据实际情况调整后再发布
        </p>

      {/* ── Lightbox ──────────────────────────────────────── */}
      {previewIndex !== null && attachedFiles[previewIndex] && createPortal(
        <div
          className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/80 p-8"
          onClick={() => setPreviewIndex(null)}
          onKeyDown={(e) => {
            if (e.key === 'Escape') setPreviewIndex(null)
            if (e.key === 'ArrowLeft' && previewIndex > 0) setPreviewIndex(previewIndex - 1)
            if (e.key === 'ArrowRight' && previewIndex < attachedFiles.length - 1) setPreviewIndex(previewIndex + 1)
          }}
          tabIndex={-1}
          ref={(el) => { if (el) el.focus() }}
        >
          <button className="absolute top-4 right-4 flex h-9 w-9 items-center justify-center rounded-full bg-white/10 text-white transition-colors hover:bg-white/20" onClick={(e) => { e.stopPropagation(); setPreviewIndex(null) }}><X className="h-5 w-5" /></button>
          {previewIndex > 0 && <button className="absolute left-4 flex h-9 w-9 items-center justify-center rounded-full bg-white/10 text-white transition-colors hover:bg-white/20" onClick={(e) => { e.stopPropagation(); setPreviewIndex(previewIndex - 1) }}><ChevronDown className="h-5 w-5 -rotate-90" /></button>}
          {previewIndex < attachedFiles.length - 1 && <button className="absolute right-16 flex h-9 w-9 items-center justify-center rounded-full bg-white/10 text-white transition-colors hover:bg-white/20" onClick={(e) => { e.stopPropagation(); setPreviewIndex(previewIndex + 1) }}><ChevronDown className="h-5 w-5 rotate-90" /></button>}
          <div className="max-h-[80vh] max-w-[90vw]" onClick={(e) => e.stopPropagation()}>
            {attachedFiles[previewIndex].type.startsWith('image/') ? (
              <img src={attachedFiles[previewIndex].dataUrl} alt="" className="max-h-[80vh] rounded object-contain" />
            ) : (
              <video src={attachedFiles[previewIndex].dataUrl} controls autoPlay className="max-h-[80vh] rounded" />
            )}
          </div>
          <div className="absolute bottom-4 flex items-center gap-2 text-sm text-white/80">
            <span>{attachedFiles[previewIndex].name}</span>
            {attachedFiles.length > 1 && <span className="text-white/50">({previewIndex + 1}/{attachedFiles.length})</span>}
          </div>
        </div>,
        document.body,
      )}

      {/* ── 删除确认 ──────────────────────────────────────── */}
      <AlertDialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              {deleteTarget?.type === 'key' ? '确定要删除全部 API Key 吗？删除后将无法使用 AI 功能。'
                : deleteTarget?.type === 'key_single' ? '确定要删除这个 API Key 吗？'
                : '确定要删除这条历史记录吗？'}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete}>确认</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
