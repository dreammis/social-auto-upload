import { useEffect, useRef, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Progress } from '@/components/ui/progress'
import { useToast } from '@/components/ui/toast'
import {
  useAuthorizeAccountGroup,
  useConfirmAuthorizeAccountGroup,
} from '@/hooks/useAccountGroups'
import { api, QR_LOGIN_PLATFORMS } from '@/api/client'
import { cn } from '@/lib/utils'
import {
  QrCode,
  Loader2,
  CheckCircle2,
  Circle,
  Globe,
  ScanLine,
  LogIn,
  ShieldCheck,
  XCircle,
  AlertCircle,
  Terminal,
  Shield,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { CliCommandBlock } from '@/components/CliCommand'
import { toneBgClass, toneBorderClass, toneTextClass } from '@/lib/tone'

// ── Step definitions ─────────────────────────────────────────────────────

interface StepDef {
  key: string
  label: string
  description: string
  icon: typeof Globe
  progress: number // 0–100
}

const STEPS: StepDef[] = [
  { key: 'starting', label: '启动浏览器', description: '正在启动自动化浏览器…', icon: Globe, progress: 15 },
  { key: 'fetching_qr', label: '获取二维码', description: '正在从平台获取登录二维码…', icon: QrCode, progress: 30 },
  { key: 'scan_qr', label: '扫码登录', description: '请使用手机 App 扫描二维码完成登录', icon: ScanLine, progress: 55 },
  { key: 'verifying', label: '验证登录', description: '扫码成功，正在验证登录状态…', icon: LogIn, progress: 75 },
  { key: 'saving', label: '保存授权', description: '正在保存授权信息到本地…', icon: ShieldCheck, progress: 90 },
  { key: 'complete', label: '授权完成', description: '平台授权已成功添加！', icon: CheckCircle2, progress: 100 },
]

// ── Props ─────────────────────────────────────────────────────────────────

interface LoginProgressModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  groupId: number
  platform: string
  groupName: string
  platformLabel: string
  onComplete: () => void
}

// ── Component ─────────────────────────────────────────────────────────────

