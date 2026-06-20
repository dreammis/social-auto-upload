import axios, { type AxiosInstance } from 'axios'
import {
  BookOutlined,
  CustomerServiceOutlined,
  NotificationOutlined,
  PlayCircleOutlined,
  ReadOutlined,
  ThunderboltOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons'

const baseURL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) || 'http://localhost:5409'

const request: AxiosInstance = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
})

type ApiResponse<T> = {
  success: boolean
  data: T
  message?: string
}

export type PlatformOption = {
  label: string
  value: string
  color?: string
  icon?: React.ReactNode
}

export const PLATFORMS: readonly PlatformOption[] = [
  { label: '抖音', value: 'douyin', color: 'magenta' },
  { label: '快手', value: 'kuaishou', color: 'orange' },
  { label: '小红书', value: 'xiaohongshu', color: 'red' },
  { label: '视频号', value: 'tencent', color: 'green' },
  { label: 'Bilibili', value: 'bilibili', color: 'blue' },
  { label: 'TikTok', value: 'tiktok', color: 'cyan' },
  { label: '百家号', value: 'baijiahao', color: 'gold' },
] as const

const PLATFORM_ICONS: Record<string, React.ReactNode> = {
  douyin: <CustomerServiceOutlined />,
  kuaishou: <ThunderboltOutlined />,
  xiaohongshu: <BookOutlined />,
  tencent: <NotificationOutlined />,
  bilibili: <PlayCircleOutlined />,
  tiktok: <VideoCameraOutlined />,
  baijiahao: <ReadOutlined />,
}

export const PLATFORMS_WITH_ICONS: readonly PlatformOption[] = PLATFORMS.map((p) => ({
  ...p,
  icon: PLATFORM_ICONS[p.value] ?? undefined,
})) as typeof PLATFORMS

export const LOGIN_PLATFORMS = PLATFORMS as readonly PlatformOption[]

/** Platforms that support note/image post uploads */
export const NOTE_PLATFORMS: readonly PlatformOption[] = [
  { label: '抖音', value: 'douyin', color: 'magenta' },
  { label: '快手', value: 'kuaishou', color: 'orange' },
  { label: '小红书', value: 'xiaohongshu', color: 'red' },
  { label: 'Bilibili', value: 'bilibili', color: 'blue' },
] as const


export type AccountItem = {
  platform: string
  account_name: string
  path: string
}

export type TaskItem = {
  task_id: string
  platform?: string
  action?: string
  account?: string
  status?: string
  created?: string
  code?: number | null
  error?: string | null
  argv?: string | null
  result?: string | null
  publish_detail?: string | null
}

export type LogEntry = {
  ts: string
  message: string
}

