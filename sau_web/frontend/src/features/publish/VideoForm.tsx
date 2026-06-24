import {
  forwardRef,
  memo,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react'
import type { FormPreviewData } from './PublishPreview'
import type { GroupSelection } from './GroupPublishSelector'
import type { FormHandle } from '@/lib/chat/chatFormBridge'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
  Button,
  Card,
  CardContent,
  Checkbox,
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Textarea,
} from '@/components/ui/index'
import { cn } from '@/lib/utils'
import { PlatformIcon } from '@/components/ui/platform-icon'
import { TagInput } from '@/components/ui/tag-input'
import { motion } from 'motion/react'
import { useToast } from '@/components/ui/toast'
import {
  api,
  PLATFORMS,
} from '../../api/client'
import {
  FilePlus,
  Inbox,
  Loader2,
  Settings,
  Wand2,
  X,
} from 'lucide-react'
import {
  effectiveMaxTags,
  platformTagLabel,
  SectionHeader,
} from './shared'
import { SchedulePicker } from './SchedulePicker'
import { formatFileSize } from '@/lib/features'
import { Tip } from '@/lib/tip'

/**
 * Staggered entrance for each animated card in the form. `custom={index}` (0..N)
 * cascades the cards from top to bottom.
 */
const cardVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      type: 'spring' as const,
      stiffness: 320,
      damping: 28,
      delay: i * 0.06,
    },
  }),
}

const springTransition = { type: 'spring' as const, stiffness: 400, damping: 30 }

/** Bilibili zone (分区) options surfaced in the advanced-options card. */
const BILIBILI_TIDS = [
  { id: 1, name: '动画' },
  { id: 13, name: '番剧' },
  { id: 168, name: '国创' },
  { id: 3, name: '音乐' },
  { id: 129, name: '舞蹈' },
  { id: 4, name: '游戏' },
  { id: 17, name: '单机游戏' },
  { id: 36, name: '科技' },
  { id: 188, name: '数码' },
  { id: 234, name: '美食' },
  { id: 223, name: '汽车' },
  { id: 155, name: '时尚' },
  { id: 202, name: '资讯' },
  { id: 181, name: '影视' },
  { id: 177, name: '纪录片' },
  { id: 23, name: '电影' },
  { id: 11, name: '电视剧' },
] as const

/** Imperative handle — parent calls `videoFormRef.current?.applyAiResult(r)`.
 *  Aliased to `FormHandle` from the chat bridge so chatAction hooks can read
 *  the same contract. `getFormSnapshot` lets the chat pipeline capture the
 *  current form contents at send time so the AI sees the user's latest edits.
 */
export type VideoFormHandle = FormHandle

type VideoFormProps = {
  /**
   * Pre-resolved group selection from GroupPublishSelector.
   * The form uses the group's cookie files directly for submission.
   */
  groupSelection?: GroupSelection | null
  /**
   * Fired on every successful submission (no thrown exceptions). Reports both
   * completed and failed task counts so the parent can show the success
   * banner / toast without parsing individual results.
   */
  onSuccess: (info: { count: number; taskIds: string[]; failedCount: number; mode: '视频' }) => void
  /** Internal exceptions (network failure, etc). The parent toasts accordingly. */
  onError: (label: '视频') => void
  /** Called on every form-change so the parent can render a live preview. */
  onFormChange?: (data: FormPreviewData) => void
}

/**
 * Video publishing form — content card (素材) + advanced options accordion,
 * stacked as animated cards. The advanced accordion holds the schedule picker,
 * headless toggle, and platform-specific fields (Douyin/Bilibili/Tencent).
 *
 * Owns 16+ fields locally so typing never re-renders the rest of PublishPage.
 *
 * Memoized because PublishPage's parent re-renders on mode toggle and on
 * AI-sidebar state changes; both pre-extraction triggered costly re-renders
 * throughout PublishPage.
 */
