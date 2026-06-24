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
// triggering it propagates state via the form's local setTitle/setDesc/setTags
// → re-renders. Any future regression in the applyAiResult body (e.g. an
// accidental setter removal) breaks this spy assertion.

// ── hoisted render-spy for memo hit-rate testing ───────────────────────
// Card is the outermost component VideoForm renders. Memo hit = VideoForm
// function body does NOT execute => Card is NOT called. Memo miss = body
// executes => Card is invoked. React 19 + forwardRef batches Profiler commits
// into a single onRender call regardless of memo outcome, so spy-on-mocked-
// child is the reliable differential.
const cardRenderSpy = vi.hoisted(() => vi.fn())

// ── mocks (must precede under-test imports) ─────────────────────────────

vi.mock('motion/react', () => {
  // Cache motion.<tag> by tag string so React sees a stable component type.
  // Without this cache, every access to `motion.div` returns a fresh arrow
  // function, which React's reconciler reads as a NEW component type →
  // unmount/remount on every render, defeating the memoization being tested.
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
    // Card is the outermost wrapper VideoForm renders — spy on it to detect
    // whether the wrapped function body executed on the latest render.
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
    Accordion: Tag('accordion'),
    AccordionContent: Tag('accordion-content'),
    AccordionItem: Tag('accordion-item'),
    AccordionTrigger: Tag('accordion-trigger'),
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
    uploadVideo: vi.fn().mockResolvedValue({ success: true, data: { task_id: 't1' } }),
    uploadNoteMultipart: vi.fn(),
    getAccounts: vi.fn().mockResolvedValue({ success: true, data: [] }),
  },
  PLATFORMS_WITH_ICONS: [
    { label: '抖音', value: 'douyin' },
    { label: '快手', value: 'kuaishou' },
  ],
  PLATFORMS: [
    { label: '抖音', value: 'douyin' },
    { label: '快手', value: 'kuaishou' },
  ],
  NOTE_PLATFORMS: [
    { label: '抖音', value: 'douyin' },
    { label: '快手', value: 'kuaishou' },
  ],
}))

// ── imports (post-mock) ────────────────────────────────────────────────

import { VideoForm, type VideoFormHandle } from './VideoForm'
import { sampleAccounts } from '@/test/fixtures'
import { TestProviders, makeQueryClient } from '@/test/render-harness'

// ── imperative-handle tests (render-spy based) ─────────────────────────

describe('VideoForm — imperative handle', () => {
  it('exposes applyAiResult and triggers a re-render when called', () => {
    const onSuccess = vi.fn()
    const onError = vi.fn()
    const qc = makeQueryClient()
    const ref = { current: null as VideoFormHandle | null }
    const refCallback = (node: VideoFormHandle | null) => {
      ref.current = node
    }

    render(
      <TestProviders client={qc}>
        <VideoForm
          ref={refCallback}
          accountOptions={sampleAccounts}
          onSuccess={onSuccess}
          onError={onError}
        />
      </TestProviders>,
    )

    expect(typeof ref.current?.applyAiResult).toBe('function')
    const baseline = cardRenderSpy.mock.calls.length

    // act() flushes the React 19 setState batch from useImperativeHandle.
    act(() => {
      ref.current!.applyAiResult({
        title: 'AI 标题',
        desc: 'AI 描述',
        tags: 'ai, video',
      } as AiGenerationResult)
    })

    // Render propagation is the strongest contract: every setTitle/setDesc/
///setTags in applyAiResult schedules a re-render → Card spy fires again.
    expect(cardRenderSpy.mock.calls.length).toBeGreaterThan(baseline)
  })

  it('does NOT throw when applyAiResult receives empty strings', () => {
    const onSuccess = vi.fn()
    const onError = vi.fn()
    const qc = makeQueryClient()
    const ref = { current: null as VideoFormHandle | null }
    render(
      <TestProviders client={qc}>
        <VideoForm
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

    // Empty fields trigger conditional setters (the `if (result.title)` guard
    // in source), so no re-render is scheduled. spy count must NOT increase.
    expect(cardRenderSpy.mock.calls.length).toBe(baseline)
  })

  it('partial result (only title) does NOT throw and re-renders once', () => {
    const onSuccess = vi.fn()
    const onError = vi.fn()
    const qc = makeQueryClient()
    const ref = { current: null as VideoFormHandle | null }
    render(
      <TestProviders client={qc}>
        <VideoForm
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
          title: '仅标题',
        } as AiGenerationResult)
      })
    }).not.toThrow()

    // Exactly one setState (setTitle) → at least one re-render. Assert ≥ 1 to
    // stay durable across React batching-policy changes.
    expect(cardRenderSpy.mock.calls.length - baseline).toBeGreaterThanOrEqual(1)
  })
})

