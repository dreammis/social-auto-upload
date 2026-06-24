import { describe, it, expect, beforeEach } from 'vitest'
import { useChatStore } from './useChatStore'

beforeEach(() => {
  useChatStore.getState().reset()
})

// ─── helpers ──────────────────────────────────────────────────────────────

function session() {
  return useChatStore.getState().newSession('video', 'douyin')
}

// ─── session lifecycle ────────────────────────────────────────────────────

describe('useChatStore — session lifecycle', () => {
  it('newSession creates a session, sets active, returns an id', () => {
    const id = session()
    expect(id).toBeTruthy()
    const s = useChatStore.getState()
    expect(s.activeSessionId).toBe(id)
    expect(s.sessions[id].formMode).toBe('video')
    expect(s.sessions[id].platform).toBe('douyin')
    expect(s.sessions[id].title).toBe('新对话')
    expect(s.sessions[id].messages).toHaveLength(0)
    expect(s.sessions[id].totalSize).toBe(0)
  })

  it('switchSession to existing id sets active and returns true', () => {
    const a = session()
    const b = useChatStore.getState().newSession('note', 'xiaohongshu')
    expect(useChatStore.getState().activeSessionId).toBe(b)
    expect(useChatStore.getState().switchSession(a)).toBe(true)
    expect(useChatStore.getState().activeSessionId).toBe(a)
  })

  it('switchSession to non-existent id returns false and leaves active unchanged', () => {
    const a = session()
    const ok = useChatStore.getState().switchSession('does-not-exist')
    expect(ok).toBe(false)
    expect(useChatStore.getState().activeSessionId).toBe(a)
  })

  it('deleteSession removes the session', () => {
    const a = session()
    const b = useChatStore.getState().newSession('note', 'xiaohongshu')
    useChatStore.getState().deleteSession(a)
    expect(useChatStore.getState().sessions[a]).toBeUndefined()
    expect(useChatStore.getState().sessions[b]).toBeDefined()
  })

  it('deleteSession of actively-selected session clears activeSessionId', () => {
    const a = session()
    useChatStore.getState().deleteSession(a)
    expect(useChatStore.getState().activeSessionId).toBeNull()
  })

  it('deleteSession of non-active session preserves activeSessionId', () => {
    const a = session()
    const b = useChatStore.getState().newSession('note')
    useChatStore.getState().switchSession(b)
    useChatStore.getState().deleteSession(a)
    expect(useChatStore.getState().activeSessionId).toBe(b)
  })

  it('deleteSession of unknown id is a no-op', () => {
    session()
    const before = useChatStore.getState().sessions
    useChatStore.getState().deleteSession('no-such-id')
    expect(useChatStore.getState().sessions).toBe(before)
  })
})

// ─── user message append ──────────────────────────────────────────────────

describe('useChatStore — appendUserMessage', () => {
  it('returns false and is a no-op when session missing', () => {
    const ok = useChatStore.getState().appendUserMessage('no-such', { content: 'hi' })
    expect(ok).toBe(false)
    expect(useChatStore.getState().sessions['no-such']).toBeUndefined()
  })

  it('appends to the session and updates totalSize/updatedAt', async () => {
    const id = session()
    const before = useChatStore.getState().sessions[id].updatedAt
    // yield so Date.now() can move forward
    await new Promise((r) => setTimeout(r, 2))
    expect(useChatStore.getState().appendUserMessage(id, { content: '一份新文案' })).toBe(true)
    const s = useChatStore.getState().sessions[id]
    expect(s.messages).toHaveLength(1)
    expect(s.messages[0].role).toBe('user')
    expect(s.messages[0].content).toBe('一份新文案')
    expect(s.totalSize).toBe('一份新文案'.length)
    expect(s.updatedAt).toBeGreaterThan(before)
  })

  it('derives session title from the first user message (truncated to 24 + ellipsis)', () => {
    const id = session()
    useChatStore.getState().appendUserMessage(id, { content: '123456789012345678901234567890123' })
    expect(useChatStore.getState().sessions[id].title).toBe('123456789012345678901234…')
  })

  it('does NOT overwrite the title on subsequent messages', () => {
    const id = session()
    useChatStore.getState().appendUserMessage(id, { content: 'first one' })
    useChatStore.getState().appendUserMessage(id, { content: 'second one' })
    expect(useChatStore.getState().sessions[id].title).toBe('first one')
  })

  it('records formContextAtSend verbatim', () => {
    const id = session()
    useChatStore.getState().appendUserMessage(id, {
      content: '缩短标题',
      formContextAtSend: { title: '无敌美食', desc: '', tags: '' },
    })
    const msg = useChatStore.getState().sessions[id].messages[0]
    expect(msg.formContextAtSend).toEqual({ title: '无敌美食', desc: '', tags: '' })
  })
})

