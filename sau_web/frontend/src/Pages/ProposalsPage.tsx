import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { ScrollArea } from '@/components/ui/scroll-area'
import { PageHeader } from '@/components/ui/page-header'
import { cn } from '@/lib/utils'
import {
  GitBranch,
  CheckCircle,
  Clock,
  FlaskConical,
  FileText,
  FolderKanban,
} from 'lucide-react'
import request from 'axios'
import { useMemo } from 'react'

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) || 'http://localhost:5409'

type ProposalArtifactTasks = {
  total: number
  completed: number
}

type ProposalArtifacts = {
  proposal?: string
  design?: string
  tasks?: ProposalArtifactTasks
}

type Proposal = {
  dir: string
  name: string
  created: string
  status: string
  artifacts?: ProposalArtifacts
  layers?: string[]
  platforms?: string[]
  applyReady?: boolean
}

const LAYER_COLORS: Record<string, string> = {
  cli: 'bg-blue-500/15 text-blue-700 dark:text-blue-400',
  api: 'bg-indigo-500/15 text-indigo-700 dark:text-indigo-400',
  frontend: 'bg-purple-500/15 text-purple-700 dark:text-purple-400',
}

const STATUS_META: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  proposed: { color: 'bg-muted text-muted-foreground', icon: <Clock className="h-4 w-4" />, label: '已提案' },
  'in-progress': { color: 'bg-blue-500/15 text-blue-700 dark:text-blue-400', icon: <FlaskConical className="h-4 w-4" />, label: '进行中' },
  completed: { color: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400', icon: <CheckCircle className="h-4 w-4" />, label: '已完成' },
  archived: { color: 'bg-muted text-muted-foreground', icon: <GitBranch className="h-4 w-4" />, label: '已归档' },
}

function ProposalsPage() {
  const { data: proposals = [], isLoading } = useQuery<Proposal[]>({
    queryKey: ['proposals'],
    queryFn: async () => {
      const res = await request.get(`${API_BASE}/api/proposals`)
      return res.data.data ?? []
    },
    refetchInterval: 30_000,
  })

  const sorted = useMemo(
    () => [...proposals].sort((a, b) => b.created.localeCompare(a.created)),
    [proposals],
  )

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="变更提案"
        description="查看项目变更提案和进度"
        icon={<FolderKanban className="h-5 w-5 text-muted-foreground" />}
      />

      <Card className="card-refined">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <CardTitle className="flex items-center gap-2 text-lg">
            <span>提案列表</span>
            <Badge variant="secondary">{proposals.length}</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="space-y-2">
                  <Skeleton className="h-5 w-[200px]" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-[150px]" />
                </div>
              ))}
            </div>
          ) : sorted.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              暂无提案。在终端运行 <code className="rounded bg-muted px-1.5 py-0.5 text-xs">/opsx-propose "你的想法"</code> 来创建第一个提案。
            </p>
          ) : (
            <ScrollArea className="h-[600px]">
              <div className="space-y-4">
                {sorted.map((p) => {
                  const meta = STATUS_META[p.status] ?? STATUS_META.proposed
                  return (
                    <div key={p.dir} className="relative pl-6 pb-4 border-l-2 border-border last:border-0">
                      <div className={cn("absolute left-[-9px] top-0 h-4 w-4 rounded-full border-2 border-background", meta.color)}>
                        {meta.icon}
                      </div>
                      <Card className="ml-4">
                        <CardHeader className="pb-2">
                          <CardTitle className="flex items-center gap-2 text-base">
                            {meta.icon}
                            <span>{p.name}</span>
                            <Badge className={meta.color}>{meta.label}</Badge>
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3">
                          {p.artifacts?.proposal && (
                            <p className="text-sm text-muted-foreground line-clamp-2">
                              {p.artifacts.proposal}
                            </p>
                          )}

                          {p.layers && p.layers.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {p.layers.map((layer) => (
                                <Badge key={layer} className={cn("text-xs", LAYER_COLORS[layer] ?? 'bg-muted text-muted-foreground')}>
                                  {layer}
                                </Badge>
                              ))}
                            </div>
                          )}

                          {p.artifacts?.tasks && (
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                              <FileText className="h-4 w-4" />
                              <span>任务进度：{p.artifacts.tasks.completed}/{p.artifacts.tasks.total}</span>
                            </div>
                          )}

                          <p className="text-xs text-muted-foreground">
                            创建时间：{new Date(p.created).toLocaleString('zh-CN', { hour12: false })}
                          </p>
                        </CardContent>
                      </Card>
                    </div>
                  )
                })}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default ProposalsPage
