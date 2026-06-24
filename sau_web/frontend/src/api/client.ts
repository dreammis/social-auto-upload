import axios, { type AxiosInstance, type AxiosError } from 'axios'

const baseURL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  (import.meta.env.DEV ? '' : 'http://localhost:6001')

const request: AxiosInstance = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout
})

// Retry configuration
const MAX_RETRIES = 3
const RETRY_DELAY = 1000 // 1 second

// Helper function for exponential backoff delay
const getRetryDelay = (retryCount: number): number => {
  return Math.pow(2, retryCount) * RETRY_DELAY
}

// Request interceptor - could add auth tokens here in the future
request.interceptors.request.use(
  (config) => {
    // Add timestamp to prevent caching for GET requests
    if (config.method === 'get') {
      config.params = {
        ...config.params,
        _t: Date.now(),
      }
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor with retry logic
request.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config

    // If no config or already retried max times, reject
    if (!config || !config.headers) {
      return Promise.reject(error)
    }

    // Initialize retry count
    const retryCount = (config.headers['x-retry-count'] as number) || 0

    // Don't retry if we've exceeded max retries
    if (retryCount >= MAX_RETRIES) {
      return Promise.reject(error)
    }

    // Don't retry for certain error types
    if (
      error.code === 'ECONNABORTED' || // Timeout
      (error.response?.status && error.response.status >= 400 && error.response.status < 500) // Client errors
    ) {
      return Promise.reject(error)
    }

    // Only retry for network errors or server errors (5xx)
    if (
      !error.response || // Network error
      (error.response.status && error.response.status >= 500) // Server error
    ) {
      // Increment retry count
      config.headers['x-retry-count'] = retryCount + 1

      // Wait before retrying
      await new Promise((resolve) => setTimeout(resolve, getRetryDelay(retryCount)))

      // Retry the request
      return request(config)
    }

    return Promise.reject(error)
  }
)

type ApiResponse<T> = {
  success: boolean
  data: T
  message?: string
}

export type PlatformOption = {
  label: string
  value: string
  color?: string
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

export const PLATFORMS_WITH_ICONS = PLATFORMS

export const LOGIN_PLATFORMS = PLATFORMS as readonly PlatformOption[]

/** Platforms that support note/image post uploads */
export const NOTE_PLATFORMS: readonly PlatformOption[] = [
  { label: '抖音', value: 'douyin', color: 'magenta' },
  { label: '快手', value: 'kuaishou', color: 'orange' },
  { label: '小红书', value: 'xiaohongshu', color: 'red' },
  { label: 'Bilibili', value: 'bilibili', color: 'blue' },
  { label: '视频号', value: 'tencent', color: 'green' },
] as const

/** Platform-specific maximum image counts for note/image posts */
export const NOTE_PLATFORM_IMAGE_LIMITS: Record<string, number> = {
  xiaohongshu: 9,
  douyin: 30,
  kuaishou: 18,
  bilibili: 20,
  tencent: 9,
  baijiahao: 30,
}

/** Get the max image count for a given platform, or a generous default */
export function getNoteImageLimit(platform?: string): number {
  if (platform && platform in NOTE_PLATFORM_IMAGE_LIMITS) {
    return NOTE_PLATFORM_IMAGE_LIMITS[platform]
  }
  return 30
}

/** Platforms that support QR-code-based login via SSE */
export const QR_LOGIN_PLATFORMS: readonly string[] = [
  'douyin',
  'kuaishou',
  'xiaohongshu',
  'tencent',
  'bilibili',
  'tiktok',
  'baijiahao',
] as const


export type AccountItem = {
  platform: string
  account_name: string
  path: string
}

export type AccountGroup = {
  id: number
  name: string
  created: string
  authorizations: AccountAuthorization[]
}

export type AccountAuthorization = {
  id: number
  platform: string
  cookie_file: string
  valid: boolean
  reason?: string
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
  getBaseUrl() {
    return baseURL
  },

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

  // Account Groups API
  getAccountGroups(): Promise<ApiResponse<AccountGroup[]>> {
    return request.get('/api/account-groups').then((res) => res.data)
  },
  createAccountGroup(name: string): Promise<{ success: boolean; data?: { id: number; name: string }; message?: string }> {
    return request.post('/api/account-groups', { name }).then((res) => res.data)
  },
  deleteAccountGroup(groupId: number): Promise<{ success: boolean; message?: string }> {
    return request.delete(`/api/account-groups/${groupId}`).then((res) => res.data)
  },
  renameAccountGroup(groupId: number, name: string): Promise<{ success: boolean; data?: { id: number; name: string }; message?: string }> {
    return request.post(`/api/account-groups/${groupId}/rename`, { name }).then((res) => res.data)
  },
  authorizeAccountGroup(groupId: number, platform: string, headless?: boolean): Promise<{
    success: boolean
    data?: { task_id: string; group_name: string; platform: string; cookie_file: string }
    message?: string
  }> {
    return request.post(`/api/account-groups/${groupId}/authorize`, { platform, headless }).then((res) => res.data)
  },
  confirmAuthorizeAccountGroup(groupId: number, platform: string): Promise<{ success: boolean; message?: string }> {
    return request.post(`/api/account-groups/${groupId}/confirm-authorize`, { platform }).then((res) => res.data)
  },
  removeAuthorization(groupId: number, platform: string): Promise<{ success: boolean; message?: string }> {
    return request.delete(`/api/account-groups/${groupId}/authorize/${platform}`).then((res) => res.data)
  },
  reorderAccountGroups(groupIds: number[]): Promise<{ success: boolean; message?: string }> {
    return request.post('/api/account-groups/reorder', { group_ids: groupIds }).then((res) => res.data)
  },
  reorderAuthorizations(groupId: number, authIds: number[]): Promise<{ success: boolean; message?: string }> {
    return request.post(`/api/account-groups/${groupId}/reorder-authorizations`, { auth_ids: authIds }).then((res) => res.data)
  },

  // AI Content Generation API
  generateAiContent(payload: {
    prompt: string
    model?: string
    system_prompt?: string
    platform?: string
  }): Promise<{ success: boolean; data?: { content: string }; message?: string }> {
    return request.post('/api/ai/generate', payload).then((res) => res.data)
  },

  fetchAiModels(): Promise<{ success: boolean; data: { id: string; name: string }[]; source?: string }> {
    return request.get('/api/ai/models').then((res) => res.data)
  },

  getAiConfig(): Promise<{ success: boolean; data: { configured: boolean; key_count: number } }> {
    return request.get('/api/ai/config').then((res) => res.data)
  },

  listAiKeys(): Promise<{ success: boolean; data: { id: number; masked: string; created: string; rate_limited: boolean }[] }> {
    return request.get('/api/ai/keys').then((res) => res.data)
  },

  setAiConfig(apiKey: string): Promise<{ success: boolean; data?: { configured: boolean; key_masked: string; key_id: number }; message?: string }> {
    return request.post('/api/ai/config', { api_key: apiKey }).then((res) => res.data)
  },

  deleteAiConfig(keyId?: number): Promise<{ success: boolean; message?: string; data?: { remaining: number } }> {
    return request.delete('/api/ai/config', { data: keyId !== undefined ? { key_id: keyId } : {} }).then((res) => res.data)
  },

  batchAddKeys(keys: string[]): Promise<{ success: boolean; data?: { added: number; skipped: number }; message?: string }> {
    return request.post('/api/ai/keys/batch', { keys }).then((res) => res.data)
  },

  async enhancePrompt(
    payload: { text: string; images?: string[]; model?: string; platform?: string },
    onChunk: (content: string) => void,
    onDone: (fullContent: string) => void,
    onError: (message: string) => void,
    onKeyInfo?: (keyId: number, masked: string) => void,
  ): Promise<void> {
    let resp: Response
    try {
      resp = await fetch(`${baseURL}/api/ai/enhance-prompt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Network error')
      return
    }

    if (!resp.ok) {
      try {
        const errBody = await resp.json()
        onError(errBody.message || `HTTP ${resp.status}`)
      } catch {
        onError(`HTTP ${resp.status}`)
      }
      return
    }

    const reader = resp.body?.getReader()
    if (!reader) {
      onError('No response body')
      return
    }

    const decoder = new TextDecoder()
    let buffer = ''
    let fullContent = ''
    let doneReceived = false

    try {
      let eventType = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim()
            continue
          }
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (eventType === 'data') {
                fullContent += (data.content ?? '')
                onChunk(data.content ?? '')
              } else if (eventType === 'done') {
                doneReceived = true
                onDone(data.content ?? fullContent)
              } else if (eventType === 'key_info') {
                if (onKeyInfo && typeof data.id === 'number') {
                  onKeyInfo(data.id, data.masked || '')
                }
              } else if (eventType === 'error') {
                onError(data.message || 'Unknown error')
                return
              }
            } catch { /* skip malformed */ }
          }
        }
      }
      if (!doneReceived && fullContent) {
        onDone(fullContent)
      }
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Stream error')
    } finally {
      reader.releaseLock()
    }
  },

  async generateAiContentStream(
    payload: { prompt: string; model?: string; system_prompt?: string; platform?: string; images?: string[] },
    onChunk: (content: string) => void,
    onDone: (fullContent: string) => void,
    onError: (message: string) => void,
    onKeyInfo?: (keyId: number, masked: string) => void,
  ): Promise<void> {
    let resp: Response
    try {
      resp = await fetch(`${baseURL}/api/ai/generate/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Network error')
      return
    }

    if (!resp.ok) {
      try {
        const errBody = await resp.json()
        onError(errBody.message || `HTTP ${resp.status}`)
      } catch {
        onError(`HTTP ${resp.status}`)
      }
      return
    }

    const reader = resp.body?.getReader()
    if (!reader) {
      onError('No response body')
      return
    }

    const decoder = new TextDecoder()
    let buffer = ''
    let fullContent = ''
    let doneReceived = false

    try {
      let eventType = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim()
            continue
          }
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (eventType === 'data') {
                fullContent += (data.content ?? '')
                onChunk(data.content ?? '')
              } else if (eventType === 'done') {
                doneReceived = true
                onDone(data.content ?? fullContent)
              } else if (eventType === 'key_info') {
                if (onKeyInfo && typeof data.id === 'number') {
                  onKeyInfo(data.id, data.masked || '')
                }
              } else if (eventType === 'error') {
                onError(data.message || 'Unknown error')
                return
              }
            } catch { /* skip malformed */ }
          }
        }
      }
      if (!doneReceived && fullContent) {
        onDone(fullContent)
      }
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Stream error')
    } finally {
      reader.releaseLock()
    }
  },

  /**
   * Multi-turn variant of generateAiContentStream: forwards a `messages`
   * array verbatim to `/api/ai/generate/stream` (the backend route accepts
   * multi-turn when a non-empty `messages` array is present).
   *
   * Maps SSE events to callbacks the same way as the single-turn path.
   * Uses an `AbortSignal` (when supplied) so the chat pipeline can
   * disconnect in-flight streams on cancel or unmount.
   */
  async generateMessagesStream(
    payload: {
      messages: Array<{ role: string; content: unknown }>
      model?: string
      platform?: string
    },
    onChunk: (content: string) => void,
    onDone: (fullContent: string) => void,
    onError: (message: string) => void,
    onKeyInfo?: (keyId: number, masked: string) => void,
    signal?: AbortSignal,
  ): Promise<void> {
    let resp: Response
    try {
      resp = await fetch(`${baseURL}/api/ai/generate/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal,
      })
    } catch (err) {
      // AbortError is intentional cancellation; swallow it silently so the
      // chat pipeline's cancel handler can do its own bookkeeping.
      if (err instanceof DOMException && err.name === 'AbortError') return
      // Other fetch failures (network down, CORS, DNS): report via callback.
      onError(err instanceof Error ? err.message : 'Network error')
      return
    }

    if (!resp.ok) {
      try {
        const errBody = await resp.json()
        onError(errBody.message || `HTTP ${resp.status}`)
      } catch {
        onError(`HTTP ${resp.status}`)
      }
      return
    }

    const reader = resp.body?.getReader()
    if (!reader) {
      onError('No response body')
      return
    }

    const decoder = new TextDecoder()
    let buffer = ''
    let fullContent = ''
    let doneReceived = false

    try {
      let eventType = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim()
            continue
          }
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (eventType === 'data') {
                fullContent += (data.content ?? '')
                onChunk(data.content ?? '')
              } else if (eventType === 'done') {
                doneReceived = true
                onDone(data.content ?? fullContent)
              } else if (eventType === 'key_info') {
                if (onKeyInfo && typeof data.id === 'number') {
                  onKeyInfo(data.id, data.masked || '')
                }
              } else if (eventType === 'error') {
                onError(data.message || 'Unknown error')
                return
              }
            } catch { /* skip malformed */ }
          }
        }
      }
      if (!doneReceived && fullContent) {
        onDone(fullContent)
      }
    } catch (err) {
      // Same rule: silent on cancel.
      if (err instanceof DOMException && err.name === 'AbortError') return
      onError(err instanceof Error ? err.message : 'Stream error')
    } finally {
      reader.releaseLock()
    }
  },
}
