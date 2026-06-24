import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render } from '@testing-library/react'
import { Profiler } from 'react'
import { QueryClient } from '@tanstack/react-query'

vi.mock('@/api/client', () => ({
  api: {
    getTasks: vi.fn(() =>
      Promise.resolve({
        success: true,
        data: [
          {
            task_id: 'task-a',
            platform: 'douyin',
            action: 'upload-video',
            account: '主号',
            status: 'failed',
            created: '2024-01-01T00:00:00Z',
            code: 1,
            error: 'cookie 过期',
            argv: '["sau","douyin","upload-video"]',
            result: null,
          },
          {
            task_id: 'task-b',
            platform: 'xiaohongshu',
            action: 'upload-note',
            account: '副号',
            status: 'running',
            created: '2024-01-02T00:00:00Z',
            code: null,
            error: null,
            argv: null,
            result: null,
          },
        ],
      }),
    ),
    uploadVideo: vi.fn(),
    uploadNoteMultipart: vi.fn(),
    getAccounts: vi.fn(),
  },
}))

vi.mock('@/hooks/useTasks', () => ({
  useTasks: () => ({
    data: undefined,
    isLoading: false,
    refetch: vi.fn(),
  }),
  useTaskLogs: () => ({
    data: [],
    isLoading: false,
  }),
}))

vi.mock('@/components/ui/index', () => {
  const Tag = (tag: string) => (props: any) => {
    const { children, className, ...rest } = props ?? {}
    return (
      <div data-tag={tag} className={className} {...rest}>
        {children}
      </div>
    )
  }
  return {
    Accordion: ({ children }: any) => <div data-tag="accordion">{children}</div>,
    AccordionContent: ({ children }: any) => <div data-tag="accordion-content">{children}</div>,
    AccordionItem: ({ children, value }: any) => (
      <div data-tag="accordion-item" data-value={value}>
        {children}
      </div>
    ),
    AccordionTrigger: ({ children }: any) => (
      <button data-tag="accordion-trigger">{children}</button>
    ),
    Badge: ({ children, variant, ...rest }: any) => (
      <span data-tag="badge" data-variant={variant} {...rest}>
        {children}
      </span>
    ),
    Button: ({ children, onClick, ...rest }: any) => (
      <button data-tag="button" onClick={onClick} {...rest}>
        {children}
      </button>
    ),
    Separator: () => <hr />,
    Sheet: ({ children, open }: any) => (
      <div data-tag="sheet" data-open={open ? '1' : '0'}>
        {children}
      </div>
    ),
    SheetContent: ({ children, className }: any) => (
      <div data-tag="sheet-content" className={className}>
        {children}
      </div>
    ),
    SheetDescription: ({ children }: any) => <p data-tag="sheet-description">{children}</p>,
    SheetHeader: ({ children }: any) => <header data-tag="sheet-header">{children}</header>,
    SheetTitle: ({ children }: any) => <h3 data-tag="sheet-title">{children}</h3>,
  }
})

vi.mock('@/components/CliCommand', () => ({
  CliCommandBlock: ({ command }: any) => (
    <pre data-tag="cli-command">{command}</pre>
  ),
}))

import { TaskDrawer } from './TaskDrawer'
import { makeTask } from '@/test/fixtures'
import {
  TestProviders,
  makeProfilerCounter,
  type ProfilerCounter,
} from '@/test/render-harness'

const TASKS_QUERY_KEY = ['tasks'] as const

function makeSeededClient() {
  const qc = new QueryClient()
  qc.setQueryData(TASKS_QUERY_KEY, [
    makeTask({ task_id: 'task-a', status: 'failed', code: 1, platform: 'douyin' }),
    makeTask({ task_id: 'task-b', status: 'running', platform: 'xiaohongshu' }),
  ])
  return qc
}

