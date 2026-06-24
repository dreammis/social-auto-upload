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
import type { AiGenerationResult } from '@/components/AiSidebar/AiSidebar'
import type { FormPreviewData } from './PublishPreview'
import type { GroupSelection } from './GroupPublishSelector'
import {
  Button,
  Card,
  CardContent,
  Checkbox,
  Input,
  Label,
  MultiSelect,
  type MultiSelectOption,
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
  NOTE_PLATFORMS,
  PLATFORMS,
  getNoteImageLimit,
  type AccountItem,
} from '../../api/client'
import {
  FilePlus,
  Image as ImageIcon,
  Loader2,
  Maximize,
  Send,
  Users,
  X,
} from 'lucide-react'
import {
  effectiveMaxTags,
  platformTagLabel,
  SectionHeader,
} from './shared'
import { SchedulePicker } from './SchedulePicker'
import { parseAccountKey } from '@/lib/features'
import { ImageLightbox } from './ImageLightbox'

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

const thumbVariants = {
  hidden: { opacity: 0, scale: 0.5 },
  visible: (i: number) => ({
    opacity: 1,
    scale: 1,
    transition: { type: 'spring' as const, stiffness: 400, damping: 25, delay: i * 0.04 },
  }),
}

/** Imperative handle: parent (PublishPage) routes AI generations here. */
export type NoteFormHandle = {
  applyAiResult: (result: AiGenerationResult) => void
}

type NoteFormProps = {
  accountOptions: AccountItem[]
  /**
   * Pre-resolved group selection from GroupPublishSelector.
   * When provided, the form skips manual platform/account picking
   * and uses the group's cookie files directly for submission.
   */
  groupSelection?: GroupSelection | null
  onSuccess: (info: { count: number; taskIds: string[]; failedCount: number; mode: '图文' }) => void
  onError: (label: '图文') => void
  /** Called when the user selects a platform, so the parent can feed it to AiSidebar. */
  onPlatformChange?: (platform: string) => void
  /** Called on every form-change so the parent can render a live preview. */
  onFormChange?: (data: FormPreviewData) => void
}

/**
 * Note publishing form — three-card layout (目标 / 素材 / 设置) with a
 * thumbnail grid + memoized ImageLightbox. Localizes 6 form fields and the
 * image-files array so typing/scrolling never re-renders PublishPage.
 */