// ─── streaming commit (happy path) ────────────────────────────────────────

describe('useChatStore — streaming commit', () => {
  it('appendStreamingChunk accumulates draft and flips status to "generating"', () => {
    session()
    expect(useChatStore.getState().jobStatus).toBe('idle')
    useChatStore.getState().appendStreamingChunk('标题')
    useChatStore.getState().appendStreamingChunk(': ')
    useChatStore.getState().appendStreamingChunk('三分钟搞定')
    const s = useChatStore.getState()
    expect(s.streamingDraft).toBe('标题: 三分钟搞定')
    expect(s.jobStatus).toBe('generating')
  })

  it('appendStreamingChunk with empty string is a no-op (does not touch state)', () => {
    session()
    useChatStore.getState().appendStreamingChunk('hello')
    const before = useChatStore.getState()
    useChatStore.getState().appendStreamingChunk('')
    const after = useChatStore.getState()
    expect(after.streamingDraft).toBe(before.streamingDraft)
    expect(after.jobStatus).toBe(before.jobStatus)
  })

  it('commitAssistantMessage finalizes the draft into an assistant message and returns it', () => {
    const id = session()
    useChatStore.getState().appendStreamingChunk('完整回答')
    const committed = useChatStore.getState().commitAssistantMessage(id)
    expect(committed).not.toBeNull()
    expect(committed!.role).toBe('assistant')
    expect(committed!.content).toBe('完整回答')
    const s = useChatStore.getState()
    expect(s.streamingDraft).toBe('')
    expect(s.jobStatus).toBe('idle')
    expect(s.sessions[id].messages).toHaveLength(1)
    expect(s.sessions[id].messages[0]).toBe(committed)
    expect(s.sessions[id].totalSize).toBe('完整回答'.length)
  })

  it('commitAssistantMessage returns null and is a no-op when draft is empty', () => {
    const id = session()
    const committed = useChatStore.getState().commitAssistantMessage(id)
    expect(committed).toBeNull()
    expect(useChatStore.getState().sessions[id].messages).toHaveLength(0)
  })

  it('commitAssistantMessage returns null when session id is unknown', () => {
    session()
    useChatStore.getState().appendStreamingChunk('projecting')
    expect(useChatStore.getState().commitAssistantMessage('no-such')).toBeNull()
    expect(useChatStore.getState().streamingDraft).toBe('projecting') // draft preserved
  })

  it('full lifecycle: newSession → user msg → stream chunks → commit', () => {
    const id = session()
    useChatStore.getState().appendUserMessage(id, { content: '请写一个炸鸡标题' })
    useChatStore.getState().appendStreamingChunk('标题: ')
    useChatStore.getState().appendStreamingChunk('一分钟学会脆皮炸鸡')
    const committed = useChatStore.getState().commitAssistantMessage(id)
    const s = useChatStore.getState().sessions[id]
    expect(s.messages.map((m) => m.role)).toEqual(['user', 'assistant'])
    expect(s.messages[1]).toBe(committed)
    expect(committed!.content).toBe('标题: 一分钟学会脆皮炸鸡')
    expect(useChatStore.getState().streamingDraft).toBe('')
    expect(useChatStore.getState().jobStatus).toBe('idle')
  })

  it('commit clears error in addition to draft', () => {
    const id = session()
    useChatStore.getState().setJobStatus('error', 'something broke earlier')
    useChatStore.getState().appendStreamingChunk('follow-up')
    useChatStore.getState().commitAssistantMessage(id)
    expect(useChatStore.getState().error).toBeNull()
  })
})

