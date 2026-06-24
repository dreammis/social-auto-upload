import {
  Activity,
  AlertOctagon,
  BarChart3,
  CheckCircle2,
  Clock,
  FlaskConical,
} from 'lucide-react'
import type { ReactNode } from 'react'
import type { ChipBarVariant } from '@/components/ui/chip-bar'

/**
 * Task-domain types, status meta, and the chip definitions for the status
 * bar.
 *
 * Cross-page helpers (formatDateTime, shortenId, runWithConcurrency,
 * BATCH_CONCURRENCY) have moved to `@/lib/features` so non-task pages can
 * reuse them.
 */

export type StatusType =
  | 'all'
  | 'pending'
  | 'running'
  | 'scheduled'
  | 'success'
  | 'failed'
  | 'error'

export type TaskStatusVariant =
  | 'secondary'
  | 'info'
  | 'warning'
  | 'success'
  | 'error'

/** Maps task.status code → friendly label + chip-bar/badge palette variant. */
export const STATUS_META: Record<string, { variant: TaskStatusVariant; label: string }> = {
  pending: { variant: 'secondary', label: '等待中' },
  running: { variant: 'info', label: '执行中' },
  scheduled: { variant: 'warning', label: '定时中' },
  success: { variant: 'success', label: '成功' },
  failed: { variant: 'error', label: '失败' },
  error: { variant: 'error', label: '异常' },
}

/** Status chip definitions shown above the table. */
export const STATUS_CHIPS: ReadonlyArray<{
  value: StatusType
  label: string
  icon: ReactNode
  variant: ChipBarVariant
}> = [
  { value: 'all', label: '全部', icon: <BarChart3 className="h-3.5 w-3.5" />, variant: 'neutral' },
  { value: 'pending', label: '等待中', icon: <Clock className="h-3.5 w-3.5" />, variant: 'neutral' },
  { value: 'running', label: '执行中', icon: <Activity className="h-3.5 w-3.5" />, variant: 'info' },
  { value: 'scheduled', label: '定时中', icon: <FlaskConical className="h-3.5 w-3.5" />, variant: 'warning' },
  { value: 'success', label: '成功', icon: <CheckCircle2 className="h-3.5 w-3.5" />, variant: 'success' },
  { value: 'failed', label: '失败', icon: <AlertOctagon className="h-3.5 w-3.5" />, variant: 'error' },
  { value: 'error', label: '异常', icon: <AlertOctagon className="h-3.5 w-3.5" />, variant: 'error' },
]

export type BatchResultItem = {
  taskId: string
  success: boolean
  message?: string
  status?: string
}

export type BatchProgress = {
  type: 'retry' | 'delete'
  total: number
  current: number
  results: BatchResultItem[]
} | null

