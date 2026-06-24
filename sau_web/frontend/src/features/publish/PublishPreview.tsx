import { memo } from 'react'
import { motion } from 'motion/react'
import { Card, CardContent, CardHeader, CardTitle, Badge } from '@/components/ui/index'
import { Eye, FileText, Image, Video } from 'lucide-react'

export type FormPreviewData = {
  title: string
  desc: string
  tags: string
  fileUrls: string[]
  fileType: 'video' | 'image' | null
}

type PublishPreviewProps = {
  mode: 'video' | 'note'
  data: FormPreviewData
}

const hasContent = (d: FormPreviewData) =>
  d.title || d.desc || d.tags || d.fileUrls.length > 0

const tagList = (tags: string) =>
  tags
    .split(/[,，]/)
    .map((t) => t.trim().replace(/^#/, ''))
    .filter(Boolean)

/**
 * Live preview of the publish form content. Reads only from props — no
 * store access, no side effects. The parent (PublishPage) feeds it via
 * `onFormChange` callbacks from VideoForm / NoteForm.
 */
export const PublishPreview = memo(function PublishPreview({
  mode,
  data,
}: PublishPreviewProps) {
  if (!hasContent(data)) {
    return (
      <Card className="h-fit border-border/60 shadow-sm opacity-60">
        <CardHeader className="pb-2 pt-4">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold tracking-tight text-muted-foreground">
            <Eye className="h-4 w-4" />
            内容预览
          </CardTitle>
        </CardHeader>
        <CardContent className="px-3.5 pb-4">
          <p className="text-xs text-muted-foreground leading-relaxed">
            填写表单后，这里会实时展示发布内容的预览效果
          </p>
        </CardContent>
      </Card>
    )
  }

  const tags = tagList(data.tags)
  const label = mode === 'video' ? '描述' : '内容'

  return (
    <Card className="h-fit border-border/60 shadow-sm">
      <CardHeader className="pb-2 pt-4">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold tracking-tight">
          <Eye className="h-4 w-4 text-primary" />
          内容预览
          <Badge variant="secondary" className="ml-auto text-[10px] font-normal">
            {mode === 'video' ? '视频' : '图文'}
          </Badge>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-3 px-3.5 pb-4">
        {/* ── Thumbnail ──────────────────────────────────── */}
        {data.fileUrls.length > 0 && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ type: 'spring', stiffness: 400, damping: 25 }}
            className="relative rounded-lg overflow-hidden bg-muted"
          >
            {data.fileType === 'video' ? (
              <video
                src={data.fileUrls[0]}
                className="w-full max-h-[180px] object-contain"
                controls
                preload="metadata"
              />
            ) : (
              <div className="grid grid-cols-2 gap-0.5 max-h-[180px] overflow-hidden">
                {data.fileUrls.slice(0, 4).map((url, i) => (
                  <img
                    key={i}
                    src={url}
                    alt={`预览 ${i + 1}`}
                    className="w-full h-[88px] object-cover"
                  />
                ))}
                {data.fileUrls.length > 4 && (
                  <div className="flex items-center justify-center bg-muted-foreground/20 text-xs text-muted-foreground">
                    +{data.fileUrls.length - 4}
                  </div>
                )}
              </div>
            )}
            <div className="absolute bottom-1.5 left-1.5 flex items-center gap-1 rounded bg-black/50 px-1.5 py-0.5 text-[10px] text-white">
              {data.fileType === 'video' ? (
                <Video className="h-3 w-3" />
              ) : (
                <Image className="h-3 w-3" />
              )}
              <span>{data.fileType === 'video' ? '视频' : `${data.fileUrls.length} 张图片`}</span>
            </div>
          </motion.div>
        )}

        {/* ── Title ──────────────────────────────────────── */}
        {data.title && (
          <div className="space-y-1">
            <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              标题
            </span>
            <p className="text-sm font-semibold leading-snug">{data.title}</p>
          </div>
        )}

        {/* ── Desc ───────────────────────────────────────── */}
        {data.desc && (
          <div className="space-y-1">
            <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              {label}
            </span>
            <p className="text-xs text-muted-foreground leading-relaxed line-clamp-4">
              {data.desc}
            </p>
          </div>
        )}

        {/* ── Tags ───────────────────────────────────────── */}
        {tags.length > 0 && (
          <div className="space-y-1.5">
            <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              标签
            </span>
            <div className="flex flex-wrap gap-1">
              {tags.map((tag, i) => (
                <Badge key={i} variant="outline" className="h-5 px-1.5 text-[10px] font-normal">
                  {tag}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* ── Footer ─────────────────────────────────────── */}
        <div className="flex items-center gap-1.5 pt-1">
          <FileText className="h-3 w-3 text-muted-foreground/50" />
          <span className="text-[10px] text-muted-foreground/60">
            发布后效果参考
          </span>
        </div>
      </CardContent>
    </Card>
  )
})
