import { create } from 'zustand'
import type {
  ChatMessage,
  ChatSession,
  FormMode,
  JobStatus,
} from '@/lib/chat/types'

const newId = (): string => crypto.randomUUID()

function approxMessageSize(m: Pick<ChatMessage, 'content' | 'attachments'>): number {
  let n = m.content.length
  if (m.attachments) for (const a of m.attachments) n += a.dataUrl.length
  return n
}

function deriveTitle(userText: string): string {
  if (!userText) return '新对话'
  return userText.length > 24 ? userText.slice(0, 24) + '…' : userText
}

export interface ChatState {
  activeSessionId: string | null
  sessions: Record<string, ChatSession>
  jobStatus: JobStatus
  /** SSE accumulator. Cleared on commit or cancel. Never persisted raw. */
  streamingDraft: string
  error: string | null
}

export interface ChatActions {
  newSession: (formMode: FormMode, platform?: string) => string
  switchSession: (id: string) => boolean
  deleteSession: (id: string) => void
  appendUserMessage: (
    sessionId: string,
    msg: Pick<ChatMessage, 'content' | 'attachments' | 'formContextAtSend'>,
  ) => boolean
  /** Append a streamed chunk; flips jobStatus to 'generating'. */
  appendStreamingChunk: (chunk: string) => void
  /** Commit the streamed draft as a final assistant message. */
  commitAssistantMessage: (sessionId: string) => ChatMessage | null
  /** Abort in-flight stream; preserves all already-committed messages. */
  cancelStream: () => boolean
  markApplied: (sessionId: string, messageId: string, fields: string[]) => void
  setJobStatus: (s: JobStatus, err?: string | null) => void
  hydrate: (sessions: ChatSession[], activeId: string | null) => void
  reset: () => void
}

const INITIAL: ChatState = {
  activeSessionId: null,
  sessions: {},
  jobStatus: 'idle',
  streamingDraft: '',
  error: null,
}

export const useChatStore = create<ChatState & ChatActions>((set, get) => ({
  ...INITIAL,

  newSession: (formMode, platform) => {
    const id = newId()
    const now = Date.now()
    const session: ChatSession = {
      id,
      title: '新对话',
      messages: [],
      formMode,
      platform,
      updatedAt: now,
      totalSize: 0,
    }
    set((s) => ({ activeSessionId: id, sessions: { ...s.sessions, [id]: session } }))
    return id
  },

  switchSession: (id) => {
    if (!get().sessions[id]) return false
    set({ activeSessionId: id })
    return true
  },

  deleteSession: (id) => {
    if (!get().sessions[id]) return
    set((s) => {
      const next = { ...s.sessions }
      delete next[id]
      return {
        sessions: next,
        activeSessionId: s.activeSessionId === id ? null : s.activeSessionId,
      }
    })
  },

  appendUserMessage: (sessionId, msg) => {
    const session = get().sessions[sessionId]
    if (!session) return false
    const message: ChatMessage = {
      id: newId(),
      role: 'user',
      content: msg.content,
      attachments: msg.attachments,
      formContextAtSend: msg.formContextAtSend,
      createdAt: Date.now(),
    }
    const title = session.messages.length === 0 ? deriveTitle(msg.content) : session.title
    const updated: ChatSession = {
      ...session,
      title,
      messages: [...session.messages, message],
      updatedAt: Date.now(),
      totalSize: session.totalSize + approxMessageSize(message),
    }
    set((s) => ({ sessions: { ...s.sessions, [sessionId]: updated } }))
    return true
  },

  appendStreamingChunk: (chunk) => {
    if (!chunk) return
    set((s) => ({ streamingDraft: s.streamingDraft + chunk, jobStatus: 'generating' }))
  },

  commitAssistantMessage: (sessionId) => {
    const { streamingDraft, sessions } = get()
    const session = sessions[sessionId]
    if (!session || !streamingDraft) return null
    const message: ChatMessage = {
      id: newId(),
      role: 'assistant',
      content: streamingDraft,
      createdAt: Date.now(),
    }
    const updated: ChatSession = {
      ...session,
      messages: [...session.messages, message],
      updatedAt: Date.now(),
      totalSize: session.totalSize + approxMessageSize(message),
    }
    set((s) => ({
      streamingDraft: '',
      jobStatus: 'idle',
      error: null,
      sessions: { ...s.sessions, [sessionId]: updated },
    }))
    return message
  },

  cancelStream: () => {
    const { jobStatus } = get()
    const wasActive = jobStatus === 'generating' || jobStatus === 'enhancing'
    if (!wasActive) return false
    // Crucially: do NOT touch `sessions`. Already-committed messages
    // remain intact; only the in-flight draft is discarded.
    set({ streamingDraft: '', jobStatus: 'idle', error: null })
    return true
  },

  markApplied: (sessionId, messageId, fields) => {
    if (!fields.length) return
    const session = get().sessions[sessionId]
    if (!session) return
    set((s) => ({
      sessions: {
        ...s.sessions,
        [sessionId]: {
          ...session,
          messages: session.messages.map((m) =>
            m.id === messageId
              ? { ...m, appliedTo: Array.from(new Set([...(m.appliedTo ?? []), ...fields])) }
              : m,
          ),
        },
      },
    }))
  },

  setJobStatus: (jobStatus, error = null) => set({ jobStatus, error }),

  hydrate: (sessions, activeId) => {
    const byId: Record<string, ChatSession> = {}
    for (const s of sessions) byId[s.id] = s
    set({
      sessions: byId,
      activeSessionId: sessions.some((s) => s.id === activeId) ? activeId : null,
    })
  },

  reset: () => set(INITIAL),
}))