export const VideoForm = memo(
  forwardRef<VideoFormHandle, VideoFormProps>(function VideoForm(
    { groupSelection, onSuccess, onError, onFormChange },
    ref,
  ) {
    const { addToast } = useToast()

    const [title, setTitle] = useState('')
    const [desc, setDesc] = useState('')
    const [tags, setTags] = useState('')
    const [schedule, setSchedule] = useState('')
    const [headless, setHeadless] = useState(true)
    const [thumbnail, setThumbnail] = useState('')
    const [thumbnailLandscape, setThumbnailLandscape] = useState('')
    const [thumbnailPortrait, setThumbnailPortrait] = useState('')
    const [productLink, setProductLink] = useState('')
    const [productTitle, setProductTitle] = useState('')
    const [tid, setTid] = useState<number | undefined>()
    const [shortTitle, setShortTitle] = useState('')
    const [category, setCategory] = useState('')
    const [isDraft, setIsDraft] = useState(false)
    const [enhancingField, setEnhancingField] = useState<'title' | 'desc' | null>(null)

    const fileRef = useRef<File | null>(null)
    const [fileInfo, setFileInfo] = useState<{ name: string; size: number } | null>(null)
    const [dragOver, setDragOver] = useState(false)
    const [submitting, setSubmitting] = useState(false)

    const platformLabelMap = useMemo(
      () => Object.fromEntries(PLATFORMS.map((p) => [p.value, p.label])),
      [],
    )

    /** Currently selected/active platforms for conditional field rendering. */
    const activePlatforms = useMemo(
      () => new Set(groupSelection?.platforms ?? []),
      [groupSelection],
    )
    const hasDouyin = activePlatforms.has('douyin')
    const hasBilibili = activePlatforms.has('bilibili')
    const hasTencent = activePlatforms.has('tencent')
    const hasAnyPlatformSpecific = hasDouyin || hasBilibili || hasTencent

    const OPTIMIZE_MODEL = 'google/gemma-3-1b-it:free'

    const enhanceField = useCallback(async (field: 'title' | 'desc') => {
      const value = field === 'title' ? title : desc
      if (!value.trim()) return
      setEnhancingField(field)
      const partName = field === 'title' ? '标题' : '视频简介'
      const systemPrompt = `你是一个文案优化助手。请对用户提供的${partName}进行润色优化。

严格规则：
1. 只基于原文优化，不得添加原文中没有的新信息、新观点或新内容
2. 可以优化：用词精准度、语句流畅度、排版格式、标点符号
3. 不得改变原文的核心含义和关键信息
4. 去除明显的 AI 生成痕迹，使文案读起来像人工撰写
5. 只返回优化后的${partName}内容，不要添加任何解释、前缀或后缀`
      const messages = [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: value },
      ]
      let enhanced = ''
      try {
        await api.generateMessagesStream(
          { messages, model: OPTIMIZE_MODEL },
          (chunk) => { enhanced += chunk },
          (final) => {
            const result = (final || enhanced).trim()
            if (result) {
              if (field === 'title') setTitle(result)
              else setDesc(result)
              addToast(`${partName}已优化`, 'success')
            }
            setEnhancingField(null)
          },
          (err) => {
            setEnhancingField(null)
            addToast(err || '优化失败', 'error')
          },
        )
      } catch {
        setEnhancingField(null)
        addToast('优化请求失败', 'error')
      }
    }, [title, desc, addToast])

    /**
     * Stable imperative handle. Setters returned by useState are reference-
     * stable across renders, so listing them explicitly silences any
     * `react-hooks/exhaustive-deps` lint warnings without changing behavior.
     */
    useImperativeHandle(
      ref,
      () => ({
        applyAiResult(result) {
          if (result.title) setTitle(result.title)
          if (result.desc) setDesc(result.desc)
          if (result.tags) setTags(result.tags)
        },
        getFormSnapshot: () => ({ title, desc, tags }),
      }),
      [setTitle, setDesc, setTags, title, desc, tags],
    )

    /**
     * Object URL lifecycle: re-creates whenever the chosen file changes,
     * and revokes on unmount or before the next allocation.
     */
    const previewUrl = useMemo(
      () => (fileRef.current ? URL.createObjectURL(fileRef.current) : null),
      [fileInfo],
    )
    useEffect(() => {
      return () => {
        if (previewUrl) URL.revokeObjectURL(previewUrl)
      }
    }, [previewUrl])

    /** Report form state upward for the live preview panel. */
    // Mirror the parent callback through a ref so this effect's dep array
    // stays focused on the form fields only. (The current `handleFormChange`
    // in PublishPage is `useCallback([])` and therefore stable; this pattern
    // is defensive — it guarantees the effect never re-fires spuriously if a
    // future refactor accidentally binds the callback to reactive state.)
    const onFormChangeRef = useRef(onFormChange)
    useEffect(() => {
      onFormChangeRef.current = onFormChange
    }, [onFormChange])

    useEffect(() => {
      const handler = onFormChangeRef.current
      if (!handler) return
      const urls: string[] = []
      if (previewUrl) urls.push(previewUrl)
      if (thumbnailPortrait) urls.push(thumbnailPortrait)
      if (thumbnailLandscape) urls.push(thumbnailLandscape)
      if (thumbnail) urls.push(thumbnail)
      handler({
        title: title.trim(),
        desc: desc.trim(),
        tags,
        fileUrls: urls,
        fileType: fileInfo ? 'video' : null,
      })
    }, [title, desc, tags, previewUrl, thumbnailPortrait, thumbnailLandscape, thumbnail, fileInfo])

    const clearAll = useCallback(() => {
      setTitle('')
      setDesc('')
      setTags('')
      setSchedule('')
      setThumbnail('')
      setThumbnailLandscape('')
      setThumbnailPortrait('')
      setProductLink('')
      setProductTitle('')
      setTid(undefined)
      setShortTitle('')
      setCategory('')
      setIsDraft(false)
      setFileInfo(null)
      fileRef.current = null
    }, [])

    const submit = useCallback(async () => {
      if (!groupSelection?.platforms.length) {
        addToast('请先在上方选择发布账号组和平台', 'warning')
        return
      }
      if (!fileRef.current) {
        addToast('请选择视频文件', 'warning')
        return
      }
      if (!title.trim()) {
        addToast('请输入标题', 'warning')
        return
      }

      setSubmitting(true)
      try {
        const tasks = groupSelection.mappings
          .filter((m) => groupSelection.platforms.includes(m.platform))
          .map((mapping) =>
            api
              .uploadVideo({
                platform: mapping.platform,
                account: mapping.cookieFile,
                title,
                file: fileRef.current!,
                desc: desc || undefined,
                tags: tags || undefined,
                schedule: schedule || undefined,
                headless: String(headless),
                thumbnail: thumbnail || undefined,
                thumbnail_landscape: thumbnailLandscape || undefined,
                thumbnail_portrait: thumbnailPortrait || undefined,
                product_link: productLink || undefined,
                product_title: productTitle || undefined,
                tid,
                short_title: shortTitle || undefined,
                category: category || undefined,
                is_draft: isDraft ? 'true' : undefined,
              })
              .then((res) => ({
                platform: mapping.platform,
                accountKey: `${mapping.platform}::${mapping.cookieFile}`,
                success: res.success,
                taskId: res.data?.task_id,
              })),
          )

        const results = await Promise.all(tasks)
        const ids: string[] = []
        results.forEach((item) => {
          if (item.success && item.taskId) ids.push(item.taskId)
        })

        const failed = results.filter((item) => !item.success)
        if (failed.length) {
          addToast(`有 ${failed.length} 个任务提交失败`, 'error')
        } else {
          addToast(`已提交 ${results.length} 个视频上传任务`, 'success')
        }
        clearAll()
        onSuccess({ count: results.length, taskIds: ids, failedCount: failed.length, mode: '视频' })
      } catch {
        addToast('视频请求失败，请检查后端连接', 'error')
        onError('视频')
      } finally {
        setSubmitting(false)
      }
    }, [
      groupSelection,
      title,
      desc,
      tags,
      schedule,
      headless,
      thumbnail,
      thumbnailLandscape,
      thumbnailPortrait,
      productLink,
      productTitle,
      tid,
      shortTitle,
      category,
      isDraft,
      addToast,
      clearAll,
      onSuccess,
      onError,
    ])

    return (
      <>
        {/* ── 内容素材 ─────────────────────────────────────────── */}
        <motion.div
          custom={0}
          variants={cardVariants}
          initial="hidden"
          animate="visible"
        >
          <Card className="card-refined">
            <CardContent className="p-5 space-y-4">
              <SectionHeader icon={<FilePlus className="h-4 w-4" />} title="内容素材" />
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>视频文件</Label>
                  <div
                    className={cn(
                      'flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-5 transition-colors cursor-pointer',
                      dragOver && !fileInfo
                        ? 'border-primary bg-primary/10'
                        : fileInfo
                          ? 'border-primary/50 bg-primary/5'
                          : 'border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/50',
                    )}
                    onClick={() => document.getElementById('video-file-input')?.click()}
                    onDragOver={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      setDragOver(true)
                    }}
                    onDragLeave={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      if (!e.currentTarget.contains(e.relatedTarget as Node)) {
                        setDragOver(false)
                      }
                    }}
                    onDrop={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      setDragOver(false)
                      const file = e.dataTransfer.files?.[0]
                      if (file && file.type.startsWith('video/')) {
                        fileRef.current = file
                        setFileInfo({ name: file.name, size: file.size })
                      }
                    }}
                  >
                    {fileInfo ? (
                      <motion.div
                        key={fileInfo.name + fileInfo.size}
                        className="w-full space-y-3"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={springTransition}
                      >
                        <div className="relative rounded-lg overflow-hidden bg-black/70 group/video">
                          <video
                            src={previewUrl ?? undefined}
                            controls
                            className="w-full max-h-[360px] object-contain"
                            preload="metadata"
                          >
                            您的浏览器不支持视频预览
                          </video>
                          <div className="absolute top-2 right-2 flex gap-1.5 opacity-0 group-hover/video:opacity-100 transition-opacity">
                            <Button
                              variant="secondary"
                              size="icon"
                              className="h-7 w-7 bg-black/60 hover:bg-black/80 text-white border-0"
                              onClick={(e) => {
                                e.stopPropagation()
                                setFileInfo(null)
                                fileRef.current = null
                              }}
                            >
                              <X className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </div>
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <span className="font-medium text-foreground/80 truncate max-w-[200px]">
                            {fileInfo.name}
                          </span>
                          <span>{formatFileSize(fileInfo.size)}</span>
                        </div>
                      </motion.div>
                    ) : (
                      <>
                        <Inbox className="h-10 w-10 text-primary mb-2" />
                        <p className="text-sm text-muted-foreground">
                          点击此区域或拖拽视频文件到此处上传
                        </p>
                        <p className="text-xs text-muted-foreground/60 mt-1">
                          支持 MP4 / MOV / AVI 等常见格式
                        </p>
                      </>
                    )}
                  </div>
                  <input
                    id="video-file-input"
                    type="file"
                    accept="video/*"
                    className="hidden"
                    onChange={(e) => {
                      const file = e.target.files?.[0]
                      if (file) {
                        fileRef.current = file
                        setFileInfo({ name: file.name, size: file.size })
                      }
                    }}
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>标题</Label>
                    <div className="flex items-center gap-1.5">
                      <Tip text="AI 优化标题">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 rounded-md p-0"
                          onClick={() => enhanceField('title')}
                          disabled={enhancingField !== null || !title.trim()}
                        >
                          {enhancingField === 'title' ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <Wand2 className="h-3 w-3" />
                          )}
                        </Button>
                      </Tip>
                      <span className="text-[11px] text-muted-foreground tabular-nums">
                        {title.length}/100
                      </span>
                    </div>
                  </div>
                  <Input
                    placeholder="请输入视频标题（建议 6-20 字）"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    maxLength={100}
                  />
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="video-desc">视频简介</Label>
                      <Tip text="AI 优化简介">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 rounded-md p-0"
                          onClick={() => enhanceField('desc')}
                          disabled={enhancingField !== null || !desc.trim()}
                        >
                          {enhancingField === 'desc' ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <Wand2 className="h-3 w-3" />
                          )}
                        </Button>
                      </Tip>
                    </div>
                    <Textarea
                      id="video-desc"
                      className="min-h-[90px]"
                      placeholder="补充视频简介、背景说明或发布备注"
                      value={desc}
                      onChange={(e) => setDesc(e.target.value)}
                      maxLength={1000}
                    />
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label>标签</Label>
                      <span className="text-[11px] text-muted-foreground">
                        {platformTagLabel([...activePlatforms])}
                      </span>
                    </div>
                    <TagInput
                      placeholder="按 Enter 添加标签（# 可省略）"
                      value={tags}
                      onChange={(val) => setTags(val)}
                      maxTags={effectiveMaxTags([...activePlatforms])}
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* ── 高级选项 (collapsed by default) ───────────────────── */}
        <motion.div
          custom={1}
          variants={cardVariants}
          initial="hidden"
          animate="visible"
        >
          <Card className="card-refined overflow-hidden">
            <Accordion type="single" collapsible>
              <AccordionItem value="advanced" className="border-b-0">
                <AccordionTrigger className="px-5 py-3 hover:no-underline">
                  <div className="flex items-center gap-2">
                    <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary/10 text-primary">
                      <Settings className="h-3.5 w-3.5" />
                    </div>
                    <span className="text-sm font-semibold">高级选项</span>
                    {(thumbnail ||
                      thumbnailLandscape ||
                      thumbnailPortrait ||
                      schedule ||
                      hasAnyPlatformSpecific) && (
                      <span className="ml-1 h-1.5 w-1.5 rounded-full bg-primary" />
                    )}
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-5 pb-5">
                  {/* ── 通用行为: 定时发布 + 无头模式 ── */}
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 pb-4 border-b border-border/30">
                    <SchedulePicker value={schedule} onChange={setSchedule} />
                    <div className="flex items-center gap-2 self-end pb-1">
                      <Checkbox
                        id="video-headless"
                        checked={headless}
                        onCheckedChange={(checked) => setHeadless(checked === true)}
                      />
                      <Label htmlFor="video-headless" className="text-xs text-muted-foreground">
                        无头模式（不显示浏览器窗口）
                      </Label>
                    </div>
                  </div>

                  {/* ── 通用封面字段 ── */}
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 mt-4">
                    <div className="space-y-1.5">
                      <Label className="text-xs">封面地址</Label>
                      <Input
                        placeholder="URL 或 Data URI"
                        value={thumbnail}
                        onChange={(e) => setThumbnail(e.target.value)}
                        className="h-8 text-xs"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label className="text-xs">横版封面 (4:3)</Label>
                      <Input
                        placeholder="URL 或 Data URI"
                        value={thumbnailLandscape}
                        onChange={(e) => setThumbnailLandscape(e.target.value)}
                        className="h-8 text-xs"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label className="text-xs">竖版封面 (3:4)</Label>
                      <Input
                        placeholder="URL 或 Data URI"
                        value={thumbnailPortrait}
                        onChange={(e) => setThumbnailPortrait(e.target.value)}
                        className="h-8 text-xs"
                      />
                    </div>
                  </div>

                  {/* ── 平台特定字段: 抖音 ── */}
                  {hasDouyin && (
                    <div className="mt-4 pt-4 border-t border-border/30">
                      <div className="flex items-center gap-1.5 mb-2">
                        <PlatformIcon platform="douyin" className="h-3 w-3" />
                        <span className="text-[11px] font-semibold text-muted-foreground">
                          抖音专属
                        </span>
                      </div>
                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                        <div className="space-y-1.5">
                          <Label className="text-xs">商品链接</Label>
                          <Input
                            placeholder="https://"
                            value={productLink}
                            onChange={(e) => setProductLink(e.target.value)}
                            className="h-8 text-xs"
                          />
                        </div>
                        <div className="space-y-1.5">
                          <Label className="text-xs">商品标题</Label>
                          <Input
                            placeholder="可选"
                            value={productTitle}
                            onChange={(e) => setProductTitle(e.target.value)}
                            className="h-8 text-xs"
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* ── 平台特定字段: Bilibili ── */}
                  {hasBilibili && (
                    <div className="mt-4 pt-4 border-t border-border/30">
                      <div className="flex items-center gap-1.5 mb-2">
                        <PlatformIcon platform="bilibili" className="h-3 w-3" />
                        <span className="text-[11px] font-semibold text-muted-foreground">
                          Bilibili 专属
                        </span>
                      </div>
                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                        <div className="space-y-1.5">
                          <Label className="text-xs">分区分类</Label>
                          <Select
                            value={String(tid || '')}
                            onValueChange={(v) => setTid(v ? Number(v) : undefined)}
                          >
                            <SelectTrigger className="h-8 text-xs">
                              <SelectValue placeholder="选择分区" />
                            </SelectTrigger>
                            <SelectContent>
                              {BILIBILI_TIDS.map((t) => (
                                <SelectItem key={t.id} value={String(t.id)}>
                                  {t.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* ── 平台特定字段: 视频号 ── */}
                  {hasTencent && (
                    <div className="mt-4 pt-4 border-t border-border/30">
                      <div className="flex items-center gap-1.5 mb-2">
                        <PlatformIcon platform="tencent" className="h-3 w-3" />
                        <span className="text-[11px] font-semibold text-muted-foreground">
                          视频号专属
                        </span>
                      </div>
                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                        <div className="space-y-1.5">
                          <Label className="text-xs">短标题</Label>
                          <Input
                            placeholder="可选"
                            value={shortTitle}
                            onChange={(e) => setShortTitle(e.target.value)}
                            className="h-8 text-xs"
                          />
                        </div>
                        <div className="space-y-1.5">
                          <Label className="text-xs">原创分类</Label>
                          <Input
                            placeholder="可选"
                            value={category}
                            onChange={(e) => setCategory(e.target.value)}
                            className="h-8 text-xs"
                          />
                        </div>
                      </div>
                      <div className="mt-2 flex items-center gap-2">
                        <Checkbox
                          id="video-draft"
                          checked={isDraft}
                          onCheckedChange={(checked) => setIsDraft(checked === true)}
                        />
                        <Label htmlFor="video-draft" className="text-xs">
                          保存为草稿
                        </Label>
                      </div>
                    </div>
                  )}

                  {!hasAnyPlatformSpecific && (
                    <p className="mt-4 text-[11px] text-muted-foreground/50">
                      选择抖音、Bilibili 或视频号后显示专属选项
                    </p>
                  )}
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </Card>
        </motion.div>

        {/* ── 提交按钮 ─────────────────────────────────────────── */}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" onClick={clearAll}>
            清空
          </Button>
          <Button
            onClick={submit}
            disabled={submitting}
            className="btn-elegant"
          >
            {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            提交视频
          </Button>
        </div>
      </>
    )
  }),
)
