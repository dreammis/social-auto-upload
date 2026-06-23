import { useEffect, useRef, type ReactNode } from 'react'
import { TourProvider, useTour, type StepType } from '@reactour/tour'
import { useToast } from '@/components/ui/toast'

const STORAGE_KEY = 'sau-onboarding-done'

// ── Steps (emojis embedded in content strings) ────────────────────────
const steps: StepType[] = [
  {
    selector: 'body',
    content: '1️⃣ 欢迎使用 SAU Shell 🎉\n\n支持抖音、快手、小红书、B 站、视频号等多平台自动发布。\n\n接下来 5 步完成首次配置。',
  },
  {
    selector: '[data-tour="new-group"]',
    content: '2️⃣ 创建第一个分组\n\n点击「新建分组」，输入名称即可。\n\n建议按用途命名，如「个人号」「工作室号」。',
  },
  {
    selector: '[data-tour="add-auth"]',
    content: '3️⃣ 添加平台授权 🔑\n\n分组卡片内点击 "+"，选择平台后扫码登录。\n\n登录后自动保存 Cookie，后续无需重复登录。',
  },
  {
    selector: '[data-tour="check-all"]',
    content: '4️⃣ 检测账号状态 ✅\n\n使用「一键检测」查看 Cookie 是否有效。\n\n绿色 = 正常，红色 = 已失效需重新登录。',
  },
  {
    selector: '[data-tour="nav-publish"]',
    content: '5️⃣ 开始发布 🚀\n\n点击左侧「发布中心」，选择平台和账号，上传视频或图文即可发布。\n\n支持定时发布和 AI 内容生成。',
  },
]

// ── Dark-mode aware styles ─────────────────────────────────────────────
const tourStyles = {
  popover: (base: Record<string, unknown>) => ({
    ...base,
    background: 'var(--popover, hsl(0 0% 100%))',
    color: 'var(--popover-foreground, hsl(0 0% 3.9%))',
    borderRadius: 14,
    padding: 20,
    fontSize: 13,
    lineHeight: 1.6,
    maxWidth: 340,
    boxShadow: '0 16px 48px rgba(0,0,0,0.25)',
    border: '1px solid var(--border, hsl(0 0% 89.8%))',
    whiteSpace: 'pre-line',
  }),
  maskArea: (base: Record<string, unknown>) => ({
    ...base,
    rx: 12,
  }),
  badge: (base: Record<string, unknown>) => ({
    ...base,
    background: 'var(--primary, hsl(262 83% 58%))',
    color: 'var(--primary-foreground, hsl(0 0% 100%))',
  }),
  controls: (base: Record<string, unknown>) => ({
    ...base,
    marginTop: 12,
    fontSize: 12,
    gap: 6,
    '& button': {
      fontSize: 12,
      padding: '4px 10px',
      borderRadius: 6,
    },
  }),
  close: (base: Record<string, unknown>) => ({
    ...base,
    color: 'var(--muted-foreground, hsl(0 0% 45%))',
    top: 12,
    right: 14,
  }),
  dot: (base: Record<string, unknown>) => ({
    ...base,
    background: 'var(--muted, hsl(0 0% 96%))',
    width: 8,
    height: 8,
    borderRadius: 4,
    transition: 'all 0.3s ease',
  }),
  arrow: (base: Record<string, unknown>) => ({
    ...base,
    color: 'var(--primary, hsl(262 83% 58%))',
  }),
}

// ── persist on close + notify via custom event ────────────────────────
const TOUR_DONE_EVENT = 'sau-tour-done'
const TOUR_RESET_EVENT = 'sau-tour-reset'
const beforeClose = () => {
  localStorage.setItem(STORAGE_KEY, '1')
  window.dispatchEvent(new Event(TOUR_DONE_EVENT))
}

/**
 * Public reset hook — call from anywhere (settings, sidebar footer, etc.)
 * to clear the localStorage flag and immediately reopen the tour.
 */
export function resetOnboardingTour() {
  localStorage.removeItem(STORAGE_KEY)
  window.dispatchEvent(new Event(TOUR_RESET_EVENT))
}

// ── Inner hook component ────────────────────────────────────────────────
function AutoStartTour() {
  const { setIsOpen, setCurrentStep } = useTour()
  const { addToast } = useToast()
  const startedRef = useRef(false)
  const toastRef = useRef(addToast)
  toastRef.current = addToast

  // Auto-start on mount (once)
  useEffect(() => {
    if (localStorage.getItem(STORAGE_KEY) || startedRef.current) return
    startedRef.current = true
    const id = setTimeout(() => setIsOpen(true), 500)
    return () => clearTimeout(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Listen for tour-done event
  useEffect(() => {
    const handler = () => toastRef.current('引导完成，开始使用吧！', 'success')
    window.addEventListener(TOUR_DONE_EVENT, handler)
    return () => window.removeEventListener(TOUR_DONE_EVENT, handler)
  }, [])

  // Listen for manual reset events — reopen the tour from step 0
  useEffect(() => {
    const handler = () => {
      setCurrentStep(0)
      setIsOpen(true)
    }
    window.addEventListener(TOUR_RESET_EVENT, handler)
    return () => window.removeEventListener(TOUR_RESET_EVENT, handler)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return null
}

// ── Public wrapper ──────────────────────────────────────────────────────
export function OnboardingTour({ children }: { children: ReactNode }) {
  return (
    <TourProvider
      steps={steps}
      beforeClose={beforeClose}
      styles={tourStyles}
      showNavigation
      showBadge
      showDots
      showCloseButton
    >
      <AutoStartTour />
      {children}
    </TourProvider>
  )
}
