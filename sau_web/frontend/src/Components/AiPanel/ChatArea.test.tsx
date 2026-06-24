import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ChatArea } from './ChatArea'
import { useChatStore } from '@/stores/useChatStore'

beforeEach(() => {
  useChatStore.getState().reset()
})

describe('ChatArea — empty state', () => {
  it('shows the empty hint when no active session and no draft', () => {
    render(<ChatArea />)
    expect(screen.getByText(/点击上方「一键生成」/)).toBeDefined()
  })

  it('hides the empty hint when a stream is in flight (draft non-empty)', () => {
    // No active session, but a draft is being typed
    useChatStore.getState().appendStreamingChunk('partial')
    render(<ChatArea />)
    expect(screen.queryByText(/点击上方「一键生成」/)).toBeNull()
    expect(screen.getByText('partial')).toBeDefined()
  })

  it('hides the empty hint when the session has messages', () => {
    const sid = useChatStore.getState().newSession('video', 'douyin')
    useChatStore.getState().appendUserMessage(sid, { content: 'first turn' })
    render(<ChatArea />)
    expect(screen.queryByText(/点击上方「一键生成」/)).toBeNull()
    expect(screen.getByText('first turn')).toBeDefined()
  })
})

describe('ChatArea — message rendering', () => {
  it('renders user messages with right alignment', () => {
    const sid = useChatStore.getState().newSession('video', 'douyin')
    useChatStore.getState().appendUserMessage(sid, { content: '给我一个标题' })
    render(<ChatArea />)
    const bubble = screen.getByText('给我一个标题')
    // Container element should justify-end (right-aligned).
    const li = bubble.closest('li')
    expect(li?.className).toContain('justify-end')
  })

  it('renders assistant messages with left alignment and AI label', () => {
    const sid = useChatStore.getState().newSession('note', 'xiaohongshu')
    useChatStore.getState().appendUserMessage(sid, { content: 'q' })
    useChatStore.getState().appendStreamingChunk('答案: 你好世界')
    useChatStore.getState().commitAssistantMessage(sid)
    render(<ChatArea />)
    expect(screen.getByText('答案: 你好世界')).toBeDefined()
    expect(screen.getByText('AI')).toBeDefined()
    const answer = screen.getByText('答案: 你好世界')
    const li = answer.closest('li')
    expect(li?.className).toContain('justify-start')
  })

  it('renders system snapshot messages with italic muted styling', () => {
    // System messages can appear in history but are rare in practice. Test
    // by direct injection into the session.
    const sid = useChatStore.getState().newSession('video', 'douyin')
    // Hack: appendUserMessage only takes role 'user'; for the test, build
    // a session with a synthetic sys message via direct state mutation.
    useChatStore.setState((s) => ({
      sessions: {
        ...s.sessions,
        [sid]: {
          ...s.sessions[sid],
          messages: [
            {
              id: 'sys-1',
              role: 'system',
              content: '[当前表单状态] 标题: 老王',
              createdAt: Date.now(),
            },
          ],
        },
      },
    }))
    render(<ChatArea />)
    const sysLine = screen.getByText(/当前表单状态/)
    expect(sysLine.tagName).toBe('LI')
    expect(sysLine.className).toContain('italic')
  })

  it('renders the appliedTo chip when present', () => {
    const sid = useChatStore.getState().newSession('video', 'douyin')
    useChatStore.getState().appendUserMessage(sid, { content: 'q' })
    useChatStore.getState().appendStreamingChunk('a')
    const msg = useChatStore.getState().commitAssistantMessage(sid)!
    useChatStore.getState().markApplied(sid, msg.id, ['title', 'tags'])
    render(<ChatArea />)
    // ChatArea currently renders raw field names (English). When localized,
    // these should switch to 标题/描述/标签.
    expect(screen.getByText(/已应用到:.*title.*tags/)).toBeDefined()
  })
})

describe('ChatArea — streaming draft', () => {
  it('shows streamingDraft + caret when jobStatus === "generating"', () => {
    // Open a session so chat store has somewhere to anchor the stream
    const sid = useChatStore.getState().newSession('video', 'douyin')
    useChatStore.setState({
      streamingDraft: '正在打字…',
      jobStatus: 'generating',
      activeSessionId: sid,
    })
    render(<ChatArea />)
    expect(screen.getByText('正在打字…')).toBeDefined()
    // Caret is a span — we don't put a data-testid by default, so just
    // verify the text alongside the caret visually:
    expect(screen.getByText('正在打字…').parentElement?.querySelector('span.animate-pulse')).not.toBeNull()
  })

  it('does NOT show streaming text when draft is empty even if jobStatus says generating', () => {
    useChatStore.setState({ jobStatus: 'generating', streamingDraft: '' })
    render(<ChatArea />)
    // Streaming caret should not appear (empty draft hides the bubble)
    // — but the empty hint shows.
    expect(screen.getByText(/点击上方「一键生成」/)).toBeDefined()
  })
})

describe('ChatArea — error block', () => {
  it('renders the chat error when status is error', () => {
    useChatStore.setState({ jobStatus: 'error', error: 'API quota exhausted' })
    render(<ChatArea />)
    expect(screen.getByText('API quota exhausted')).toBeDefined()
    expect(screen.getByText('API quota exhausted').className).toContain('text-destructive')
  })

  it('does NOT render the error block when status recovers to idle', () => {
    useChatStore.setState({ jobStatus: 'error', error: 'temp err' })
    useChatStore.setState({ jobStatus: 'idle', error: null })
    render(<ChatArea />)
    expect(screen.queryByText('temp err')).toBeNull()
  })
})