// ─── cancelStream ─────────────────────────────────────────────────────────

describe('useChatStore — cancelStream', () => {
  it('returns true and clears draft when was generating', () => {
    const id = session()
    useChatStore.getState().appendStreamingChunk('一半的')
    expect(useChatStore.getState().streamingDraft).toBeTruthy()
    expect(useChatStore.getState().cancelStream()).toBe(true)
    expect(useChatStore.getState().streamingDraft).toBe('')
    expect(useChatStore.getState().jobStatus).toBe('idle')
    expect(useChatStore.getState().sessions[id].messages).toHaveLength(0) // nothing committed yet
  })

  it('returns true when was enhancing', () => {
    session()
    useChatStore.getState().setJobStatus('enhancing')
    expect(useChatStore.getState().cancelStream()).toBe(true)
    expect(useChatStore.getState().jobStatus).toBe('idle')
  })

  it('returns false and is a true no-op when already idle', () => {
    session()
    const before = useChatStore.getState()
    expect(useChatStore.getState().cancelStream()).toBe(false)
    expect(useChatStore.getState()).toEqual(before)
  })

  it('returns false when was already in error state', () => {
    session()
    useChatStore.getState().setJobStatus('error', 'boom')
    expect(useChatStore.getState().cancelStream()).toBe(false)
    expect(useChatStore.getState().jobStatus).toBe('error')
  })

  it('preserves already-committed messages (does NOT delete history)', () => {
    const id = session()
    useChatStore.getState().appendUserMessage(id, { content: 'turn 1' })
    useChatStore.getState().appendStreamingChunk('turn 1 answer')
    useChatStore.getState().commitAssistantMessage(id)
    useChatStore.getState().appendStreamingChunk('interrupted midstream')
    useChatStore.getState().cancelStream()
    const s = useChatStore.getState().sessions[id]
    expect(s.messages.map((m) => m.role)).toEqual(['user', 'assistant'])
    expect(s.messages[1].content).toBe('turn 1 answer')
  })
})

// ─── markApplied ──────────────────────────────────────────────────────────

