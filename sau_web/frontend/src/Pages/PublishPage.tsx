import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PageHeader } from '@/components/ui/page-header'
import { Badge } from '@/components/ui/index'
import { useAccounts } from '../hooks/useTasks'
import { useAccountGroups } from '../hooks/useAccountGroups'
import { usePublishStore } from '../stores/publishStore'
import { PublishAiSidebar, MobileAiDrawer } from '@/components/AiRightPanel'
import { useMobileDrawer } from '@/hooks/useMobileDrawer'
import { Image as ImageIcon, Send, Video, Flag, RefreshCw, Users, Layers, Sparkles } from 'lucide-react'
import { VideoForm, type VideoFormHandle } from '../features/publish/VideoForm'
import { NoteForm, type NoteFormHandle } from '../features/publish/NoteForm'
import { PublishSuccessBanner } from '../features/publish/PublishSuccessBanner'
import { GroupPublishSelector, type GroupSelection } from '../features/publish/GroupPublishSelector'
import { PLATFORMS } from '../api/client'
import { formatTaskId } from '../features/publish/shared'
import type { FormPreviewData } from '../features/publish/PublishPreview'

/**
 * Two-column publish-center layout.
 *
 * Below lg (default 1024px): form spans full width, AI assistant is hidden
 * and surfaced via a floating action button → bottom-sheet drawer. We use
 * lg (not md=768) so the form keeps enough horizontal room for its
 * multi-select platform picker, dropzone, and schedule picker.
 *
 * lg and up: form takes the left 60%, AI assistant takes the right 40%
 * (resolves to `grid-cols-[3fr_2fr]`). The preview that used to live in
 * its own aside is now integrated into the AI sidebar as a collapsible
 * section at the bottom of the panel.
 */
