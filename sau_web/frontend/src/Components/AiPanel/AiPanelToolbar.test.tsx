import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

// ── controlled mocks ──────────────────────────────────────────────────────

let aiState = {
  selectedModel: 'google/gemma-4-26b-a4b-it:free',
  modelTags: ['text'],
}

let aiConfigData: { key_count: number; configured: boolean } = {
  key_count: 3,
  configured: true,
}

vi.mock('@/stores/useAiStore', () => ({
  useAiStore: (selector: (s: typeof aiState) => unknown) => selector(aiState),
}))

vi.mock('@/hooks/useAiConfig', () => ({
  useAiConfig: () => ({ data: aiConfigData, isLoading: false }),
  useAiKeys: () => ({ data: [], isLoading: false }),
  useSetAiConfig: () => ({ mutateAsync: vi.fn() }),
  useDeleteAiConfig: () => ({ mutateAsync: vi.fn() }),
}))

vi.mock('@/lib/tip', () => ({
  Tip: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

vi.mock('@/components/ui/button', () => ({
  Button: ({ children, className, onClick, disabled, ...rest }: any) => (
    <button className={className} onClick={onClick} disabled={disabled} {...rest}>
      {children}
    </button>
  ),
}))

vi.mock('@/components/ui/badge', () => ({
  Badge: ({ children, className }: any) => <span className={className}>{children}</span>,
}))

vi.mock('lucide-react', () => ({
  Sparkles: () => <span data-icon="sparkles" />,
  ChevronUp: () => <span data-icon="chevron-up" />,
  Key: () => <span data-icon="key" />,
  Zap: () => <span data-icon="zap" />,
}))

// ── imports (post-mock) ────────────────────────────────────────────────────

import { AiPanelToolbar } from './AiPanelToolbar'

describe('AiPanelToolbar — rendering', () => {
  it('shows the AI assistant label', () => {
    render(<AiPanelToolbar isExpanded={false} onToggle={vi.fn()} />)
    expect(screen.getByText('AI 助手')).toBeDefined()
  })

  it('shortens the model name to last segment', () => {
    aiState.selectedModel = 'openai/gpt-4o-mini'
    render(<AiPanelToolbar isExpanded={false} onToggle={vi.fn()} />)
    expect(screen.getByText('gpt-4o-mini')).toBeDefined()
  })

  it('falls back to full model name when no slash', () => {
    aiState.selectedModel = 'simplename'
    render(<AiPanelToolbar isExpanded={false} onToggle={vi.fn()} />)
    expect(screen.getByText('simplename')).toBeDefined()
  })
})

describe('AiPanelToolbar — key count', () => {
  beforeEach(() => {
    aiConfigData = { key_count: 3, configured: true }
  })

  it('shows key count when configured', () => {
    render(<AiPanelToolbar isExpanded={false} onToggle={vi.fn()} />)
    expect(screen.getByText('3 Keys')).toBeDefined()
  })

  it('shows "未配置" when key_count is 0', () => {
    aiConfigData = { key_count: 0, configured: false }
    render(<AiPanelToolbar isExpanded={false} onToggle={vi.fn()} />)
    expect(screen.getByText('未配置')).toBeDefined()
  })
})

describe('AiPanelToolbar — toggle button', () => {
  it('shows "展开" label when collapsed', () => {
    render(<AiPanelToolbar isExpanded={false} onToggle={vi.fn()} />)
    expect(screen.getByText('展开')).toBeDefined()
  })

  it('shows "收起" label when expanded', () => {
    render(<AiPanelToolbar isExpanded={true} onToggle={vi.fn()} />)
    expect(screen.getByText('收起')).toBeDefined()
  })

  it('fires onToggle when clicked', () => {
    const onToggle = vi.fn()
    render(<AiPanelToolbar isExpanded={false} onToggle={onToggle} />)
    fireEvent.click(screen.getByText('展开'))
    expect(onToggle).toHaveBeenCalledTimes(1)
  })

  it('fires onToggle again when already expanded', () => {
    const onToggle = vi.fn()
    render(<AiPanelToolbar isExpanded={true} onToggle={onToggle} />)
    fireEvent.click(screen.getByText('收起'))
    expect(onToggle).toHaveBeenCalledTimes(1)
  })
})

describe('AiPanelToolbar — quick generate button', () => {
  it('does NOT render quick-generate when onQuickGenerate not provided', () => {
    render(<AiPanelToolbar isExpanded={false} onToggle={vi.fn()} />)
    expect(screen.queryByText('一键全流程')).toBeNull()
  })

  it('renders quick-generate button when onQuickGenerate provided', () => {
    render(
      <AiPanelToolbar
        isExpanded={false}
        onToggle={vi.fn()}
        onQuickGenerate={vi.fn()}
      />,
    )
    expect(screen.getByText('一键全流程')).toBeDefined()
  })

  it('quick-generate fires onQuickGenerate on click', () => {
    const onQuickGenerate = vi.fn()
    render(
      <AiPanelToolbar
        isExpanded={false}
        onToggle={vi.fn()}
        onQuickGenerate={onQuickGenerate}
      />,
    )
    fireEvent.click(screen.getByText('一键全流程'))
    expect(onQuickGenerate).toHaveBeenCalledTimes(1)
  })

  it('quick-generate is disabled when isGenerating=true', () => {
    render(
      <AiPanelToolbar
        isExpanded={false}
        onToggle={vi.fn()}
        onQuickGenerate={vi.fn()}
        isGenerating={true}
      />,
    )
    const btn = screen.getByText('一键全流程').closest('button') as HTMLButtonElement
    expect(btn.disabled).toBe(true)
  })

  it('quick-generate is NOT disabled when isGenerating=false', () => {
    render(
      <AiPanelToolbar
        isExpanded={false}
        onToggle={vi.fn()}
        onQuickGenerate={vi.fn()}
        isGenerating={false}
      />,
    )
    const btn = screen.getByText('一键全流程').closest('button') as HTMLButtonElement
    expect(btn.disabled).toBe(false)
  })
})

describe('AiPanelToolbar — mobile viewport (375px)', () => {
  const origWidth = window.innerWidth
  const origHeight = window.innerHeight

  afterEach(() => {
    window.innerWidth = origWidth
    window.innerHeight = origHeight
  })

  beforeEach(() => {
    window.innerWidth = 375
    window.innerHeight = 667
  })

  it('"AI 助手" label has hidden sm:inline class (hidden on mobile)', () => {
    render(<AiPanelToolbar isExpanded={false} onToggle={vi.fn()} />)
    const label = screen.getByText('AI 助手')
    expect(label.className).toContain('hidden')
    expect(label.className).toContain('sm:inline')
  })

  it('"一键全流程" text has hidden sm:inline class when quick-generate shown', () => {
    render(
      <AiPanelToolbar isExpanded={false} onToggle={vi.fn()} onQuickGenerate={vi.fn()} />,
    )
    const label = screen.getByText('一键全流程')
    expect(label.className).toContain('hidden')
    expect(label.className).toContain('sm:inline')
  })

  it('"展开" text has hidden sm:inline class (hidden on mobile)', () => {
    render(<AiPanelToolbar isExpanded={false} onToggle={vi.fn()} />)
    const label = screen.getByText('展开')
    expect(label.className).toContain('hidden')
    expect(label.className).toContain('sm:inline')
  })

  it('"收起" text has hidden sm:inline class when expanded on mobile', () => {
    render(<AiPanelToolbar isExpanded={true} onToggle={vi.fn()} />)
    const label = screen.getByText('收起')
    expect(label.className).toContain('hidden')
    expect(label.className).toContain('sm:inline')
  })

  it('model name section has hidden md:flex class (hidden below 768px)', () => {
    aiState.selectedModel = 'openai/gpt-4o-mini'
    render(<AiPanelToolbar isExpanded={false} onToggle={vi.fn()} />)
    const modelSpan = screen.getByText('gpt-4o-mini')
    // The parent div uses hidden md:flex — target by the md breakpoint token
    const parentDiv = modelSpan.closest('[class*="md:flex"]') as HTMLElement
    expect(parentDiv).toBeDefined()
    expect(parentDiv.className).toContain('hidden')
  })

  it('sparkles icon is always present (no text dependency)', () => {
    render(<AiPanelToolbar isExpanded={false} onToggle={vi.fn()} />)
    expect(document.querySelector('[data-icon="sparkles"]')).toBeDefined()
  })

  it('chevron-up icon is always present', () => {
    render(<AiPanelToolbar isExpanded={false} onToggle={vi.fn()} />)
    expect(document.querySelector('[data-icon="chevron-up"]')).toBeDefined()
  })

  it('key icon is always present', () => {
    render(<AiPanelToolbar isExpanded={false} onToggle={vi.fn()} />)
    expect(document.querySelector('[data-icon="key"]')).toBeDefined()
  })

  it('toolbar responds to toggle click on mobile', () => {
    const onToggle = vi.fn()
    render(<AiPanelToolbar isExpanded={false} onToggle={onToggle} />)
    // The button containing "展开" is clickable even at 375px
    fireEvent.click(screen.getByText('展开'))
    expect(onToggle).toHaveBeenCalledTimes(1)
  })
})
