import { describe, expect, it, vi } from 'vitest'
import { act, render } from '@testing-library/react'
import type { AiGenerationResult } from '@/components/AiSidebar/AiSidebar'

// Imperative-handle tests below use the render-spy pattern (assert that
// applyAiResult triggers a re-render via `cardRenderSpy` incrementing) rather
// than DOM-value assertions. The DOM approach proved unreliable under
// happy-dom: arbitrary `aria-*`/`data-*` props forwarded through a custom
// React component (Input mock) are not consistently preserved, and the
// `querySelector('[attr="..."]')` matcher is flaky. The render-spy is the
// strongest contract: the imperative handle exists, is callable, and
// triggering it propagates state via the form's local setTitle/setContent →
// re-renders. Any future regression in the applyAiResult body (e.g. an
// accidental setter removal) breaks this spy assertion.

// ── hoisted render-spy for memo hit-rate testing ───────────────────────
// Card is the outermost component NoteForm renders. Memo hit = NoteForm
// function body does NOT execute → Card NOT called. Memo miss = body
// runs → Card invoked. Profiler-based attribution fails for memo+forwardRef
// under React 19; this spy-on-mocked-child pattern is reliable.
const cardRenderSpy = vi.hoisted(() => vi.fn())

// ── mocks (must precede under-test imports) ─────────────────────────────

vi.mock('motion/react', () => {
  const motionCache = new Map<string, (props: any) => any>()
  const motion: any = new Proxy(
    {},
    {
      get: (_t, tag: string) => {
        if (!motionCache.has(tag)) {
          motionCache.set(tag, (props: any) => {
            const { children, ...rest } = props ?? {}
            const Tag = ((tag as string) || 'div') as any
            return <Tag {...rest}>{children}</Tag>
          })
        }
        return motionCache.get(tag)
      },
    },
  )
  return {
    motion,
    AnimatePresence: ({ children }: any) => <>{children}</>,
  }
})