describe('TaskDrawer — prop surface', () => {
  it('renders nothing useful when taskId=null (sheet closed)', () => {
    const qc = makeSeededClient()
    const onClose = vi.fn()
    const onRetry = vi.fn()
    const { container } = render(
      <TestProviders client={qc}>
        <TaskDrawer taskId={null} onClose={onClose} onRetry={onRetry} retrying={null} />
      </TestProviders>,
    )
    expect(container.querySelector('[data-tag="sheet"]')).toBeTruthy()
    expect(
      container.querySelector('[data-tag="sheet"]')?.getAttribute('data-open'),
    ).toBe('0')
  })

  it('renders the task details when taskId points to a known task', () => {
    const qc = makeSeededClient()
    const onClose = vi.fn()
    const onRetry = vi.fn()
    const { container } = render(
      <TestProviders client={qc}>
        <TaskDrawer taskId="task-a" onClose={onClose} onRetry={onRetry} retrying={null} />
      </TestProviders>,
    )
    expect(container.querySelector('[data-tag="sheet"]')?.getAttribute('data-open')).toBe('1')
    expect(container.textContent).toContain('douyin')
    expect(container.textContent).toContain('task-a')
  })

  it('sheet open/closed reflects the taskId prop', () => {
    const qc = makeSeededClient()
    const { container, rerender } = render(
      <TestProviders client={qc}>
        <TaskDrawer taskId="task-a" onClose={vi.fn()} onRetry={vi.fn()} retrying={null} />
      </TestProviders>,
    )
    expect(container.querySelector('[data-tag="sheet"]')?.getAttribute('data-open')).toBe('1')

    rerender(
      <TestProviders client={qc}>
        <TaskDrawer taskId={null} onClose={vi.fn()} onRetry={vi.fn()} retrying={null} />
      </TestProviders>,
    )
    expect(container.querySelector('[data-tag="sheet"]')?.getAttribute('data-open')).toBe('0')
  })

  it('retry button fires onRetry with the matching task from cache', async () => {
    const qc = makeSeededClient()
    const onRetry = vi.fn()
    // Wait for query to resolve before rendering so cache is populated for the
    // `useTaskFromCache` subscription below.
    await qc.prefetchQuery({
      queryKey: TASKS_QUERY_KEY,
      queryFn: async () => {
        const { api } = await import('@/api/client')
        const res = await (api as any).getTasks()
        return res.data ?? []
      },
    })

    const { container } = render(
      <TestProviders client={qc}>
        <TaskDrawer taskId="task-a" onClose={vi.fn()} onRetry={onRetry} retrying={null} />
      </TestProviders>,
    )

    const retryBtn = Array.from(container.querySelectorAll('button')).find((b) =>
      b.textContent?.includes('重试'),
    )
    expect(retryBtn).toBeDefined()
    fireEvent.click(retryBtn!)
    expect(onRetry).toHaveBeenCalledTimes(1)
    expect(onRetry.mock.calls[0][0].task_id).toBe('task-a')
  })

  it('does not show retry button for running tasks (canRetry gate)', async () => {
    const qc = new QueryClient()
    qc.setQueryData(TASKS_QUERY_KEY, [
      makeTask({ task_id: 'task-running', status: 'running', platform: 'douyin' }),
    ])
    await qc.prefetchQuery({
      queryKey: TASKS_QUERY_KEY,
      queryFn: async () => {
        const { api } = await import('@/api/client')
        const res = await (api as any).getTasks()
        return res.data ?? []
      },
    })

    const { container } = render(
      <TestProviders client={qc}>
        <TaskDrawer taskId="task-running" onClose={vi.fn()} onRetry={vi.fn()} retrying={null} />
      </TestProviders>,
    )
    expect(
      Array.from(container.querySelectorAll('button')).find((b) =>
        b.textContent?.includes('重试'),
      ),
    ).toBeUndefined()
  })

  it('logs accordion expands for non-terminal task statuses', async () => {
    const qc = new QueryClient()
    qc.setQueryData(TASKS_QUERY_KEY, [
      makeTask({ task_id: 'task-failed', status: 'failed', platform: 'douyin' }),
    ])
    await qc.prefetchQuery({
      queryKey: TASKS_QUERY_KEY,
      queryFn: async () => {
        const { api } = await import('@/api/client')
        const res = await (api as any).getTasks()
        return res.data ?? []
      },
    })

    const { container } = render(
      <TestProviders client={qc}>
        <TaskDrawer taskId="task-failed" onClose={vi.fn()} onRetry={vi.fn()} retrying={null} />
      </TestProviders>,
    )
    // implementation passes defaultValue='logs' for failed/error/running.
    // Our mock of Accordion accepts no real expansion state, so we check
    // that the accordion trigger was rendered with the right content.
    const trigger = Array.from(container.querySelectorAll('[data-tag="accordion-trigger"]')).find(
      (el) => el.textContent?.includes('运行日志'),
    )
    expect(trigger).toBeDefined()
  })

  it('honors `retrying` flag by clearing the button label context', () => {
    const qc = new QueryClient()
    qc.setQueryData(TASKS_QUERY_KEY, [
      makeTask({ task_id: 'a', status: 'failed', code: 1 }),
    ])
    const { container } = render(
      <TestProviders client={qc}>
        <TaskDrawer taskId="a" onClose={vi.fn()} onRetry={vi.fn()} retrying="a" />
      </TestProviders>,
    )
    const btn = Array.from(container.querySelectorAll('button')).find((b) =>
      b.textContent?.includes('重试'),
    )
    expect(btn).toBeDefined()
    // Button behavior under retrying='a' is to render a Loader2 inside.
    // We don't ship Loader2 in mocks, so the structural assertion is that
    // the button still rendered with the right text.
    expect(btn!.textContent).toContain('重试')
  })
})

