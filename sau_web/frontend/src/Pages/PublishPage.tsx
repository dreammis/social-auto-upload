import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'
import { PageHeader } from '@/components/ui/page-header'
import { cn } from '@/lib/utils'
import { NOTE_PLATFORMS, PLATFORMS, PLATFORMS_WITH_ICONS, api } from '../api/client'
import { useAccounts } from '../hooks/useTasks'
import { usePublishStore } from '../stores/publishStore'
import { useToast } from '@/components/ui/toast'
import {
  Send,
  FilePlus,
  Settings,
  Flag,
  X,
  Inbox,
  Image,
  Video,
  CheckCircle,
  Info,
  Loader2,
} from 'lucide-react'

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
]

function parseAccountKey(key: string) {
  const parts = key.split('::')
  return parts[1] ?? key
}

function formatTaskId(value?: string) {
  if (!value) return '-'
  return value.length > 14 ? `...${value.slice(-10)}` : value
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function SectionHeader({ icon, title, color }: { icon: React.ReactNode; title: string; color?: string }) {
  return (
    <div className="flex items-center gap-2 mb-4 pb-2 border-b">
      <div
        className="flex h-7 w-7 items-center justify-center rounded-lg"
        style={{ background: color ? `${color}15` : 'rgba(22,119,255,0.08)', color: color ?? '#1677ff' }}
      >
        {icon}
      </div>
      <span className="text-sm font-semibold">{title}</span>
    </div>
  )
}

function PublishPage() {
  const navigate = useNavigate()
  const { addToast } = useToast()
  const [submitting, setSubmitting] = useState(false)

  const [videoPlatforms, setVideoPlatforms] = useState<string[]>([])
  const [videoAccounts, setVideoAccounts] = useState<string[]>([])
  const [videoTitle, setVideoTitle] = useState('')
  const [videoDesc, setVideoDesc] = useState('')
  const [videoTags, setVideoTags] = useState('')
  const [videoSchedule, setVideoSchedule] = useState('')
  const [videoHeadless, setVideoHeadless] = useState(true)
  const [videoThumbnail, setVideoThumbnail] = useState('')
  const [videoThumbnailLandscape, setVideoThumbnailLandscape] = useState('')
  const [videoThumbnailPortrait, setVideoThumbnailPortrait] = useState('')
  const [videoProductLink, setVideoProductLink] = useState('')
  const [videoProductTitle, setVideoProductTitle] = useState('')
  const [videoTid, setVideoTid] = useState<number | undefined>()
  const [videoShortTitle, setVideoShortTitle] = useState('')
  const [videoCategory, setVideoCategory] = useState('')
  const [videoIsDraft, setVideoIsDraft] = useState(false)

  const [notePlatforms, setNotePlatforms] = useState<string[]>([])
  const [noteAccounts, setNoteAccounts] = useState<string[]>([])
  const [noteTitle, setNoteTitle] = useState('')
  const [noteContent, setNoteContent] = useState('')
  const [noteTags, setNoteTags] = useState('')
  const [noteSchedule, setNoteSchedule] = useState('')
  const [noteHeadless, setNoteHeadless] = useState(true)

  const videoFileRef = useRef<File | null>(null)
  const [videoFileInfo, setVideoFileInfo] = useState<{ name: string; size: number } | null>(null)
  const [noteImageFiles, setNoteImageFiles] = useState<File[]>([])
  const navigateTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const { data: accountOptions = [], refetch: refetchAccounts } = useAccounts()
  const lastTaskIds = usePublishStore((s) => s.lastTaskIds)
  const submitSuccess = usePublishStore((s) => s.submitSuccess)
  const setLastTaskIds = usePublishStore((s) => s.setLastTaskIds)
  const setSubmitSuccess = usePublishStore((s) => s.setSubmitSuccess)

  const submitVideoForm = async () => {
    if (!videoPlatforms.length || !videoAccounts.length) {
      addToast('请选择平台和账号', 'warning')
      return
    }
    if (!videoFileRef.current) {
      addToast('请选择视频文件', 'warning')
      return
    }
    if (!videoTitle.trim()) {
      addToast('请输入标题', 'warning')
      return
    }

    setSubmitting(true)
    try {
      const tasks = videoPlatforms.flatMap((platform) =>
        videoAccounts.map((accountKey) =>
          api
            .uploadVideo({
              platform,
              account: parseAccountKey(accountKey),
              title: videoTitle,
              file: videoFileRef.current!,
              desc: videoDesc || undefined,
              tags: videoTags || undefined,
              schedule: videoSchedule || undefined,
              headless: String(videoHeadless),
              thumbnail: videoThumbnail || undefined,
              thumbnail_landscape: videoThumbnailLandscape || undefined,
              thumbnail_portrait: videoThumbnailPortrait || undefined,
              product_link: videoProductLink || undefined,
              product_title: videoProductTitle || undefined,
              tid: videoTid,
              short_title: videoShortTitle || undefined,
              category: videoCategory || undefined,
              is_draft: videoIsDraft ? 'true' : undefined,
            })
            .then((res) => ({ platform, accountKey, success: res.success, taskId: res.data?.task_id })),
        ),
      )

      const results = await Promise.all(tasks)
      const ids: string[] = []
      results.forEach((item) => {
        if (item.success && item.taskId) ids.push(item.taskId)
      })
      setLastTaskIds(ids)

      const failed = results.filter((item) => !item.success)
      if (failed.length) {
        addToast(`有 ${failed.length} 个任务提交失败`, 'error')
      } else {
        addToast(`已提交 ${results.length} 个视频上传任务`, 'success')
      }
      setVideoTitle('')
      setVideoDesc('')
      setVideoTags('')
      setVideoSchedule('')
      setVideoThumbnail('')
      setVideoThumbnailLandscape('')
      setVideoThumbnailPortrait('')
      setVideoProductLink('')
      setVideoProductTitle('')
      setVideoTid(undefined)
      setVideoShortTitle('')
      setVideoCategory('')
      setVideoIsDraft(false)
      setVideoFileInfo(null)
      videoFileRef.current = null
      setSubmitSuccess({ count: results.length, mode: '视频', taskIds: ids })
      if (navigateTimerRef.current) clearTimeout(navigateTimerRef.current)
      navigateTimerRef.current = setTimeout(() => navigate('/tasks'), 1500)
    } catch {
      addToast('视频请求失败，请检查后端连接', 'error')
    } finally {
      setSubmitting(false)
    }
  }

  useEffect(() => {
    return () => {
      if (navigateTimerRef.current) clearTimeout(navigateTimerRef.current)
    }
  }, [])

  const submitNoteForm = async () => {
    if (!notePlatforms.length || !noteAccounts.length) {
      addToast('请选择平台和账号', 'warning')
      return
    }
    if (noteImageFiles.length === 0) {
      addToast('请至少添加一张图片', 'warning')
      return
    }
    if (!noteTitle.trim()) {
      addToast('请输入标题', 'warning')
      return
    }

    setSubmitting(true)
    try {
      const tasks = notePlatforms.flatMap((platform) =>
        noteAccounts.map((accountKey) =>
          api
            .uploadNoteMultipart({
              platform,
              account: parseAccountKey(accountKey),
              title: noteTitle,
              note: noteContent || undefined,
              tags: noteTags || undefined,
              schedule: noteSchedule || undefined,
              headless: String(noteHeadless),
              images: noteImageFiles,
            })
            .then((res) => ({ platform, accountKey, success: res.success, taskId: res.data?.task_id })),
        ),
      )

      const results = await Promise.all(tasks)
      const ids: string[] = []
      results.forEach((item) => {
        if (item.success && item.taskId) ids.push(item.taskId)
      })
      setLastTaskIds(ids)

      const failed = results.filter((item) => !item.success)
      if (failed.length) {
        addToast(`有 ${failed.length} 个任务提交失败`, 'error')
      } else {
        addToast(`已提交 ${results.length} 个图文上传任务`, 'success')
      }
      setNoteTitle('')
      setNoteContent('')
      setNoteTags('')
      setNoteSchedule('')
      setNoteImageFiles([])
      setSubmitSuccess({ count: results.length, mode: '图文', taskIds: ids })
      if (navigateTimerRef.current) clearTimeout(navigateTimerRef.current)
      navigateTimerRef.current = setTimeout(() => navigate('/tasks'), 1500)
    } catch {
      addToast('图文请求失败，请检查后端连接', 'error')
    } finally {
      setSubmitting(false)
    }
  }

  const handleGoToTasks = () => {
    if (navigateTimerRef.current) clearTimeout(navigateTimerRef.current)
    navigate('/tasks')
  }

  const accountCount = accountOptions.length
  const platformCount = PLATFORMS.length

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="发布中心"
        description="发布视频或图文到多个平台"
        icon={<Send className="h-5 w-5 text-muted-foreground" />}
      />

      {submitSuccess && (
        <Alert className="border-emerald-200 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950">
          <CheckCircle className="h-4 w-4 text-emerald-600" />
          <AlertTitle className="text-emerald-800 dark:text-emerald-200">提交成功</AlertTitle>
          <AlertDescription className="flex items-center justify-between">
            <span>
              <strong>{submitSuccess.count}</strong> 个{submitSuccess.mode}上传任务已提交！
            </span>
            <Button size="sm" onClick={handleGoToTasks}>查看任务状态 →</Button>
          </AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Video className="h-5 w-5 text-primary" />
                <span>发布视频</span>
                <Badge className="bg-pink-500/15 text-pink-700 dark:text-pink-400">Video</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <SectionHeader icon={<Send className="h-4 w-4" />} title="发布目标" color="#1677ff" />
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>发布平台</Label>
                    <Select value={videoPlatforms[0] || ''} onValueChange={(v) => setVideoPlatforms(v ? [v] : [])}>
                      <SelectTrigger>
                        <SelectValue placeholder="选择发布平台" />
                      </SelectTrigger>
                      <SelectContent>
                        {PLATFORMS_WITH_ICONS.map((p) => (
                          <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>发布账号</Label>
                    <Select value={videoAccounts[0] || ''} onValueChange={(v) => setVideoAccounts(v ? [v] : [])}>
                      <SelectTrigger>
                        <SelectValue placeholder="选择发布账号" />
                      </SelectTrigger>
                      <SelectContent>
                        {accountOptions.map((item) => (
                          <SelectItem key={`${item.platform}_${item.account_name}`} value={`${item.platform}::${item.account_name}`}>
                            {item.platform} / {item.account_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              <div>
                <SectionHeader icon={<FilePlus className="h-4 w-4" />} title="内容素材" color="#7c3aed" />
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label>视频文件</Label>
                    <div
                      className={cn(
                        "flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition-colors cursor-pointer",
                        videoFileInfo
                          ? "border-primary/50 bg-primary/5"
                          : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/50"
                      )}
                      onClick={() => document.getElementById('video-file-input')?.click()}
                    >
                      {videoFileInfo ? (
                        <div className="flex items-center gap-3">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                            <Video className="h-5 w-5" />
                          </div>
                          <div>
                            <p className="font-medium">{videoFileInfo.name}</p>
                            <p className="text-sm text-muted-foreground">{formatFileSize(videoFileInfo.size)}</p>
                          </div>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={(e) => {
                              e.stopPropagation()
                              setVideoFileInfo(null)
                              videoFileRef.current = null
                            }}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                      ) : (
                        <>
                          <Inbox className="h-10 w-10 text-primary mb-2" />
                          <p className="text-sm text-muted-foreground">点击此区域或拖拽视频文件到此处上传</p>
                          <p className="text-xs text-muted-foreground/60 mt-1">支持 MP4 / MOV / AVI 等常见格式</p>
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
                          videoFileRef.current = file
                          setVideoFileInfo({ name: file.name, size: file.size })
                        }
                      }}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>标题</Label>
                    <Input
                      placeholder="请输入视频标题（建议 6-20 字）"
                      value={videoTitle}
                      onChange={(e) => setVideoTitle(e.target.value)}
                      maxLength={100}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>视频简介</Label>
                    <textarea
                      className="flex min-h-[100px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                      placeholder="补充视频简介、背景说明或发布备注"
                      value={videoDesc}
                      onChange={(e) => setVideoDesc(e.target.value)}
                      maxLength={1000}
                    />
                  </div>
                </div>
              </div>

              <div>
                <SectionHeader icon={<Settings className="h-4 w-4" />} title="发布设置" color="#059669" />
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>标签</Label>
                    <Input
                      placeholder="输入标签后按 Enter"
                      value={videoTags}
                      onChange={(e) => setVideoTags(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>定时发布</Label>
                    <Input
                      type="datetime-local"
                      value={videoSchedule}
                      onChange={(e) => setVideoSchedule(e.target.value)}
                    />
                  </div>
                </div>
                <div className="mt-4">
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="video-headless"
                      checked={videoHeadless}
                      onCheckedChange={(checked) => setVideoHeadless(checked === true)}
                    />
                    <Label htmlFor="video-headless" className="text-sm">无头模式（不显示浏览器窗口）</Label>
                  </div>
                </div>
              </div>

              <div>
                <SectionHeader icon={<Settings className="h-4 w-4" />} title="高级选项" color="#d97706" />
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>封面地址（可选）</Label>
                    <Input
                      placeholder="封面图片 URL 或 Data URI"
                      value={videoThumbnail}
                      onChange={(e) => setVideoThumbnail(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>横版封面（可选，4:3）</Label>
                    <Input
                      placeholder="封面图片 URL 或 Data URI"
                      value={videoThumbnailLandscape}
                      onChange={(e) => setVideoThumbnailLandscape(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>竖版封面（可选，3:4）</Label>
                    <Input
                      placeholder="封面图片 URL 或 Data URI"
                      value={videoThumbnailPortrait}
                      onChange={(e) => setVideoThumbnailPortrait(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>商品链接（抖音）</Label>
                    <Input
                      placeholder="https://"
                      value={videoProductLink}
                      onChange={(e) => setVideoProductLink(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>商品标题（抖音）</Label>
                    <Input
                      placeholder="可选商品标题"
                      value={videoProductTitle}
                      onChange={(e) => setVideoProductTitle(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Bilibili 分类</Label>
                    <Select value={String(videoTid || '')} onValueChange={(v) => setVideoTid(v ? Number(v) : undefined)}>
                      <SelectTrigger>
                        <SelectValue placeholder="选择 Bilibili 分区" />
                      </SelectTrigger>
                      <SelectContent>
                        {BILIBILI_TIDS.map((t) => (
                          <SelectItem key={t.id} value={String(t.id)}>{t.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>短标题（视频号）</Label>
                    <Input
                      placeholder="可选视频号短标题"
                      value={videoShortTitle}
                      onChange={(e) => setVideoShortTitle(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>原创分类（视频号）</Label>
                    <Input
                      placeholder="可选原创内容分类"
                      value={videoCategory}
                      onChange={(e) => setVideoCategory(e.target.value)}
                    />
                  </div>
                </div>
                <div className="mt-4">
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="video-draft"
                      checked={videoIsDraft}
                      onCheckedChange={(checked) => setVideoIsDraft(checked === true)}
                    />
                    <Label htmlFor="video-draft" className="text-sm">保存为草稿不发布（视频号）</Label>
                  </div>
                </div>
              </div>

              <Separator />

              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>提交后即创建视频上传任务，可在「任务列表」追踪执行状态。</AlertDescription>
              </Alert>

              <div className="flex gap-2">
                <Button variant="outline" onClick={() => {
                  setVideoTitle('')
                  setVideoDesc('')
                  setVideoTags('')
                  setVideoSchedule('')
                  setVideoThumbnail('')
                  setVideoThumbnailLandscape('')
                  setVideoThumbnailPortrait('')
                  setVideoProductLink('')
                  setVideoProductTitle('')
                  setVideoTid(undefined)
                  setVideoShortTitle('')
                  setVideoCategory('')
                  setVideoIsDraft(false)
                  setVideoFileInfo(null)
                  videoFileRef.current = null
                }}>
                  清空
                </Button>
                <Button onClick={submitVideoForm} disabled={submitting}>
                  {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                  提交视频
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Image className="h-5 w-5 text-purple-600" />
                <span>发布图文</span>
                <Badge className="bg-purple-500/15 text-purple-700 dark:text-purple-400">Note</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <SectionHeader icon={<Send className="h-4 w-4" />} title="发布目标" color="#1677ff" />
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>发布平台</Label>
                    <Select value={notePlatforms[0] || ''} onValueChange={(v) => setNotePlatforms(v ? [v] : [])}>
                      <SelectTrigger>
                        <SelectValue placeholder="选择发布平台" />
                      </SelectTrigger>
                      <SelectContent>
                        {NOTE_PLATFORMS.map((p) => (
                          <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>发布账号</Label>
                    <Select value={noteAccounts[0] || ''} onValueChange={(v) => setNoteAccounts(v ? [v] : [])}>
                      <SelectTrigger>
                        <SelectValue placeholder="选择发布账号" />
                      </SelectTrigger>
                      <SelectContent>
                        {accountOptions.map((item) => (
                          <SelectItem key={`${item.platform}_${item.account_name}`} value={`${item.platform}::${item.account_name}`}>
                            {item.platform} / {item.account_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              <div>
                <SectionHeader icon={<FilePlus className="h-4 w-4" />} title="内容素材" color="#7c3aed" />
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label>标题</Label>
                    <Input
                      placeholder="请输入图文标题"
                      value={noteTitle}
                      onChange={(e) => setNoteTitle(e.target.value)}
                      maxLength={100}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>图文正文</Label>
                    <textarea
                      className="flex min-h-[150px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                      placeholder="请输入图文正文，多行内容会自动换行显示"
                      value={noteContent}
                      onChange={(e) => setNoteContent(e.target.value)}
                      maxLength={3000}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>图片</Label>
                    <div
                      className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-muted-foreground/25 p-6 transition-colors cursor-pointer hover:border-primary/50 hover:bg-muted/50"
                      onClick={() => document.getElementById('note-image-input')?.click()}
                    >
                      <Image className="h-8 w-8 text-purple-600 mb-2" />
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
                          setNoteImageFiles((prev) => [...prev, ...Array.from(files)])
                        }
                      }}
                    />
                    {noteImageFiles.length > 0 && (
                      <div className="grid grid-cols-4 gap-2 mt-2">
                        {noteImageFiles.map((file, idx) => (
                          <div key={`${file.name}-${idx}`} className="relative aspect-square rounded-lg overflow-hidden border">
                            <img
                              src={URL.createObjectURL(file)}
                              alt={`图片 ${idx + 1}`}
                              className="h-full w-full object-cover"
                            />
                            <button
                              className="absolute top-1 right-1 h-5 w-5 rounded-full bg-black/50 text-white flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity"
                              onClick={() => setNoteImageFiles((prev) => prev.filter((_, i) => i !== idx))}
                            >
                              <X className="h-3 w-3" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                    <p className="text-xs text-muted-foreground">支持 JPG / PNG / GIF / WebP，可添加多张</p>
                  </div>
                </div>
              </div>

              <div>
                <SectionHeader icon={<Settings className="h-4 w-4" />} title="发布设置" color="#059669" />
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>标签</Label>
                    <Input
                      placeholder="输入标签后按 Enter"
                      value={noteTags}
                      onChange={(e) => setNoteTags(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>定时发布</Label>
                    <Input
                      type="datetime-local"
                      value={noteSchedule}
                      onChange={(e) => setNoteSchedule(e.target.value)}
                    />
                  </div>
                </div>
                <div className="mt-4">
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="note-headless"
                      checked={noteHeadless}
                      onCheckedChange={(checked) => setNoteHeadless(checked === true)}
                    />
                    <Label htmlFor="note-headless" className="text-sm">无头模式（不显示浏览器窗口）</Label>
                  </div>
                </div>
              </div>

              <Separator />

              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>支持拖拽上传多张图片，提交后即创建图文上传任务。</AlertDescription>
              </Alert>

              <div className="flex gap-2">
                <Button variant="outline" onClick={() => {
                  setNoteTitle('')
                  setNoteContent('')
                  setNoteTags('')
                  setNoteSchedule('')
                  setNoteImageFiles([])
                }}>
                  清空
                </Button>
                <Button onClick={submitNoteForm} disabled={submitting}>
                  {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                  提交图文
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="xl:col-span-1">
          <Card className="sticky top-6">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Flag className="h-5 w-5 text-amber-600" />
                <span>发布概览</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">可用账号</span>
                <span className="text-sm font-bold text-primary">{accountCount}</span>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">支持平台</span>
                <span className="text-sm font-bold">{platformCount}</span>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">最近提交</span>
                <span className="text-sm font-bold">
                  {lastTaskIds.length > 0 ? `${lastTaskIds.length} 个` : '暂无'}
                </span>
              </div>
              <Separator />
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">最新任务 ID</p>
                {lastTaskIds.length === 0 ? (
                  <p className="text-xs text-muted-foreground">暂无提交记录</p>
                ) : (
                  <div className="flex flex-wrap gap-1">
                    {lastTaskIds.map((id) => (
                      <Badge key={id} variant="secondary" className="text-xs">
                        {formatTaskId(id)}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
              <Separator />
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">
                  后端地址：<code className="bg-muted px-1 rounded">http://localhost:5409</code>
                </p>
                <p className="text-xs text-muted-foreground">
                  接口：<code className="bg-muted px-1 rounded">/api/upload/*</code>
                </p>
              </div>
              <Button variant="outline" size="sm" className="w-full" onClick={() => refetchAccounts()}>
                刷新
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default PublishPage