export const api = {
  getAccounts(platform?: string): Promise<ApiResponse<AccountItem[]>> {
    return request
      .get('/api/accounts', {
        params: platform ? { platform } : undefined,
      })
      .then((res) => res.data)
  },
  deleteAccount(platform: string, account: string): Promise<ApiResponse<null>> {
    return request.post('/api/accounts/delete', { platform, account }).then((res) => res.data)
  },
  checkAccount(platform: string, account: string, deep: boolean = false): Promise<{
    success: boolean
    data?: {
      quick: { valid: boolean; reason: string; age_hours: number | null; file_size: number | null }
      deep_check: string | null
      task_id: string | null
    }
    message?: string
  }> {
    return request.post('/api/accounts/check', { platform, account, deep }).then((res) => res.data)
  },
  checkAllAccounts(): Promise<{
    success: boolean
    data?: { platform: string; account: string; quick: { valid: boolean; reason: string; age_hours: number | null; file_size: number | null } }[]
  }> {
    return request.post('/api/accounts/check-all', {}).then((res) => res.data)
  },
  loginAccount(payload: { platform: string; account: string; headless?: boolean }): Promise<{ success: boolean; data?: { task_id: string }; message?: string }> {
    return request.post('/api/accounts/login', payload).then((res) => res.data)
  },
  uploadVideo(payload: {
    platform: string
    account: string
    title: string
    file: File
    desc?: string
    tags?: string
    schedule?: string
    headless?: string
    thumbnail?: string
    thumbnail_landscape?: string
    thumbnail_portrait?: string
    product_link?: string
    product_title?: string
    tid?: number
    short_title?: string
    category?: string
    is_draft?: string
  }): Promise<{ success: boolean; data?: { task_id: string }; message?: string }> {
    const formData = new FormData()
    formData.append('platform', payload.platform)
    formData.append('account', payload.account)
    formData.append('title', payload.title)
    formData.append('file', payload.file)
    if (payload.desc !== undefined) formData.append('desc', payload.desc)
    if (payload.tags !== undefined) formData.append('tags', payload.tags)
    if (payload.schedule) formData.append('schedule', payload.schedule)
    if (payload.thumbnail) formData.append('thumbnail', payload.thumbnail)
    if (payload.thumbnail_landscape) formData.append('thumbnail_landscape', payload.thumbnail_landscape)
    if (payload.thumbnail_portrait) formData.append('thumbnail_portrait', payload.thumbnail_portrait)
    if (payload.product_link) formData.append('product_link', payload.product_link)
    if (payload.product_title) formData.append('product_title', payload.product_title)
    if (payload.tid !== undefined) formData.append('tid', String(payload.tid))
    if (payload.headless !== undefined) formData.append('headless', payload.headless)
    if (payload.short_title) formData.append('short_title', payload.short_title)
    if (payload.category) formData.append('category', payload.category)
    if (payload.is_draft !== undefined) formData.append('is_draft', payload.is_draft)

    return request({
      method: 'post',
      url: '/api/upload/video',
      data: formData,
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((res) => res.data)
  },
  uploadNote(payload: {
    platform: string
    account: string
    images: string[]
    title: string
    note?: string
    tags?: string
    schedule?: string
    headless?: string
  }): Promise<{ success: boolean; data?: { task_id: string }; message?: string }> {
    return request.post('/api/upload/note', payload).then((res) => res.data)
  },
  /** Upload note with actual file objects via multipart FormData (images_0, images_1, …) */
  uploadNoteMultipart(payload: {
    platform: string
    account: string
    title: string
    images: File[]
    note?: string
    tags?: string
    schedule?: string
    headless?: string
  }): Promise<{ success: boolean; data?: { task_id: string }; message?: string }> {
    const formData = new FormData()
    formData.append('platform', payload.platform)
    formData.append('account', payload.account)
    formData.append('title', payload.title)
    if (payload.note) formData.append('note', payload.note)
    if (payload.tags) formData.append('tags', payload.tags)
    if (payload.schedule) formData.append('schedule', payload.schedule)
    if (payload.headless !== undefined) formData.append('headless', payload.headless)
    payload.images.forEach((file, idx) => {
      formData.append(`images_${idx}`, file)
    })
    return request({
      method: 'post',
      url: '/api/upload/note',
      data: formData,
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((res) => res.data)
  },
  getTasks(): Promise<ApiResponse<TaskItem[]>> {
    return request.get('/api/tasks').then((res) => res.data)
  },
  retryTask(taskId: string): Promise<{ success: boolean; data?: { task_id: string }; message?: string }> {
    return request.post('/api/tasks/retry', { task_id: taskId }).then((res) => res.data)
  },
  deleteTask(taskId: string): Promise<{ success: boolean; message?: string }> {
    return request.post('/api/tasks/delete', { task_id: taskId }).then((res) => res.data)
  },
  clearTasks(status?: string[]): Promise<{ success: boolean; data?: { deleted: number } }> {
    return request.post('/api/tasks/clear', { status }).then((res) => res.data)
  },
  addTask(payload: {
    platform: string
    action: string
    account: string
    title?: string
    file?: string
    images?: string[]
    argv?: string[]
  }): Promise<{ success: boolean; data?: { task_id: string }; message?: string }> {
    return request.post('/api/tasks/add', payload).then((res) => res.data)
  },
  getLogs(after?: string, taskId?: string): Promise<ApiResponse<LogEntry[]>> {
    const params: Record<string, string> = {}
    if (after) params.after = after
    if (taskId) params.task_id = taskId
    return request
      .get('/api/logs', {
        params: Object.keys(params).length ? params : undefined,
      })
      .then((res) => res.data)
  },
}