export function LoginProgressModal({
  open,
  onOpenChange,
  groupId,
  platform,
  groupName,
  platformLabel,
  onComplete,
}: LoginProgressModalProps) {
  const { addToast } = useToast()
  const authorizeGroup = useAuthorizeAccountGroup()
  const confirmAuthorize = useConfirmAuthorizeAccountGroup()

  const isQrPlatform = QR_LOGIN_PLATFORMS.includes(platform)

  const [currentStepIndex, setCurrentStepIndex] = useState(0)
  const [qrCodeUrl, setQrCodeUrl] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isCompleting, setIsCompleting] = useState(false)
  const [isVerifying, setIsVerifying] = useState(false)

  const eventSourceRef = useRef<EventSource | null>(null)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const cancelledRef = useRef(false)
  const stepRef = useRef(0)
  const completingRef = useRef(false)
  const sseStartedAtRef = useRef<number | null>(null)

  // Diagnostic tag for SSE-related logs/messages — gives context (platform + group)
  // so support/dev issues can be traced quickly in the browser console.
  const ctx = `[${platformLabel}/${platform} · ${groupName}]`

  // Diagnose EventSource errors by readyState, so we can give a precise message
  // (e.g. "never connected" vs "server killed the connection" vs "proxy timed out").
  function describeSseError(es: EventSource): { userMsg: string; log: string } {
    const secondsSinceOpen = sseStartedAtRef.current
      ? Math.max(0, Math.round((Date.now() - sseStartedAtRef.current) / 1000))
      : null
    const elapsed = secondsSinceOpen !== null ? `${secondsSinceOpen}s` : '?'

    // Indexes from EventSource spec: 0=CONNECTING, 1=OPEN, 2=CLOSED
    switch (es.readyState) {
      case EventSource.CONNECTING:
        return {
          userMsg: `无法连接到登录服务 ${ctx}（已尝试 ${elapsed}）— 请确认后端已启动`,
          log: `[SSE] initial connection failed for ${ctx} after ${elapsed} (readyState=CONNECTING, url=${es.url})`,
        }
      case EventSource.CLOSED:
        return {
          userMsg: `登录服务连接已中断 ${ctx}（连接持续 ${elapsed}）— 可能是代理/防火墙超时或后端崩溃`,
          log: `[SSE] connection dropped for ${ctx} after ${elapsed} (readyState=CLOSED, url=${es.url})`,
        }
      default:
        return {
          userMsg: `登录服务通信异常 ${ctx}（readyState=${es.readyState}）`,
          log: `[SSE] unexpected error for ${ctx} (readyState=${es.readyState}, url=${es.url})`,
        }
    }
  }

  const goToStep = useCallback((index: number) => {
    stepRef.current = index
    setCurrentStepIndex(index)
  }, [])

  const cleanup = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
      timeoutRef.current = null
    }
  }, [])

  // ── Start flow when modal opens ──────────────────────────────────────

  useEffect(() => {
    if (!open) {
      cancelledRef.current = true
      cleanup()
      setCurrentStepIndex(0)
      setQrCodeUrl(null)
      setErrorMessage(null)
      setIsCompleting(false)
      completingRef.current = false
      return
    }

    cancelledRef.current = false
    setCurrentStepIndex(0)
    setQrCodeUrl(null)
    setErrorMessage(null)
    setIsCompleting(false)
    setIsVerifying(false)
    completingRef.current = false
    stepRef.current = 0

    // Local cancellation flag for THIS effect invocation. Required because in <StrictMode>
    // dev mode, useEffect does setup → cleanup → setup. Without a local flag, the first
    // setup's async chain could resume after cleanup & open an EventSource whose `onerror`
    // later reads `eventSourceRef.current` pointing to the SECOND setup's EventSource
    // (which may still be in CONNECTING), producing a spurious "无法连接" toast.
    //
    // Pairs with the "stale ES" guard (`eventSource !== eventSourceRef.current`) used in
    // every event handler and the safety timeout — see those sites for details.
    let isEffectCancelled = false

    // Non-QR platforms: show manual CLI instructions (no SSE flow)
    if (!isQrPlatform) {
      return () => {
        isEffectCancelled = true
        cancelledRef.current = true
        cleanup()
      }
    }
    authorizeGroup.mutateAsync({ groupId, platform, headless: true })
      .then((result) => {
        if (isEffectCancelled || cancelledRef.current) return

        if (result.success && result.data) {
          goToStep(1) // → fetching QR

          const sseUrl = `${api.getBaseUrl()}/api/accounts/login/sse?platform=${platform}&account=${encodeURIComponent(result.data.group_name)}&headless=true`
          const eventSource = new EventSource(sseUrl)
          // Stale-ES guard: if a previous setup's .then() (or a prior mutation chain)
          // already assigned a different EventSource to the ref, the live one is that
          // ref; ours is stale — close it so we don't leak an EventSource with no
          // active handlers. Identifies the "stale" branch used by event handlers below.
          if (eventSourceRef.current && eventSourceRef.current !== eventSource) {
            console.info(`[SSE-stale] ${ctx} discarding stale EventSource (StrictMode/duplicate setup)`)
            eventSource.close()
            return
          }
          eventSourceRef.current = eventSource
          sseStartedAtRef.current = Date.now()
          console.info(`[SSE] opening ${sseUrl}`)

          eventSource.addEventListener('qrcode', (e) => {
            if (isEffectCancelled || cancelledRef.current) return
            // Drop events from a stale EventSource (StrictMode leftovers, etc.)
            if (eventSource !== eventSourceRef.current) {
              eventSource.close()
              return
            }
            try {
              const data = JSON.parse(e.data)
              if (data.image_data_url) {
                setQrCodeUrl(data.image_data_url)
                goToStep(2) // → scan QR
              }
            } catch (err) {
              console.warn(`[SSE] ${ctx} failed to parse 'qrcode' event:`, err)
            }
          })

          eventSource.addEventListener('result', async (e) => {
            if (isEffectCancelled || cancelledRef.current) return
            if (eventSource !== eventSourceRef.current) {
              eventSource.close()
              return
            }
            eventSource.close()
            eventSourceRef.current = null

            try {
              const data = JSON.parse(e.data)
              if (data.success) {
                goToStep(3) // → verifying
                await new Promise((r) => setTimeout(r, 1000))
                if (isEffectCancelled || cancelledRef.current) return

                goToStep(4) // → saving

                const confirmResult = await confirmAuthorize.mutateAsync({
                  groupId,
                  platform,
                })

                if (isEffectCancelled || cancelledRef.current) return

                if (confirmResult.success) {
                  goToStep(5) // → complete
                  setIsCompleting(true)
                  completingRef.current = true
                  addToast('授权添加成功', 'success')

                  // auto-close after success
                  setTimeout(() => {
                    if (!isEffectCancelled && !cancelledRef.current) {
                      onComplete()
                      onOpenChange(false)
                    }
                  }, 1800)
                } else {
                  // Backend-provided message surfaces verbatim, with context for traceability
                  const msg = confirmResult.message
                    ? `${confirmResult.message}（${ctx}）`
                    : `保存授权失败 ${ctx}`
                  setErrorMessage(msg)
                  addToast(msg, 'error')
                }
              } else {
                // Backend-provided login failure message surfaces verbatim, with context
                const msg = data.message
                  ? `${data.message}（${ctx}）`
                  : `登录失败 ${ctx}`
                console.warn(`[SSE] ${ctx} backend returned failure:`, data)
                setErrorMessage(msg)
                addToast(msg, 'error')
              }
            } catch (err) {
              console.warn(`[SSE] ${ctx} failed to parse 'result' event:`, err)
              setErrorMessage(`登录失败，无法解析后端响应 ${ctx}`)
              addToast(`登录失败，无法解析后端响应 ${ctx}`, 'error')
            }
          })

          eventSource.onerror = () => {
            if (isEffectCancelled || cancelledRef.current) return
            // Stale-ES guard (see note at the fresh-EventSource creation site): the
            // shared `eventSourceRef.current` may now point to a sibling ES opened by
            // the second StrictMode setup. Reading `eventSourceRef.current` here would
            // surface its (possibly CONNECTING) state and trigger a wrong
            // "无法连接" toast. Reference the closure's own `eventSource` instead.
            if (eventSource !== eventSourceRef.current) {
              console.info(`[SSE-stale] ${ctx} ignoring onerror from stale EventSource`)
              eventSource.close()
              return
            }
            // Reference the closure's actual EventSource, not the shared ref,
            // to avoid reading state from a sibling EventSource.
            const { userMsg, log } = describeSseError(eventSource)
            console.warn(log)
            eventSource.close()
            eventSourceRef.current = null
            if (timeoutRef.current) clearTimeout(timeoutRef.current)
            timeoutRef.current = null
            setErrorMessage(userMsg)
            addToast(userMsg, 'error')
          }

          // Safety timeout (5 minutes)
          timeoutRef.current = setTimeout(() => {
            if (isEffectCancelled || cancelledRef.current || completingRef.current) return
            // Stale ES — this timeout belongs to a prior setup whose EventSource
            // was already replaced; do nothing.
            if (eventSource !== eventSourceRef.current) {
              timeoutRef.current = null
              return
            }
            const es = eventSourceRef.current
            es?.close()
            eventSourceRef.current = null
            timeoutRef.current = null
            const msg = `登录已超过 5 分钟未完成 ${ctx}，请重试或确认手机已扫码`
            console.warn(`[SSE] ${ctx} safety timeout reached`)
            setErrorMessage(msg)
            addToast(msg, 'warning')
          }, 300000)
        } else {
          // Branch when authorize endpoint returned {success:false} (e.g. 409 already authorized)
          const msg = result.message
            ? `${result.message}（${ctx}）`
            : `启动授权失败 ${ctx}`
          console.warn(`[authorize] ${ctx} authorize endpoint returned failure:`, result)
          setErrorMessage(msg)
          addToast(msg, 'error')
        }
      })
      .catch((err) => {
        if (isEffectCancelled || cancelledRef.current) return
        // Surface real network/HTTP error to console for diagnosis; show generic to user
        console.error(`[authorize] ${ctx} request failed:`, err)
        const msg = `授权请求失败 ${ctx}（请打开浏览器控制台查看详情）`
        setErrorMessage(msg)
        addToast(msg, 'error')
      })

    return () => {
      isEffectCancelled = true
      cancelledRef.current = true
      cleanup()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  const currentStep = STEPS[currentStepIndex] ?? STEPS[0]
  const progressValue = currentStep.progress

  // ── Manual (non-QR) flow: verify & save ────────────────────────────
  const handleManualVerify = useCallback(async () => {
    setIsVerifying(true)
    setErrorMessage(null)
    try {
      const confirmResult = await confirmAuthorize.mutateAsync({ groupId, platform })
      if (confirmResult.success) {
        setIsCompleting(true)
        completingRef.current = true
        addToast('授权添加成功', 'success')
        setTimeout(() => {
          if (!cancelledRef.current) {
            onComplete()
            onOpenChange(false)
          }
        }, 1800)
      } else {
        setErrorMessage(confirmResult.message || '未检测到登录信息')
        addToast(confirmResult.message || '未检测到登录信息', 'error')
      }
    } catch {
      setErrorMessage('验证请求失败')
      addToast('验证请求失败', 'error')
    } finally {
      setIsVerifying(false)
    }
  }, [confirmAuthorize, groupId, platform, addToast, onComplete, onOpenChange])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[420px] gap-0 p-0">
        {/* ── Header ─────────────────────────────────────────────────── */}
        <div className="p-6 pb-4">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <div
                className={cn(
                  // QR branch keeps `bg-primary/10 text-primary` (= Linear CTA
                  // palette, NOT status). Non-QR branch falls back to the
                  // status-warning chip via `@/lib/tone`.
                  'flex h-7 w-7 items-center justify-center rounded-lg',
                  isQrPlatform
                    ? 'bg-primary/10 text-primary'
                    : cn(toneBgClass('warning'), toneTextClass('warning')),
                )}
              >
                {isQrPlatform ? <QrCode className="h-4 w-4" /> : <Terminal className="h-4 w-4" />}
              </div>
              <span>{isQrPlatform ? '扫码登录' : '手动登录'}</span>
              <span className="text-xs font-normal text-muted-foreground">·</span>
              <span className="text-xs font-normal text-muted-foreground">{platformLabel}</span>
            </DialogTitle>
            <DialogDescription className="text-xs">{groupName}</DialogDescription>
          </DialogHeader>
        </div>

        {isQrPlatform ? (
          <>
            {/* ── Progress bar ───────────────────────────────────────────── */}
            <div className="px-6 pb-2">
              <div className="flex items-center gap-3">
                <div className="flex-1">
                  <Progress value={progressValue} className="h-1.5" />
                </div>
                <span className="text-[11px] font-medium text-muted-foreground tabular-nums shrink-0">
                  {progressValue}%
                </span>
              </div>
              <p className="mt-1.5 text-[11px] text-muted-foreground/70">{currentStep.description}</p>
            </div>

            {/* ── Step indicators ────────────────────────────────────────── */}
            <div className="px-6 py-3">
              {STEPS.map((step, i) => {
                const isCompleted = i < currentStepIndex
                const isActive = i === currentStepIndex && !errorMessage && !isCompleting
                const isPending = i > currentStepIndex
                const StepIcon = step.icon

                return (
                  <div key={step.key} className="flex items-center gap-3 py-[5px]">
                    {/* Status bullet */}
                    <div className="flex h-5 w-5 items-center justify-center shrink-0">
                      {isCompleted ? (
                        <motion.div
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          transition={{ type: 'spring', stiffness: 400, damping: 20 }}
                        >
                          <CheckCircle2 className={cn('h-4 w-4', toneTextClass('success'))} />
                        </motion.div>
                      ) : isActive ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                      ) : (
                        <Circle
                          className={cn(
                            'h-[7px] w-[7px] fill-current',
                            isPending ? 'text-muted-foreground/20' : 'text-muted-foreground/40',
                          )}
                        />
                      )}
                    </div>

                    {/* Step icon */}
                    <div
                      className={cn(
                        'flex h-7 w-7 items-center justify-center rounded-md shrink-0 transition-colors duration-300',
                        isCompleted
                          ? cn(toneBgClass('success'), toneTextClass('success'))
                          : isActive
                            ? 'bg-primary/10 text-primary'
                            : 'bg-muted/50 text-muted-foreground/40',
                      )}
                    >
                      <StepIcon className="h-3.5 w-3.5" />
                    </div>

                    {/* Step label */}
                    <span
                      className={cn(
                        'text-xs transition-colors duration-200',
                        isActive && 'font-medium text-foreground',
                        isCompleted && 'text-muted-foreground',
                        isPending && 'text-muted-foreground/40',
                      )}
                    >
                      {step.label}
                    </span>
                  </div>
                )
              })}
            </div>

            {/* ── QR Code display ────────────────────────────────────────── */}
            <AnimatePresence mode="wait">
              {currentStep.key === 'scan_qr' && qrCodeUrl && !errorMessage && (
                <motion.div
                  key="qr-section"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.3, ease: 'easeInOut' }}
                  className="overflow-hidden px-6"
                >
                  <div className="flex flex-col items-center pb-4">
                    <div className="relative">
                      <img
                        src={qrCodeUrl}
                        alt={`${platformLabel} 登录二维码`}
                        className="w-52 h-52 rounded-xl border border-border shadow-sm"
                      />
                      <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 translate-y-full mt-2 whitespace-nowrap">
                        <span className={cn('text-[10px] flex items-center gap-1', toneTextClass('warning'))}>
                          <AlertCircle className="h-3 w-3" />
                          二维码有效期 5 分钟，请使用 {platformLabel} App 扫码
                        </span>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* ── QR loading skeleton ────────────────────────────────────── */}
            <AnimatePresence mode="wait">
              {currentStep.key === 'scan_qr' && !qrCodeUrl && !errorMessage && (
                <motion.div
                  key="qr-loading"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex flex-col items-center pb-4 px-6"
                >
                  <div className="w-52 h-52 rounded-xl border-2 border-dashed border-border/60 bg-muted/20 flex flex-col items-center justify-center gap-2">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground/50" />
                    <span className="text-[11px] text-muted-foreground/50">正在获取二维码…</span>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </>
        ) : (
          <>
            {/* ── Manual CLI instruction view ────────────────────────────── */}
            <div className="px-6 pb-3 space-y-4">
              <div className={cn('rounded-lg p-4', toneBorderClass('warning'), toneBgClass('warning'))}>
                <div className="flex items-start gap-2.5">
                  <AlertCircle className={cn('h-4 w-4 mt-0.5 shrink-0', toneTextClass('warning'))} />
                  <div>
                    <p className={cn('text-xs font-medium', toneTextClass('warning'))}>
                      {platformLabel} 需要本地终端登录
                    </p>
                    {/* color-mix dimmed foreground — kept inline: it's an
                        opacity reduction on the same warning-fg, not a different
                        tonal vocabulary entry. */}
                    <p className="mt-1 text-[11px] text-[color-mix(in_oklab,var(--status-warning-fg),transparent_30%)]">
                      该平台不支持网页端扫码登录，请先在本地终端运行以下命令完成登录，
                      然后点击下方按钮验证并保存授权。
                    </p>
                  </div>
                </div>
              </div>

              <CliCommandBlock command={`sau ${platform} login --account "${groupName}"`} />

              <p className="text-[10px] text-muted-foreground leading-relaxed">
                登录完成后，Cookie 将保存到 <code className="text-[10px] bg-muted px-1 rounded">cookies/{`${platform}_${groupName}`}.json</code>，
                届时该平台的授权信息即可在网页端使用。
              </p>

              <Button
                onClick={handleManualVerify}
                disabled={isVerifying || isCompleting}
                className="w-full"
                variant="default"
              >
                {isVerifying ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Shield className="h-4 w-4 mr-2" />
                )}
                {isVerifying ? '正在验证…' : '验证并保存授权'}
              </Button>
            </div>
          </>
        )}

        {/* ── Error banner ───────────────────────────────────────────── */}
        <AnimatePresence>
          {errorMessage && (
            <motion.div
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.25, ease: 'easeOut' }}
              className={cn(
                'mx-6 mb-5 flex items-start gap-2 rounded-lg p-3',
                toneBorderClass('error'),
                toneBgClass('error'),
              )}
            >
              <XCircle className={cn('mt-0.5 h-4 w-4 shrink-0', toneTextClass('error'))} />
              <div className="flex-1 min-w-0">
                <p className={cn('text-xs font-medium', toneTextClass('error'))}>授权失败</p>
                <p className={cn('mt-0.5 text-[11px]', `${toneTextClass('error')}/80`)}>{errorMessage}</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Success banner ─────────────────────────────────────────── */}
        <AnimatePresence>
          {isCompleting && (
            <motion.div
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              className={cn(
                'mx-6 mb-5 flex items-center gap-2 rounded-lg p-3',
                toneBorderClass('success'),
                toneBgClass('success'),
              )}
            >
              <CheckCircle2 className={cn('h-4 w-4 shrink-0', toneTextClass('success'))} />
              <p className={cn('text-xs font-medium', toneTextClass('success'))}>
                {platformLabel} 授权已成功添加
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Spacer for consistent bottom padding ───────────────────── */}
        <div className="h-4" />
      </DialogContent>
    </Dialog>
  )
}