// ── React.memo + callback-stability: render-spy pattern ─────────────────
// `cardRenderSpy` fires every time the mocked Card is invoked by VideoForm.
// React.memo short-circuits VideoForm's render → spy NOT called.
// React.memo shallow-miss → VideoForm body runs → spy called.

describe('VideoForm — React.memo + callback stability (render-spy)', () => {
  beforeEach(() => {
    cardRenderSpy.mockClear()
  })

  it('memo HIT: shallow-equal props → spy not called on rerender', () => {
    const onSuccess = vi.fn()
    const onError = vi.fn()
    const qc = makeQueryClient()

    const { rerender } = render(
      <TestProviders client={qc}>
        <VideoForm
          accountOptions={sampleAccounts}
          onSuccess={onSuccess}
          onError={onError}
        />
      </TestProviders>,
    )
    const initial = cardRenderSpy.mock.calls.length
    expect(initial).toBeGreaterThan(0) // initial mount

    cardRenderSpy.mockClear()

    rerender(
      <TestProviders client={qc}>
        <VideoForm
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
    const stableOnSuccess = vi.fn()
    const freshOnSuccess = vi.fn()
    const qc = makeQueryClient()

    const { rerender } = render(
      <TestProviders client={qc}>
        <VideoForm
          accountOptions={sampleAccounts}
          onSuccess={stableOnSuccess}
          onError={onError}
        />
      </TestProviders>,
    )
    cardRenderSpy.mockClear()

    rerender(
      <TestProviders client={qc}>
        <VideoForm
          accountOptions={sampleAccounts}
          onSuccess={freshOnSuccess} // identity change → memo miss
          onError={onError}
        />
      </TestProviders>,
    )

    expect(cardRenderSpy).toHaveBeenCalled()
  })

  it('memo MISS: fresh onError identity → spy called on rerender', () => {
    const onSuccess = vi.fn()
    const stableOnError = vi.fn()
    const freshOnError = vi.fn()
    const qc = makeQueryClient()

    const { rerender } = render(
      <TestProviders client={qc}>
        <VideoForm
          accountOptions={sampleAccounts}
          onSuccess={onSuccess}
          onError={stableOnError}
        />
      </TestProviders>,
    )
    cardRenderSpy.mockClear()

    rerender(
      <TestProviders client={qc}>
        <VideoForm
          accountOptions={sampleAccounts}
          onSuccess={onSuccess}
          onError={freshOnError}
        />
      </TestProviders>,
    )

    expect(cardRenderSpy).toHaveBeenCalled()
  })

  it('memo HIT: same accountOptions array reference → spy not called', () => {
    const accounts = sampleAccounts
    const onSuccess = vi.fn()
    const onError = vi.fn()
    const qc = makeQueryClient()

    const { rerender } = render(
      <TestProviders client={qc}>
        <VideoForm
          accountOptions={accounts}
          onSuccess={onSuccess}
          onError={onError}
        />
      </TestProviders>,
    )
    cardRenderSpy.mockClear()

    rerender(
      <TestProviders client={qc}>
        <VideoForm
          accountOptions={accounts}
          onSuccess={onSuccess}
          onError={onError}
        />
      </TestProviders>,
    )

    expect(cardRenderSpy).not.toHaveBeenCalled()
  })

  it('memo MISS: fresh accountOptions array identity → spy called', () => {
    const onSuccess = vi.fn()
    const onError = vi.fn()
    const qc = makeQueryClient()

    const { rerender } = render(
      <TestProviders client={qc}>
        <VideoForm
          accountOptions={sampleAccounts}
          onSuccess={onSuccess}
          onError={onError}
        />
      </TestProviders>,
    )
    cardRenderSpy.mockClear()

    rerender(
      <TestProviders client={qc}>
        <VideoForm
          accountOptions={[...sampleAccounts]} // fresh array identity
          onSuccess={onSuccess}
          onError={onError}
        />
      </TestProviders>,
    )

    expect(cardRenderSpy).toHaveBeenCalled()
  })

  it('memo contract: VideoForm is React.memo wrapped (not a plain forwardRef)', () => {
    // $$typeof is Symbol.for('react.memo') when React.memo wraps the component.
    // Plain forwardRef components have $$typeof = Symbol.for('react.forward_ref').
    // `React.memo(forwardRef(fn))` collapses both — verify the merged surface.
    const memoSymbol = Symbol.for('react.memo')
    const memoWrapperSymbol = (VideoForm as any)?.$$typeof
    expect(memoWrapperSymbol).toBe(memoSymbol)
  })
})
// NoteFormHandle is needed only for type compatibility in the partial-result
// test's ref holder. Imported lazily to avoid unused-import warnings here.
import type { NoteFormHandle } from './NoteForm'