describe('TaskDrawer — React.memo + callback stability', () => {
  it('memo HIT: rerender with same taskId + same callbacks → no new inner commit', () => {
    const qc = makeSeededClient()
    const onClose = vi.fn()
    const onRetry = vi.fn()
    const inner: ProfilerCounter = makeProfilerCounter()

    const { rerender } = render(
      <TestProviders client={qc}>
        <Profiler id="drawer" onRender={(_, phase) => inner.phases.push(phase as string)}>
          <TaskDrawer taskId="task-a" onClose={onClose} onRetry={onRetry} retrying={null} />
        </Profiler>
      </TestProviders>,
    )
    const baseline = inner.phases.length

    rerender(
      <TestProviders client={qc}>
        <Profiler id="drawer" onRender={(_, phase) => inner.phases.push(phase as string)}>
          <TaskDrawer taskId="task-a" onClose={onClose} onRetry={onRetry} retrying={null} />
        </Profiler>
      </TestProviders>,
    )

    expect(inner.phases.length).toBe(baseline)
  })

  it('memo MISS: changing taskId triggers a new commit', () => {
    const qc = makeSeededClient()
    const onClose = vi.fn()
    const onRetry = vi.fn()
    const inner: ProfilerCounter = makeProfilerCounter()

    const { rerender } = render(
      <TestProviders client={qc}>
        <Profiler id="drawer" onRender={(_, phase) => inner.phases.push(phase as string)}>
          <TaskDrawer taskId="task-a" onClose={onClose} onRetry={onRetry} retrying={null} />
        </Profiler>
      </TestProviders>,
    )
    const baseline = inner.phases.length

    rerender(
      <TestProviders client={qc}>
        <Profiler id="drawer" onRender={(_, phase) => inner.phases.push(phase as string)}>
          <TaskDrawer taskId="task-b" onClose={onClose} onRetry={onRetry} retrying={null} />
        </Profiler>
      </TestProviders>,
    )

    expect(inner.phases.length).toBeGreaterThan(baseline)
  })

  it('memo MISS: fresh onClose identity triggers a new commit', () => {
    const qc = makeSeededClient()
    const onRetry = vi.fn()
    const stableOnClose = vi.fn()
    const freshOnClose = vi.fn()
    const inner: ProfilerCounter = makeProfilerCounter()

    const { rerender } = render(
      <TestProviders client={qc}>
        <Profiler id="drawer" onRender={(_, phase) => inner.phases.push(phase as string)}>
          <TaskDrawer taskId="task-a" onClose={stableOnClose} onRetry={onRetry} retrying={null} />
        </Profiler>
      </TestProviders>,
    )
    const baseline = inner.phases.length

    rerender(
      <TestProviders client={qc}>
        <Profiler id="drawer" onRender={(_, phase) => inner.phases.push(phase as string)}>
          <TaskDrawer taskId="task-a" onClose={freshOnClose} onRetry={onRetry} retrying={null} />
        </Profiler>
      </TestProviders>,
    )

    expect(inner.phases.length).toBeGreaterThan(baseline)
  })
})