describe('useChatStore — markApplied', () => {
  it('records the applied field on the target message', () => {
    const id = session()
    useChatStore.getState().appendUserMessage(id, { content: 'q' })
    useChatStore.getState().appendStreamingChunk('a')
    const a = useChatStore.getState().commitAssistantMessage(id)!
    expect(a.appliedTo).toBeUndefined()
    useChatStore.getState().markApplied(id, a.id, ['title'])
    expect(useChatStore.getState().sessions[id].messages[1].appliedTo).toEqual(['title'])
  })

  it('dedupes repeated fields across multiple calls', () => {
    const id = session()
    useChatStore.getState().appendUserMessage(id, { content: 'q' })
    useChatStore.getState().appendStreamingChunk('a')
    const a = useChatStore.getState().commitAssistantMessage(id)!
    useChatStore.getState().markApplied(id, a.id, ['title'])
    useChatStore.getState().markApplied(id, a.id, ['title', 'desc'])
    useChatStore.getState().markApplied(id, a.id, ['desc', 'tags'])
    expect(useChatStore.getState().sessions[id].messages[1].appliedTo).toEqual(['title', 'desc', 'tags'])
  })

  it('preserves prior fields when adding new ones', () => {
    const id = session()
    useChatStore.getState().appendUserMessage(id, { content: 'q' })
    useChatStore.getState().appendStreamingChunk('a')
    const a = useChatStore.getState().commitAssistantMessage(id)!
    useChatStore.getState().markApplied(id, a.id, ['title'])
    useChatStore.getState().markApplied(id, a.id, ['tags'])
    expect(useChatStore.getState().sessions[id].messages[1].appliedTo).toEqual(['title', 'tags'])
  })

  it('no-ops when session missing', () => {
    const id = session()
    useChatStore.getState().appendUserMessage(id, { content: 'q' })
    useChatStore.getState().appendStreamingChunk('a')
    const a = useChatStore.getState().commitAssistantMessage(id)!
    const before = useChatStore.getState().sessions[id].messages
    useChatStore.getState().markApplied('no-such', a.id, ['title'])
    expect(useChatStore.getState().sessions[id].messages).toBe(before) // referentially unchanged
  })

  it('no-ops with empty fields array (does not pollute appliedTo)', () => {
    const id = session()
    useChatStore.getState().appendUserMessage(id, { content: 'q' })
    useChatStore.getState().appendStreamingChunk('a')
    const a = useChatStore.getState().commitAssistantMessage(id)!
    useChatStore.getState().markApplied(id, a.id, [])
    expect(useChatStore.getState().sessions[id].messages[1].appliedTo).toBeUndefined()
  })
})

// ─── setJobStatus + error ──────────────────────────────────────────────────

describe('useChatStore — setJobStatus + error', () => {
  it('updates jobStatus and stores error message', () => {
    session()
    useChatStore.getState().setJobStatus('error', 'API quota exhausted')
    expect(useChatStore.getState().jobStatus).toBe('error')
    expect(useChatStore.getState().error).toBe('API quota exhausted')
  })

  it('clears error when called with no message even from error state', () => {
    session()
    useChatStore.getState().setJobStatus('error', 'first error')
    useChatStore.getState().setJobStatus('idle')
    expect(useChatStore.getState().jobStatus).toBe('idle')
    expect(useChatStore.getState().error).toBeNull()
  })
})

// ─── hydrate + reset ──────────────────────────────────────────────────────

describe('useChatStore — hydrate + reset', () => {
  it('hydrate populates sessions and active', () => {
    const sessions = [
      {
        id: 's1',
        title: 'first',
        messages: [],
        formMode: 'video' as const,
        updatedAt: 1,
        totalSize: 0,
      },
      {
        id: 's2',
        title: 'second',
        messages: [],
        formMode: 'note' as const,
        updatedAt: 2,
        totalSize: 0,
      },
    ]
    useChatStore.getState().hydrate(sessions, 's2')
    expect(useChatStore.getState().sessions.s1.id).toBe('s1')
    expect(useChatStore.getState().sessions.s2.id).toBe('s2')
    expect(useChatStore.getState().activeSessionId).toBe('s2')
  })

  it('hydrate ignores an unknown activeId', () => {
    useChatStore.getState().hydrate(
      [
        {
          id: 's1',
          title: 'first',
          messages: [],
          formMode: 'video' as const,
          updatedAt: 1,
          totalSize: 0,
        },
      ],
      'no-such-session',
    )
    expect(useChatStore.getState().activeSessionId).toBeNull()
    expect(useChatStore.getState().sessions.s1).toBeDefined()
  })

  it('reset zeroes everything', () => {
    const id = session()
    useChatStore.getState().setJobStatus('error', 'x')
    useChatStore.getState().appendStreamingChunk('leftover')
    useChatStore.getState().reset()
    const s = useChatStore.getState()
    expect(s.activeSessionId).toBeNull()
    expect(s.sessions).toEqual({})
    expect(s.jobStatus).toBe('idle')
    expect(s.streamingDraft).toBe('')
    expect(s.error).toBeNull()
    expect(s.sessions[id]).toBeUndefined()
  })
})