export default function PublishPage() {
  const navigate = useNavigate()
  const { data: accountOptions = [], refetch: refetchAccounts } = useAccounts()
  const { data: groups = [] } = useAccountGroups()
  const lastTaskIds = usePublishStore((s) => s.lastTaskIds)
  const submitSuccess = usePublishStore((s) => s.submitSuccess)
  const setLastTaskIds = usePublishStore((s) => s.setLastTaskIds)
  const setSubmitSuccess = usePublishStore((s) => s.setSubmitSuccess)

  const [mode, setMode] = useState<'video' | 'note'>('video')
  const [previewData, setPreviewData] = useState<FormPreviewData>({ title: '', desc: '', tags: '', fileUrls: [], fileType: null })
  const [groupSelection, setGroupSelection] = useState<GroupSelection | null>(null)

  const videoFormRef = useRef<VideoFormHandle>(null)
  const noteFormRef = useRef<NoteFormHandle>(null)
  const navigateTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Mobile bottom-drawer toggle. Above the md breakpoint the inline
  // PublishAiSidebar takes over and the hook auto-closes the drawer.
  const { isMobile, isOpen, open, close } = useMobileDrawer()

  // Clear pending auto-navigate on unmount.
  useEffect(() => {
    return () => {
      if (navigateTimerRef.current) clearTimeout(navigateTimerRef.current)
    }
  }, [])

  const handleGoToTasks = useCallback(() => {
    if (navigateTimerRef.current) clearTimeout(navigateTimerRef.current)
    navigate('/tasks')
  }, [navigate])

  const scheduleNavigateAfterSubmit = useCallback(() => {
    if (navigateTimerRef.current) clearTimeout(navigateTimerRef.current)
    navigateTimerRef.current = setTimeout(() => navigate('/tasks'), 1500)
  }, [navigate])

  const handleVideoSuccess = useCallback(
    (info: { count: number; taskIds: string[]; failedCount: number; mode: '视频' }) => {
      setLastTaskIds(info.taskIds)
      setSubmitSuccess({
        count: info.count,
        mode: info.mode,
        taskIds: info.taskIds,
      })
      scheduleNavigateAfterSubmit()
    },
    [setLastTaskIds, setSubmitSuccess, scheduleNavigateAfterSubmit],
  )

  const handleNoteSuccess = useCallback(
    (info: { count: number; taskIds: string[]; failedCount: number; mode: '图文' }) => {
      setLastTaskIds(info.taskIds)
      setSubmitSuccess({
        count: info.count,
        mode: info.mode,
        taskIds: info.taskIds,
      })
      scheduleNavigateAfterSubmit()
    },
    [setLastTaskIds, setSubmitSuccess, scheduleNavigateAfterSubmit],
  )

  const handleVideoError = useCallback(() => {
    /* form already toasted */
  }, [])
  const handleNoteError = useCallback(() => {
    /* form already toasted */
  }, [])

  const handleAiGenerated = useCallback(
    (result: { title: string; desc: string; tags: string }) => {
      if (mode === 'video') videoFormRef.current?.applyAiResult(result)
      else noteFormRef.current?.applyAiResult(result)
    },
    [mode],
  )

  const handleFormChange = useCallback((data: FormPreviewData) => {
    setPreviewData(data)
  }, [])

  return (
    <div className="p-6">
      <PageHeader
        title="发布中心"
        description="发布视频或图文到多个平台"
        icon={<Send className="h-5 w-5 text-muted-foreground" />}
      />

      <PublishSuccessBanner info={submitSuccess} onGoToTasks={handleGoToTasks} />

      {/* ── Overview stats ──────────────────────────────────── */}
      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="flex items-center gap-3 card-refined px-4 py-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
            <Users className="h-4 w-4 text-primary" />
          </div>
          <div>
            <p className="text-lg font-bold leading-none">{accountOptions.length}</p>
            <p className="text-[11px] text-muted-foreground mt-0.5">可用账号</p>
          </div>
        </div>
        <div className="flex items-center gap-3 card-refined px-4 py-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-500/10">
            <Layers className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div>
            <p className="text-lg font-bold leading-none">{PLATFORMS.length}</p>
            <p className="text-[11px] text-muted-foreground mt-0.5">支持平台</p>
          </div>
        </div>
        <div className="flex items-center gap-3 card-refined px-4 py-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-500/10">
            <Flag className="h-4 w-4 text-amber-600 dark:text-amber-400" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <p className="text-lg font-bold leading-none">
                {lastTaskIds.length > 0 ? lastTaskIds.length : '—'}
              </p>
              {lastTaskIds.length > 0 && (
                <div className="flex items-center gap-1 min-w-0 overflow-hidden">
                  {lastTaskIds.slice(0, 2).map((id) => (
                    <Badge key={id} variant="secondary" className="text-[10px] h-4 px-1.5 shrink-0">
                      {formatTaskId(id)}
                    </Badge>
                  ))}
                  {lastTaskIds.length > 2 && (
                    <span className="text-[10px] text-muted-foreground shrink-0">+{lastTaskIds.length - 2}</span>
                  )}
                </div>
              )}
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">最近提交</p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="h-9 w-9 p-0 text-muted-foreground hover:text-foreground shrink-0"
            onClick={() => void refetchAccounts()}
            aria-label="刷新账号列表"
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* ── Main content: form + AI sidebar (60/40 split at lg+) ── */}
      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[3fr_2fr]">
        {/* Left: form */}
        <div className="min-w-0">
          <Tabs
            value={mode}
            onValueChange={(v) => {
              setMode(v as 'video' | 'note')
              setGroupSelection(null)
            }}
          >
            <TabsList className="w-full grid grid-cols-2 mb-4">
              <TabsTrigger value="video" className="gap-2 transition-colors duration-150 data-[state=active]:bg-card/80 data-[state=active]:shadow-sm">
                <Video className="h-4 w-4" />
                发布视频
              </TabsTrigger>
              <TabsTrigger value="note" className="gap-2 transition-colors duration-150 data-[state=active]:bg-card/80 data-[state=active]:shadow-sm">
                <ImageIcon className="h-4 w-4" />
                发布图文
              </TabsTrigger>
            </TabsList>

            {/* ── Group selector ──── */}
            <GroupPublishSelector
              groups={groups}
              mode={mode}
              value={groupSelection}
              onChange={setGroupSelection}
            />

            <div className="mt-4">
              <TabsContent value="video" className="mt-0 data-[state=inactive]:hidden">
                <VideoForm
                  ref={videoFormRef}
                  groupSelection={groupSelection}
                  onSuccess={handleVideoSuccess}
                  onError={handleVideoError}
                  onFormChange={handleFormChange}
                />
              </TabsContent>
              <TabsContent value="note" className="mt-0 data-[state=inactive]:hidden">
                <NoteForm
                  ref={noteFormRef}
                  groupSelection={groupSelection}
                  onSuccess={handleNoteSuccess}
                  onError={handleNoteError}
                  onFormChange={handleFormChange}
                />
              </TabsContent>
            </div>
          </Tabs>
        </div>

        {/* Right (lg+): sticky AI sidebar with collapsible preview */}
        <div className="hidden lg:block lg:sticky lg:top-6 lg:self-start">
          <div className="h-[calc(100vh-9rem)] min-h-[480px] flex flex-col">
            <PublishAiSidebar
              mode={mode}
              platform={groupSelection?.platforms[0] ?? ''}
              onGenerated={handleAiGenerated}
              previewMode={mode}
              previewData={previewData}
              formRef={mode === 'video' ? videoFormRef : noteFormRef}
            />
          </div>
        </div>
      </div>

      {/* ── Mobile (<lg): floating action button + drawer ───────────── */}
      {isMobile && (
        <Button
          onClick={open}
          size="lg"
          className="fixed bottom-4 right-4 z-40 h-11 rounded-full px-4 shadow-lg shadow-primary/25"
          data-testid="mobile-ai-trigger"
          aria-label="打开 AI 助手"
        >
          <Sparkles className="h-4 w-4 mr-1.5" />
          AI 助手
        </Button>
      )}
      <MobileAiDrawer open={isMobile && isOpen} onClose={close}>
        <PublishAiSidebar
          mode={mode}
          platform={groupSelection?.platforms[0] ?? ''}
          onGenerated={handleAiGenerated}
          previewMode={mode}
          previewData={previewData}
          formRef={mode === 'video' ? videoFormRef : noteFormRef}
        />
      </MobileAiDrawer>
    </div>
  )
}
