import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'

// ── controlled mocks ──────────────────────────────────────────────────────

const toolbarSpy = vi.hoisted(() => vi.fn())

vi.mock('./AiPanelToolbar', () => ({
  AiPanelToolbar: (props: any) => {
    toolbarSpy(props)
    return (
      <div data-testid="ai-panel-toolbar">
        <button data-testid="toolbar-toggle" onClick={props.onToggle}>
          toggle
        </button>
        {props.onQuickGenerate && (
          <button data-testid="toolbar-quick-generate" onClick={props.onQuickGenerate}>
            quick-generate
          </button>
        )}
      </div>
    )
  },
}))

vi.mock('motion/react', () => {
  const motionCache = new Map<string, (props: any) => any>()
  const motion: any = new Proxy(
    {},
    {
      get: (_t, tag: string) => {
        if (!motionCache.has(tag)) {
          motionCache.set(tag, (props: any) => {
            const { children, animate, initial, transition, exit, ...rest } = props ?? {}
            return (
              <div
                data-motion-tag={tag}
                data-animate-height={animate?.height}
                data-animate-opacity={animate?.opacity}
                data-exit-y={exit?.y}
                {...rest}
              >
                {children}
              </div>
            )
          })
        }
        return motionCache.get(tag)
      },
    },
  )
  return { motion, AnimatePresence: ({ children }: any) => <>{children}</> }
})

vi.mock('lucide-react', () => ({
  X: ({ className }: any) => <span data-icon="x" className={className} />,
}))

// ── imports (post-mock) ────────────────────────────────────────────────────

import { AiPanel } from './AiPanel'

describe('AiPanel — default state', () => {
  it('renders children', () => {
    render(
      <AiPanel>
        <div data-testid="child">content</div>
      </AiPanel>,
    )
    expect(screen.getByTestId('child')).toBeDefined()
    expect(screen.getByText('content')).toBeDefined()
  })

  it('starts collapsed by default (isExpanded=false on toolbar)', () => {
    toolbarSpy.mockClear()
    render(
      <AiPanel>
        <div>child</div>
      </AiPanel>,
    )
    expect(toolbarSpy).toHaveBeenCalled()
    expect(toolbarSpy.mock.calls[0][0].isExpanded).toBe(false)
  })

  it('starts expanded when defaultExpanded=true', () => {
    toolbarSpy.mockClear()
    render(
      <AiPanel defaultExpanded={true}>
        <div>child</div>
      </AiPanel>,
    )
    expect(toolbarSpy).toHaveBeenCalled()
    expect(toolbarSpy.mock.calls[0][0].isExpanded).toBe(true)
  })
})

describe('AiPanel — toggle', () => {
  beforeEach(() => {
    toolbarSpy.mockClear()
  })

  it('toggles from collapsed to expanded when toolbar onToggle fires', () => {
    render(
      <AiPanel>
        <div>child</div>
      </AiPanel>,
    )

    // First render — collapsed
    expect(toolbarSpy.mock.calls[0][0].isExpanded).toBe(false)

    // Click toggle
    fireEvent.click(screen.getByTestId('toolbar-toggle'))

    // After re-render — expanded
    const lastCall = toolbarSpy.mock.calls[toolbarSpy.mock.calls.length - 1][0]
    expect(lastCall.isExpanded).toBe(true)
  })

  it('toggles from expanded back to collapsed', () => {
    render(
      <AiPanel defaultExpanded={true}>
        <div>child</div>
      </AiPanel>,
    )

    const firstCall = toolbarSpy.mock.calls[0][0]
    expect(firstCall.isExpanded).toBe(true)

    fireEvent.click(screen.getByTestId('toolbar-toggle'))

    const lastCall = toolbarSpy.mock.calls[toolbarSpy.mock.calls.length - 1][0]
    expect(lastCall.isExpanded).toBe(false)
  })
})