export const NoteForm = memo(
  forwardRef<NoteFormHandle, NoteFormProps>(function NoteForm(
    { accountOptions, groupSelection, onSuccess, onError, onPlatformChange, onFormChange },
    ref,
  ) {
    const { addToast } = useToast()

    const [platforms, setPlatforms] = useState<string[]>([])
    const [accounts, setAccounts] = useState<string[]>([])
    const [title, setTitle] = useState('')
    const [content, setContent] = useState('')
    const [tags, setTags] = useState('')
    const [schedule, setSchedule] = useState('')
    const [headless, setHeadless] = useState(true)

    const [imageFiles, setImageFiles] = useState<File[]>([])
    const [dragOver, setDragOver] = useState(false)
    const [dragIndex, setDragIndex] = useState<number | null>(null)
    const dragIdxRef = useRef<number | null>(null)
    const [dropTarget, setDropTarget] = useState<number | null>(null)
    const [lightboxIndex, setLightboxIndex] = useState<number | null>(null)
    const [submitting, setSubmitting] = useState(false)

    const isGroupMode = !!groupSelection
    const platformLabelMap = useMemo(
      () => Object.fromEntries(PLATFORMS.map((p) => [p.value, p.label])),
      [],
    )

    /** Only show platforms that have at least one authorized account. */
    const availablePlatforms = useMemo(
      () =>
        isGroupMode
          ? new Set(groupSelection!.mappings.map((m) => m.platform))
          : new Set(accountOptions.map((a) => a.platform)),
      [isGroupMode, groupSelection, accountOptions],
    )

    /** Multi-select options for the platform picker, filtered to authorized platforms. */
    const notePlatformOptions: MultiSelectOption[] = useMemo(
      () =>
        NOTE_PLATFORMS.filter((p) => availablePlatforms.has(p.value)).map((p) => ({
          label: p.label,
          value: p.value,
          icon: <PlatformIcon platform={p.value} className="h-4 w-4" />,
        })),
      [availablePlatforms],
    )

    /** Filter accounts to only show those matching the selected platforms. */
    const filteredAccounts = useMemo(
      () =>
        platforms.length === 0
          ? accountOptions
          : accountOptions.filter((a) => platforms.includes(a.platform)),
      [accountOptions, platforms],
    )

    /** When multiple platforms are selected, use the most restrictive image limit. */
    const imageLimit = Math.min(
      ...(platforms.length > 0 ? platforms.map((p) => getNoteImageLimit(p)) : [30]),
    )
    const imageFilesRef = useRef(imageFiles)
    imageFilesRef.current = imageFiles

    /** Enforce platform-specific image limit. Uses a ref to read current
     *  length so toast side-effects stay outside the setState updater. */
    const addImagesWithinLimit = (incoming: File[]) => {
      if (incoming.length === 0) return
      const remaining = imageLimit - imageFilesRef.current.length
      if (remaining <= 0) {
        addToast(`当前平台最多只能添加 ${imageLimit} 张图片`, 'warning')
        return
      }
      const toAdd = incoming.slice(0, remaining)
      if (toAdd.length < incoming.length) {
        addToast(`已截取前 ${toAdd.length} 张（当前平台限制 ${imageLimit} 张）`, 'warning')
      }
      setImageFiles((prev) => [...prev, ...toAdd])
    }

    useImperativeHandle(
      ref,
      () => ({
        applyAiResult(result) {
          if (result.title) setTitle(result.title)
          if (result.desc) setContent(result.desc)
        },
      }),
      [setTitle, setContent],
    )

    /**
     * Object URLs leak if we don't revoke them. Re-create the memo whenever
     * the file list changes and revoke all on unmount.
     */
    const imageUrls = useMemo(
      () => imageFiles.map((f) => URL.createObjectURL(f)),
      [imageFiles],
    )
    useEffect(() => {
      return () => {
        imageUrls.forEach((url) => URL.revokeObjectURL(url))
      }
    }, [imageUrls])

    /** Report form state upward for the live preview panel. */
    // Mirror the parent callback through a ref so this effect's dep array
    // stays focused on the form fields only. Prevents spurious re-fires if
    // a future refactor binds `onFormChange` to reactive state.
    const onFormChangeRef = useRef(onFormChange)
    useEffect(() => {
      onFormChangeRef.current = onFormChange
    }, [onFormChange])

    useEffect(() => {
      const handler = onFormChangeRef.current
      if (!handler) return
      handler({
        title,
        desc: content,
        tags,
        fileUrls: imageUrls,
        fileType: imageFiles.length > 0 ? 'image' : null,
      })
    }, [title, content, tags, imageUrls])

    const handleLightboxClose = useCallback(() => setLightboxIndex(null), [])
    const handleLightboxPrev = useCallback(
      () => setLightboxIndex((i) => (i !== null && i > 0 ? i - 1 : i)),
      [],
    )
    const handleLightboxNext = useCallback(
      () =>
        setLightboxIndex((i) =>
          i !== null && i < imageFiles.length - 1 ? i + 1 : i,
        ),
      [imageFiles.length],
    )

    const removeImage = useCallback((idx: number) => {
      setImageFiles((prev) => prev.filter((_, i) => i !== idx))
      // Clamp lightbox if it was pointing at or past the removed index.
      setLightboxIndex((prev) => {
        if (prev === null) return prev
        if (idx < prev) return prev - 1
        if (idx === prev) return prev < prev ? prev : null
        return prev
      })
    }, [])

    const moveImage = useCallback((fromIdx: number, toIdx: number) => {
      if (fromIdx === toIdx) return
      setImageFiles((prev) => {
        const next = [...prev]
        const [item] = next.splice(fromIdx, 1)
        next.splice(toIdx, 0, item)
        return next
      })
      // Adjust lightbox index
      setLightboxIndex((prev) => {
        if (prev === null) return prev
        if (prev === fromIdx) return toIdx
        if (fromIdx < prev && toIdx >= prev) return prev - 1
        if (fromIdx > prev && toIdx <= prev) return prev + 1
        return prev
      })
    }, [])

    const clearAll = useCallback(() => {
      setTitle('')
      setContent('')
      setTags('')
      setSchedule('')
      setImageFiles([])
    }, [])

    const submit = useCallback(async () => {
      if (isGroupMode) {
        if (!groupSelection!.platforms.length) {
          addToast('请至少选择一个发布平台', 'warning')
          return
        }
      } else {
        if (!platforms.length || !accounts.length) {
          addToast('请选择平台和账号', 'warning')
          return
        }
      }
      if (imageFiles.length === 0) {
        addToast('请至少添加一张图片', 'warning')
        return
      }
      if (!title.trim()) {
        addToast('请输入标题', 'warning')
        return
      }

      setSubmitting(true)
      try {
        let tasks: Promise<{
          platform: string
          accountKey: string
          success: boolean
          taskId: string | undefined
        }>[]

        if (isGroupMode) {
          tasks = groupSelection!.mappings
            .filter((m) => groupSelection!.platforms.includes(m.platform))
            .map((mapping) =>
              api
                .uploadNoteMultipart({
                  platform: mapping.platform,
                  account: mapping.cookieFile,
                  title,
                  note: content || undefined,
                  tags: tags || undefined,
                  schedule: schedule || undefined,
                  headless: String(headless),
                  images: imageFiles,
                })
                .then((res) => ({
                  platform: mapping.platform,
                  accountKey: `${mapping.platform}::${mapping.cookieFile}`,
                  success: res.success,
                  taskId: res.data?.task_id,
                })),
            )
        } else {
          tasks = accounts.map((accountKey) => {
            const accName = parseAccountKey(accountKey)
            const accPlatform = accountKey.split('::')[0]
            return api
              .uploadNoteMultipart({
                platform: accPlatform,
                account: accName,
                title,
                note: content || undefined,
                tags: tags || undefined,
                schedule: schedule || undefined,
                headless: String(headless),
                images: imageFiles,
              })
              .then((res) => ({
                platform: accPlatform,
                accountKey,
                success: res.success,
                taskId: res.data?.task_id,
              }))
          })
        }

        const results = await Promise.all(tasks)
        const ids: string[] = []
        results.forEach((item) => {
          if (item.success && item.taskId) ids.push(item.taskId)
        })

        const failed = results.filter((item) => !item.success)
        if (failed.length) {
          addToast(`有 ${failed.length} 个任务提交失败`, 'error')
        } else {
          addToast(`已提交 ${results.length} 个图文上传任务`, 'success')
        }
        clearAll()
        onSuccess({ count: results.length, taskIds: ids, failedCount: failed.length, mode: '图文' })
      } catch {
        addToast('图文请求失败，请检查后端连接', 'error')
        onError('图文')
      } finally {
        setSubmitting(false)
      }
    }, [isGroupMode, groupSelection, accounts, platforms, title, content, tags, schedule, headless, imageFiles, addToast, clearAll, onSuccess, onError])

    return (
      <>
        <Card>
          <CardContent className="space-y-4 pt-4">
            {/* 发布目标 */}
            <motion.div
              className="rounded-xl border border-border/30 bg-card/40 p-5"
              custom={0}
              variants={cardVariants}
              initial="hidden"
              animate="visible"
            >
              <SectionHeader icon={<Send className="h-4 w-4" />} title="发布目标" />
              {isGroupMode ? (
                <div className="flex items-center gap-3 rounded-lg bg-muted/40 border border-border/50 px-3 py-2.5">
                  <Users className="h-4 w-4 text-muted-foreground shrink-0" />
                  <div className="flex items-center gap-2 min-w-0 flex-1 flex-wrap">
                    <span className="text-sm font-medium">{groupSelection!.groupName}</span>
                    <span className="text-muted-foreground/40">·</span>
                    {groupSelection!.platforms.map((p) => (
                      <span
                        key={p}
                        className="inline-flex items-center gap-1 rounded bg-background border border-border/60 px-1.5 py-0.5 text-[11px] font-medium"
                      >
                        <PlatformIcon platform={p} className="h-3 w-3" />
                        {platformLabelMap[p] ?? p}
                      </span>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>发布平台</Label>
                    <MultiSelect
                      options={notePlatformOptions}
                      value={platforms}
                      onChange={(v) => {
                        setPlatforms(v)
                        onPlatformChange?.(v[0] || '')
                        // Clear accounts that no longer match the selected platforms
                        setAccounts((prev) =>
                          prev.filter((a) => v.includes(a.split('::')[0])),
                        )
                      }}
                      placeholder="选择发布平台（可多选）"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>发布账号</Label>
                    <Select value={accounts[0] || ''} onValueChange={(v) => setAccounts(v ? [v] : [])}>
                      <SelectTrigger>
                        <SelectValue placeholder="选择发布账号" />
                      </SelectTrigger>
                      <SelectContent>
                        {filteredAccounts.length === 0 ? (
                          <div className="px-2 py-4 text-sm text-muted-foreground text-center">
                            所选平台暂无可用账号
                          </div>
                        ) : (
                          filteredAccounts.map((item) => (
                            <SelectItem
                              key={`${item.platform}_${item.account_name}`}
                              value={`${item.platform}::${item.account_name}`}
                            >
                              <span className="flex items-center gap-2">
                                <PlatformIcon platform={item.platform} className="h-4 w-4" />
                                {item.platform} / {item.account_name}
                              </span>
                            </SelectItem>
                          ))
                        )}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              )}
            </motion.div>

            {/* 内容素材 */}
            <motion.div
              className="rounded-xl border border-border/30 bg-card/40 p-5"
              custom={1}
              variants={cardVariants}
              initial="hidden"
              animate="visible"
            >
              <SectionHeader
                icon={<FilePlus className="h-4 w-4" />}
                title="内容素材"
              />
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>图片</Label>
                  <div
                    className={cn(
                      'flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-6 transition-colors cursor-pointer',
                      dragOver
                        ? 'border-primary bg-primary/10'
                        : 'border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/50',
                    )}
                    onClick={() => document.getElementById('note-image-input')?.click()}
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
                      const files = e.dataTransfer.files
                      if (files) {
                        const newImages = Array.from(files).filter((f) =>
                          f.type.startsWith('image/'),
                        )
                        if (newImages.length > 0) {
                          addImagesWithinLimit(newImages)
                        }
                      }
                    }}
                  >
                    <ImageIcon className="h-8 w-8 text-purple-600 mb-2" />
                    <p className="text-sm text-muted-foreground">点击添加图片</p>
                  </div>
                  <input
                    id="note-image-input"
                    type="file"
                    accept="image/*"
                    multiple
                    className="hidden"
                    onChange={(e) => {
                      const files = e.target.files
                      if (files) {
                        addImagesWithinLimit(Array.from(files))
                      }
                    }}
                  />                      {imageFiles.length > 0 && (
                    <>
                      <div className="flex items-center justify-between">
                        <p className="text-[11px] text-muted-foreground">
                          {imageFiles.length}/{imageLimit} 张
                          {imageFiles.length > 1 && ' · 拖拽可调整顺序'}
                        </p>
                        {imageFiles.length >= imageLimit && (
                          <span className="text-[10px] text-amber-600 dark:text-amber-400 font-medium">
                            已达上限
                          </span>
                        )}
                      </div>
                      <div className="grid grid-cols-4 gap-2">
                      {imageFiles.map((file, idx) => (
                        <ThumbnailTile
                          key={`${file.name}-${file.size}-${file.lastModified}`}
                          url={imageUrls[idx]}
                          alt={`图片 ${idx + 1}`}
                          index={idx}
                          isDragging={dragIndex === idx}
                          isDropTarget={dropTarget === idx}
                          onOpen={() => setLightboxIndex(idx)}
                          onRemove={() => removeImage(idx)}
                          onDragStart={() => { dragIdxRef.current = idx; setDragIndex(idx) }}
                          onDragOver={() => setDropTarget(idx)}
                          onDrop={() => { moveImage(dragIdxRef.current!, idx); setDragIndex(null); setDropTarget(null) }}
                          onDragEnd={() => { setDragIndex(null); setDropTarget(null) }}
                          onDragLeave={() => setDropTarget((t) => (t === idx ? null : t))}
                        />
                      ))}
                      </div>
                    </>
                  )}
                  <p className="text-xs text-muted-foreground">
                    支持 JPG / PNG / GIF / WebP，可添加多张或拖拽到此区域
                  </p>
                </div>

                <div className="space-y-2">
                  <Label>标题</Label>
                  <Input
                    placeholder="请输入图文标题"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    maxLength={100}
                  />
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="note-content">图文正文</Label>
                    <Textarea
                      id="note-content"
                      className="min-h-[90px]"
                      placeholder="请输入图文正文，多行内容会自动换行显示"
                      value={content}
                      onChange={(e) => setContent(e.target.value)}
                      maxLength={3000}
                    />
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label>标签</Label>
                      <span className="text-[11px] text-muted-foreground">
                        {platformTagLabel(platforms)}
                      </span>
                    </div>
                    <TagInput
                      placeholder="按 Enter 添加标签（# 可省略）"
                      value={tags}
                      onChange={(val) => setTags(val)}
                      maxTags={effectiveMaxTags(platforms)}
                    />
                    <SchedulePicker
                      value={schedule}
                      onChange={setSchedule}
                    />
                    <div className="flex items-center gap-2 pt-1">
                      <Checkbox
                        id="note-headless"
                        checked={headless}
                        onCheckedChange={(checked) => setHeadless(checked === true)}
                      />
                      <Label htmlFor="note-headless" className="text-xs text-muted-foreground">
                        无头模式（不显示浏览器窗口）
                      </Label>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>



            <div className="flex gap-2 pt-2">
              <Button variant="outline" size="sm" onClick={clearAll}>
                清空
              </Button>
              <Button
                onClick={submit}
                disabled={submitting}
                className="bg-gradient-to-r from-purple-600 to-pink-500 hover:from-purple-600/90 hover:to-pink-500/90 text-primary-foreground shadow-md shadow-purple-500/20"
              >
                {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                提交图文
              </Button>
            </div>
          </CardContent>
        </Card>

        <ImageLightbox
          imageUrls={imageUrls}
          openIndex={lightboxIndex}
          onClose={handleLightboxClose}
          onPrev={handleLightboxPrev}
          onNext={handleLightboxNext}
        />
      </>
    )
  }),
)

/**
 * Single thumbnail rendered inside the image-grid. Memoized because the
 * grid renders N thumbnails per NoteForm and only one changes on hover/
 * remove — without memoization, removing index 3 re-renders all N tiles.
 *
 * Supports HTML5 drag-and-drop reordering: each tile is draggable, dropping
 * on another tile swaps their positions with visual feedback.
 */
const ThumbnailTile = memo(function ThumbnailTile({
  url,
  alt,
  index,
  isDragging,
  isDropTarget,
  onOpen,
  onRemove,
  onDragStart,
  onDragOver,
  onDrop,
  onDragEnd,
  onDragLeave,
}: {
  url: string
  alt: string
  index: number
  isDragging?: boolean
  isDropTarget?: boolean
  onOpen: () => void
  onRemove: () => void
  onDragStart?: () => void
  onDragOver?: () => void
  onDrop?: () => void
  onDragEnd?: () => void
  onDragLeave?: () => void
}) {
  return (
    <motion.div
      custom={index}
      variants={thumbVariants}
      initial="hidden"
      animate="visible"
      className={`relative aspect-square rounded-lg overflow-hidden border group/img cursor-pointer transition-all duration-150 ${
        isDragging ? 'opacity-30 scale-95' : ''
      } ${isDropTarget ? 'ring-2 ring-primary border-primary scale-105' : ''}`}
      onClick={onOpen}
      whileHover={{ scale: isDragging ? 0.95 : 1.02 }}
      transition={{ type: 'spring', stiffness: 500, damping: 30 }}
      draggable
      onDragStart={(e) => {
        e.stopPropagation()
        e.dataTransfer.effectAllowed = 'move'
        onDragStart?.()
      }}
      onDragOver={(e) => {
        e.preventDefault()
        e.stopPropagation()
        e.dataTransfer.dropEffect = 'move'
        onDragOver?.()
      }}
      onDrop={(e) => {
        e.preventDefault()
        e.stopPropagation()
        onDrop?.()
      }}
      onDragEnd={() => {
        onDragEnd?.()
      }}
      onDragLeave={() => {
        onDragLeave?.()
      }}
    >
      {/* Order number badge */}
      <span className="absolute top-1 left-1 z-10 flex h-4 w-4 items-center justify-center rounded-full bg-black/50 text-[9px] font-medium text-white opacity-0 group-hover/img:opacity-100 transition-opacity pointer-events-none">
        {index + 1}
      </span>
      <img
        src={url}
        alt={alt}
        className="h-full w-full object-cover transition-transform duration-300 group-hover/img:scale-105"
        draggable={false}
      />
      <div className="absolute inset-0 bg-black/0 group-hover/img:bg-black/20 transition-colors flex items-center justify-center">
        <Maximize className="h-4 w-4 text-white opacity-0 group-hover/img:opacity-100 transition-opacity" />
      </div>
      <button
        className="absolute top-1 right-1 h-5 w-5 rounded-full bg-black/50 text-white flex items-center justify-center opacity-0 group-hover/img:opacity-100 transition-opacity"
        onClick={(e) => {
          e.stopPropagation()
          onRemove()
        }}
        aria-label="删除图片"
      >
        <X className="h-3 w-3" />
      </button>
    </motion.div>
  )
})