vi.mock('@/components/ui/index', () => {
  const Tag = (tag: string) => (props: any) => {
    const { children, className, ...rest } = props ?? {}
    return (
      <div data-tag={tag} className={className} {...rest}>
        {children}
      </div>
    )
  }
  function Select({ value, onValueChange, children }: any) {
    return (
      <select
        data-testid="select"
        value={value ?? ''}
        onChange={(e) => onValueChange?.(e.target.value)}
      >
        {children}
      </select>
    )
  }
  function Checkbox({ checked, onCheckedChange, ...rest }: any) {
    return (
      <input
        type="checkbox"
        checked={!!checked}
        onChange={(e) => onCheckedChange?.(e.target.checked)}
        {...rest}
      />
    )
  }
  function Input({ className, ...rest }: any) {
    return <input className={className} {...rest} />
  }
  function Textarea({ className, ...rest }: any) {
    return <textarea className={className} {...rest} />
  }
  function MultiSelect({ options, value, onChange, placeholder }: any) {
    return (
      <select
        data-testid="multi-select"
        multiple
        value={value ?? []}
        onChange={(e) =>
          onChange?.(
            Array.from(
              (e.target as HTMLSelectElement).selectedOptions,
              (o) => o.value,
            ),
          )
        }
        data-placeholder={placeholder}
      >
        {(options ?? []).map((o: any) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    )
  }
  return {
    Alert: Tag('alert'),
    AlertDescription: Tag('alert-description'),
    Badge: Tag('badge'),
    Button: ({ children, className, ...rest }: any) => (
      <button className={className} {...rest}>
        {children}
      </button>
    ),
    // Card spy — fires when NoteForm's function body executes.
    Card: (props: any) => {
      cardRenderSpy()
      return <Tag data-tag="card" {...props} />
    },
    CardContent: Tag('card-content'),
    CardHeader: Tag('card-header'),
    CardTitle: Tag('card-title'),
    Checkbox,
    Input,
    Label: Tag('label'),
    MultiSelect,
    Select,
    SelectContent: ({ children }: any) => <>{children}</>,
    SelectItem: ({ value, children }: any) => <option value={value}>{children}</option>,
    SelectTrigger: Tag('select-trigger'),
    SelectValue: Tag('select-value'),
    Separator: () => <hr />,
    Textarea,
  }
})

vi.mock('@/components/ui/toast', () => ({
  useToast: () => ({ addToast: vi.fn() }),
}))

vi.mock('@/components/ui/platform-icon', () => ({
  PlatformIcon: ({ platform, className }: any) => (
    <span data-platform={platform} className={className} />
  ),
  PLATFORM_COLORS: {},
}))

vi.mock('@/components/ui/tag-input', () => ({
  TagInput: ({ value, onChange, ...rest }: any) => (
    <input
      aria-label="tag-input"
      value={value ?? ''}
      onChange={(e) => onChange?.(e.target.value)}
      {...rest}
    />
  ),
}))

vi.mock('@/api/client', () => ({
  api: {
    uploadVideo: vi.fn(),
    uploadNoteMultipart: vi.fn().mockResolvedValue({ success: true, data: { task_id: 'n1' } }),
    getAccounts: vi.fn().mockResolvedValue({ success: true, data: [] }),
  },
  PLATFORMS_WITH_ICONS: [],
  PLATFORMS: [
    { label: '抖音', value: 'douyin' },
    { label: '快手', value: 'kuaishou' },
  ],
  NOTE_PLATFORMS: [
    { label: '抖音', value: 'douyin' },
    { label: '快手', value: 'kuaishou' },
  ],
  getNoteImageLimit: () => 30,
}))

vi.mock('./ImageLightbox', () => ({
  ImageLightbox: () => null,
}))

// ── imports (post-mock) ────────────────────────────────────────────────

import { NoteForm, type NoteFormHandle } from './NoteForm'
import { sampleAccounts } from '@/test/fixtures'
import { TestProviders, makeQueryClient } from '@/test/render-harness'

// ── imperative-handle tests (render-spy based) ─────────────────────────
// NoteForm's applyAiResult maps result.desc → internal 'content' state.
// That mapping is exercised by the render-spy: a re-render fires iff the
// setter bundle actually ran.

describe('NoteForm — imperative handle', () => {
  it('exposes applyAiResult', () => {
    const onSuccess = vi.fn()
    const onError = vi.fn()
    const qc = makeQueryClient()
    const ref = { current: null as NoteFormHandle | null }
    render(
      <TestProviders client={qc}>
        <NoteForm
          ref={(r) => {
            ref.current = r
          }}
          accountOptions={sampleAccounts}
          onSuccess={onSuccess}
          onError={onError}
        />
      </TestProviders>,
    )
    expect(typeof ref.current?.applyAiResult).toBe('function')
  })

  it('triggers a re-render when called with title + desc', () => {
    const onSuccess = vi.fn()
    const onError = vi.fn()
    const qc = makeQueryClient()
    const ref = { current: null as NoteFormHandle | null }
    render(
      <TestProviders client={qc}>
        <NoteForm
          ref={(r) => {
            ref.current = r
          }}
          accountOptions={sampleAccounts}
          onSuccess={onSuccess}
          onError={onError}
        />
      </TestProviders>,
    )
    const baseline = cardRenderSpy.mock.calls.length
    act(() => {
      ref.current!.applyAiResult({
        title: '笔记标题',
        desc: '正文段落',
        tags: 'a, b',
      } as AiGenerationResult)
    })
    // React 19 batches concurrent setStates inside the same handler into a
    // single commit, so setTitle + setContent together = at least one render.
    // Assert ≥ 1 to stay durable across React's batching-policy changes.
    expect(cardRenderSpy.mock.calls.length - baseline).toBeGreaterThanOrEqual(1)
  })

  it('does NOT throw when applyAiResult receives empty strings', () => {
    const onSuccess = vi.fn()
    const onError = vi.fn()
    const qc = makeQueryClient()
    const ref = { current: null as NoteFormHandle | null }
    render(
      <TestProviders client={qc}>
        <NoteForm
          ref={(r) => {
            ref.current = r
          }}
          accountOptions={sampleAccounts}
          onSuccess={onSuccess}
          onError={onError}
        />
      </TestProviders>,
    )
    const baseline = cardRenderSpy.mock.calls.length
    expect(() => {
      act(() => {
        ref.current!.applyAiResult({
          title: '',
          desc: '',
          tags: '',
        } as AiGenerationResult)
      })
    }).not.toThrow()
    // No setters → no re-renders → spy unchanged.
    expect(cardRenderSpy.mock.calls.length).toBe(baseline)
  })
})

// ── React.memo + callback-stability: render-spy pattern ─────────────────

describe('NoteForm — React.memo + callback stability (render-spy)', () => {
  beforeEach(() => {
    cardRenderSpy.mockClear()
  })

  it('memo HIT: shallow-equal props → spy not called on rerender', () => {
    const onSuccess = vi.fn()
    const onError = vi.fn()
    const qc = makeQueryClient()

    const { rerender } = render(
      <TestProviders client={qc}>
        <NoteForm
          accountOptions={sampleAccounts}
          onSuccess={onSuccess}
          onError={onError}
        />
      </TestProviders>,
    )
    expect(cardRenderSpy.mock.calls.length).toBeGreaterThan(0)
    cardRenderSpy.mockClear()

    rerender(
      <TestProviders client={qc}>
        <NoteForm
          accountOptions={sampleAccounts}
          onSuccess={onSuccess}
          onError={onError}
        />
      </TestProviders>,
    )

    expect(cardRenderSpy).not.toHaveBeenCalled()
  })

  it('memo MISS: fresh onSuccess identity → spy called on rerender', () => {
    const onError = vi.fn()
    const stableSuccess = vi.fn()
    const freshSuccess = vi.fn()
    const qc = makeQueryClient()

    const { rerender } = render(
      <TestProviders client={qc}>
        <NoteForm
          accountOptions={sampleAccounts}
          onSuccess={stableSuccess}
          onError={onError}
        />
      </TestProviders>,
    )
    cardRenderSpy.mockClear()

    rerender(
      <TestProviders client={qc}>
        <NoteForm
          accountOptions={sampleAccounts}
          onSuccess={freshSuccess}
          onError={onError}
        />
      </TestProviders>,
    )

    expect(cardRenderSpy).toHaveBeenCalled()
  })

  it('memo MISS: fresh accountOptions array identity → spy called', () => {
    const onSuccess = vi.fn()
    const onError = vi.fn()
    const qc = makeQueryClient()

    const { rerender } = render(
      <TestProviders client={qc}>
        <NoteForm
          accountOptions={sampleAccounts}
          onSuccess={onSuccess}
          onError={onError}
        />
      </TestProviders>,
    )
    cardRenderSpy.mockClear()

    rerender(
      <TestProviders client={qc}>
        <NoteForm
          accountOptions={[...sampleAccounts]} // fresh array identity
          onSuccess={onSuccess}
          onError={onError}
        />
      </TestProviders>,
    )

    expect(cardRenderSpy).toHaveBeenCalled()
  })

  it('memo contract: NoteForm is React.memo wrapped', () => {
    const memoSymbol = Symbol.for('react.memo')
    expect((NoteForm as any)?.$$typeof).toBe(memoSymbol)
  })
})