describe('AiPanel — children always mounted', () => {
  it('children remain in DOM when collapsed', () => {
    // This is the critical contract: AnimatePresence is NOT used,
    // children stay mounted so internal state (AiSidebar) is preserved.
    const { rerender } = render(
      <AiPanel defaultExpanded={true}>
        <div data-testid="ai-content">AI content here</div>
      </AiPanel>,
    )

    expect(screen.getByTestId('ai-content')).toBeDefined()

    // Collapse via toggle
    fireEvent.click(screen.getByTestId('toolbar-toggle'))
    rerender(
      <AiPanel defaultExpanded={true}>
        <div data-testid="ai-content">AI content here</div>
      </AiPanel>,
    )

    // Children must still be in the DOM
    expect(screen.getByTestId('ai-content')).toBeDefined()
    expect(screen.getByText('AI content here')).toBeDefined()
  })
})

describe('AiPanel — drag handle', () => {
  it('renders a drag handle in the expandable area', () => {
    render(
      <AiPanel defaultExpanded={true}>
        <div>child</div>
      </AiPanel>,
    )

    // The drag handle is the inner div with rounded-full styling
    // inside the cursor-ns-resize container
    const handles = document.querySelectorAll('[class*="cursor-ns-resize"]')
    expect(handles.length).toBeGreaterThanOrEqual(1)
  })

  it('drag handle fires mousedown for resize', () => {
    render(
      <AiPanel defaultExpanded={true}>
        <div>child</div>
      </AiPanel>,
    )

    const handle = document.querySelector('[class*="cursor-ns-resize"]') as HTMLElement
    expect(handle).toBeDefined()

    // Should not throw — drag handle is wired
    expect(() => fireEvent.mouseDown(handle)).not.toThrow()
  })
})

describe('AiPanel — props passthrough', () => {
  it('passes onQuickGenerate to toolbar', () => {
    toolbarSpy.mockClear()
    const gen = vi.fn()
    render(
      <AiPanel onQuickGenerate={gen}>
        <div>child</div>
      </AiPanel>,
    )
    expect(toolbarSpy).toHaveBeenCalled()
    // After mockClear, the first call is from this render
    const firstCall = toolbarSpy.mock.calls[0][0]
    expect(firstCall.onQuickGenerate).toBe(gen)
  })

  it('passes isGenerating to toolbar', () => {
    toolbarSpy.mockClear()
    render(
      <AiPanel isGenerating={true} onQuickGenerate={vi.fn()}>
        <div>child</div>
      </AiPanel>,
    )
    expect(toolbarSpy).toHaveBeenCalled()
    const firstCall = toolbarSpy.mock.calls[0][0]
    expect(firstCall.isGenerating).toBe(true)
  })
})

describe('AiPanel — expanded content height', () => {
  it('motion.div has height set to panelHeight when expanded', () => {
    render(
      <AiPanel defaultExpanded={true}>
        <div>child</div>
      </AiPanel>,
    )

    const motionDiv = document.querySelector('[data-motion-tag="div"]') as HTMLElement
    expect(motionDiv).toBeDefined()
    // When expanded, animate.height should be truthy (the panelHeight)
    const animateHeight = motionDiv.getAttribute('data-animate-height')
    expect(Number(animateHeight)).toBeGreaterThan(0)
  })

  it('motion.div has height=0 when collapsed', () => {
    render(
      <AiPanel defaultExpanded={false}>
        <div>child</div>
      </AiPanel>,
    )

    const motionDiv = document.querySelector('[data-motion-tag="div"]') as HTMLElement
    expect(motionDiv).toBeDefined()
    // When collapsed, animate.height should be 0
    expect(motionDiv.getAttribute('data-animate-height')).toBe('0')
  })

  it('clamps panelHeight down when window shrinks below current height', () => {
    const origHeight = window.innerHeight
    window.innerHeight = 900

    render(
      <AiPanel defaultExpanded={true}>
        <div>child</div>
      </AiPanel>,
    )

    expect(
      Number(
        (document.querySelector('[data-motion-tag="div"]') as HTMLElement).getAttribute('data-animate-height'),
      ),
    ).toBe(420)

    // Shrink so maxHeight (72% of 400 = 288) < panelHeight (420)
    window.innerHeight = 400
    act(() => {
      window.dispatchEvent(new Event('resize'))
    })

    // Re-query after re-render — panelHeight clamps to 288
    const clampedHeight = Number(
      (document.querySelector('[data-motion-tag="div"]') as HTMLElement).getAttribute('data-animate-height'),
    )
    expect(clampedHeight).toBe(288)

    window.innerHeight = origHeight
  })

  it('does NOT clamp panelHeight when window is still large enough', () => {
    const origHeight = window.innerHeight
    window.innerHeight = 2000

    render(
      <AiPanel defaultExpanded={true}>
        <div>child</div>
      </AiPanel>,
    )

    expect(
      Number(
        (document.querySelector('[data-motion-tag="div"]') as HTMLElement).getAttribute('data-animate-height'),
      ),
    ).toBe(420)

    // Shrink to still-large window (72% of 1000 = 720 > 420)
    window.innerHeight = 1000
    act(() => {
      window.dispatchEvent(new Event('resize'))
    })

    expect(
      Number(
        (document.querySelector('[data-motion-tag="div"]') as HTMLElement).getAttribute('data-animate-height'),
      ),
    ).toBe(420)

    window.innerHeight = origHeight
  })

  it('resize listener is cleaned up on unmount', () => {
    const addSpy = vi.spyOn(window, 'addEventListener')
    const removeSpy = vi.spyOn(window, 'removeEventListener')

    const { unmount } = render(
      <AiPanel>
        <div>child</div>
      </AiPanel>,
    )

    expect(addSpy).toHaveBeenCalledWith('resize', expect.any(Function))

    unmount()

    expect(removeSpy).toHaveBeenCalledWith('resize', expect.any(Function))

    addSpy.mockRestore()
    removeSpy.mockRestore()
  })
})

