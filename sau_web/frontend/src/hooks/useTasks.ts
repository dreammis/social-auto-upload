import { useQuery } from '@tanstack/react-query'
import { api, type LogEntry, type TaskItem } from '../api/client'

const TASKS_QUERY_KEY = ['tasks'] as const

/** Poll for all tasks every 3 s, but only when there are running tasks */
export function useTasks() {
  return useQuery<TaskItem[]>({
    queryKey: TASKS_QUERY_KEY,
    queryFn: async () => {
      const res = await api.getTasks()
      return res.data ?? []
    },
    refetchInterval: (query) => {
      // Stop polling if no data or no running tasks
      const tasks = query.state.data
      if (!tasks || tasks.length === 0) return false
      const hasRunningTasks = tasks.some(
        (task) => task.status === 'pending' || task.status === 'running'
      )
      return hasRunningTasks ? 3_000 : false
    },
  })
}

/**
 * Fetch accounts, optionally filtered by platform.
 */
export function useAccounts(platform?: string) {
  return useQuery({
    queryKey: ['accounts', platform ?? 'all'] as const,
    queryFn: async () => {
      const res = await api.getAccounts(platform)
      return res.data ?? []
    },
  })
}

/**
 * Fetch logs related to a specific task.
 *
 * Uses server-side filtering via the `task_id` query parameter.
 * Auto-polls every 2 s while the task is running, stops once terminal.
 */
export function useTaskLogs(taskId: string | null, taskStatus: string | undefined) {
  const isRunning = taskStatus === 'pending' || taskStatus === 'running'
  const enabled = !!taskId

  return useQuery<LogEntry[]>({
    queryKey: ['task-logs', taskId],
    queryFn: async () => {
      const res = await api.getLogs(undefined, taskId ?? undefined)
      return res.data ?? []
    },
    enabled,
    refetchInterval: enabled && isRunning ? 2_000 : false,
    staleTime: 1_000,
  })
}