describe('AiPanel — mobile viewport', () => {
  const origWidth = window.innerWidth
  const origHeight = window.innerHeight

  afterEach(() => {
    window.innerWidth = origWidth
    window.innerHeight = origHeight
    toolbarSpy.mockClear()
  })

  it('renders toolbar at 375px width (iPhone)', () => {
    window.innerWidth = 375
    window.innerHeight = 667

    render(
      <AiPanel>
        <div>child</div>
      </AiPanel>,
    )

    expect(toolbarSpy).toHaveBeenCalled()
    // Toolbar must render regardless of viewport width
    expect(screen.getByTestId('ai-panel-toolbar')).toBeDefined()
  })

  it('toolbar toggle button is always accessible on mobile', () => {
    window.innerWidth = 375

    render(
      <AiPanel>
        <div>child</div>
      </AiPanel>,
    )

    const toggleBtn = screen.getByTestId('toolbar-toggle')
    expect(toggleBtn).toBeDefined()

    // Expanding on mobile should work
    fireEvent.click(toggleBtn)
    const lastCall = toolbarSpy.mock.calls[toolbarSpy.mock.calls.length - 1][0]
    expect(lastCall.isExpanded).toBe(true)
  })

  it('renders children at mobile width when expanded', () => {
    window.innerWidth = 375

    render(
      <AiPanel defaultExpanded={true}>
        <div data-testid="mobile-child">mobile content</div>
      </AiPanel>,
    )

    expect(screen.getByTestId('mobile-child')).toBeDefined()
    expect(screen.getByText('mobile content')).toBeDefined()
  })

  it('fixed bottom positioning is preserved on mobile', () => {
    window.innerWidth = 375

    const { container } = render(
      <AiPanel>
        <div>child</div>
      </AiPanel>,
    )

    // The outer div must have fixed + bottom-0 classes
    const root = container.firstElementChild as HTMLElement
    expect(root.className).toContain('fixed')
    expect(root.className).toContain('bottom-0')
  })

  it('renders desktop bottom drawer when NOT expanded on mobile', () => {
    window.innerWidth = 375
    render(
      <AiPanel defaultExpanded={false}>
        <div>child</div>
      </AiPanel>,
    )
    // Collapsed → no Modal, no bottom drawer content
    expect(screen.queryByTestId('modal-backdrop')).toBeNull()
    expect(screen.queryByTestId('modal-panel')).toBeNull()
  })

  it('renders Modal overlay when expanded on mobile', () => {
    window.innerWidth = 375
    render(
      <AiPanel defaultExpanded={true}>
        <div data-testid="modal-child">modal content</div>
      </AiPanel>,
    )
    expect(screen.getByTestId('modal-backdrop')).toBeDefined()
    expect(screen.getByTestId('modal-panel')).toBeDefined()
    expect(screen.getByTestId('modal-child')).toBeDefined()
  })

  it('Modal backdrop click triggers close', () => {
    window.innerWidth = 375
    toolbarSpy.mockClear()
    render(
      <AiPanel defaultExpanded={true}>
        <div>child</div>
      </AiPanel>,
    )
    // Toggle was called once on mount (defaultExpanded=true)
    // Click backdrop → should call toggle to collapse
    fireEvent.click(screen.getByTestId('modal-backdrop'))
    // After backdrop click, isExpanded should be false
    const lastCall = toolbarSpy.mock.calls[toolbarSpy.mock.calls.length - 1][0]
    expect(lastCall.isExpanded).toBe(false)
  })

  it('Modal close button triggers collapse', () => {
    window.innerWidth = 375
    toolbarSpy.mockClear()
    render(
      <AiPanel defaultExpanded={true}>
        <div>child</div>
      </AiPanel>,
    )
    fireEvent.click(screen.getByTestId('modal-close'))
    const lastCall = toolbarSpy.mock.calls[toolbarSpy.mock.calls.length - 1][0]
    expect(lastCall.isExpanded).toBe(false)
  })

  it('Modal shows "AI 内容生成" header', () => {
    window.innerWidth = 375
    render(
      <AiPanel defaultExpanded={true}>
        <div>child</div>
      </AiPanel>,
    )
    expect(screen.getByText('AI 内容生成')).toBeDefined()
  })

  it('Modal has content area with children', () => {
    window.innerWidth = 375
    render(
      <AiPanel defaultExpanded={true}>
        <div data-testid="nested-child">nested</div>
      </AiPanel>,
    )
    expect(screen.getByTestId('modal-content')).toBeDefined()
    expect(screen.getByTestId('nested-child')).toBeDefined()
    expect(screen.getByText('nested')).toBeDefined()
  })

  it('Modal has exit animation y value set', () => {
    window.innerWidth = 375
    render(
      <AiPanel defaultExpanded={true}>
        <div>child</div>
      </AiPanel>,
    )
    const panel = screen.getByTestId('modal-panel')
    // The mock captures exit.y as data-exit-y
    expect(panel.getAttribute('data-exit-y')).toBe('100%')
  })

  it('Desktop bottom drawer does NOT render on mobile', () => {
    window.innerWidth = 375
    render(
      <AiPanel defaultExpanded={true}>
        <div>child</div>
      </AiPanel>,
    )
    // The desktop bottom drawer has a cursor-ns-resize drag handle
    const handles = document.querySelectorAll('[class*="cursor-ns-resize"]')
    expect(handles.length).toBe(0)
  })

  it('Modal does NOT render at desktop width even when expanded', () => {
    window.innerWidth = 1024
    render(
      <AiPanel defaultExpanded={true}>
        <div>child</div>
      </AiPanel>,
    )
    expect(screen.queryByTestId('modal-backdrop')).toBeNull()
    expect(screen.queryByTestId('modal-panel')).toBeNull()
    // Desktop bottom drawer should render instead
    const handles = document.querySelectorAll('[class*="cursor-ns-resize"]')
    expect(handles.length).toBeGreaterThanOrEqual(1)
  })

  it('toggles between Modal and collapsed on mobile via toolbar', () => {
    window.innerWidth = 375
    render(
      <AiPanel defaultExpanded={false}>
        <div>child</div>
      </AiPanel>,
    )
    // Start collapsed — no Modal
    expect(screen.queryByTestId('modal-panel')).toBeNull()

    // Click toolbar toggle to expand
    fireEvent.click(screen.getByTestId('toolbar-toggle'))

    // Modal should appear
    expect(screen.getByTestId('modal-panel')).toBeDefined()
    expect(screen.getByTestId('modal-backdrop')).toBeDefined()

    // Click close button
    fireEvent.click(screen.getByTestId('modal-close'))

    // Modal should disappear
    expect(screen.queryByTestId('modal-panel')).toBeNull()
  })
})
