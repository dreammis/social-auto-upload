import { useState, useCallback, useRef, useEffect } from "react"
import { Copy, Check } from "lucide-react"
import { cn } from "@/lib/utils"
import { useToast } from "@/components/ui/toast"

type TokenType = "prompt" | "command" | "platform" | "action" | "flag" | "string" | "number" | "path" | "value" | "plain"

interface Token {
  text: string
  type: TokenType
}

const KNOWN_PLATFORMS = new Set([
  "douyin",
  "kuaishou",
  "xiaohongshu",
  "bilibili",
  "tencent",
  "tiktok",
  "baijiahao",
])

const KNOWN_ACTIONS = new Set([
  "login",
  "check",
  "upload-video",
  "upload-note",
])

const TYPE_STYLES: Record<TokenType, string> = {
  prompt: "text-zinc-500",
  command: "text-cyan-400",
  platform: "text-fuchsia-400",
  action: "text-emerald-400",
  flag: "text-amber-300",
  string: "text-orange-300",
  number: "text-blue-400",
  path: "text-cyan-300",
  value: "text-zinc-300",
  plain: "text-zinc-300",
}

function isNumber(word: string): boolean {
  return /^\d+$/.test(word) || /^\d+\.\d+$/.test(word) || /^0[xX][0-9a-fA-F]+$/.test(word)
}

function isPath(word: string): boolean {
  if (word.includes("/") || word.includes("\\") || word.includes("~")) return true
  if (/\.(mp4|mov|avi|mkv|flv|wmv|jpg|jpeg|png|gif|webp|bmp|svg|txt|json|yaml|yml|md|py|js|ts|tsx|jsx|css|scss|html|xml|csv|log|sh|bat|exe|dll|zip|tar|gz|rar|7z|pdf|doc|docx|xls|xlsx|ppt|pptx)$/i.test(word)) {
    return true
  }
  return false
}

function tokenize(command: string): Token[] {
  const tokens: Token[] = []
  let i = 0
  let prevNonPlainType: TokenType | null = null

  while (i < command.length) {
    // Spaces
    if (command[i] === " ") {
      let spaces = ""
      while (i < command.length && command[i] === " ") {
        spaces += " "
        i++
      }
      tokens.push({ text: spaces, type: "plain" })
      continue
    }

    // Quoted strings
    if (command[i] === '"' || command[i] === "'") {
      const quote = command[i]
      let str = quote
      i++
      while (i < command.length && command[i] !== quote) {
        if (command[i] === "\\" && i + 1 < command.length) {
          str += command[i] + command[i + 1]
          i += 2
        } else {
          str += command[i]
          i++
        }
      }
      if (i < command.length) {
        str += command[i]
        i++
      }
      tokens.push({ text: str, type: "string" })
      prevNonPlainType = "string"
      continue
    }

    // Word / token
    let word = ""
    while (
      i < command.length &&
      command[i] !== " " &&
      command[i] !== '"' &&
      command[i] !== "'"
    ) {
      word += command[i]
      i++
    }

    // Split --flag=value into separate tokens for finer highlighting
    if (word.startsWith("--") && word.includes("=")) {
      const eqIdx = word.indexOf("=")
      const flagPart = word.slice(0, eqIdx)
      const valuePart = word.slice(eqIdx + 1)
      tokens.push({ text: flagPart, type: "flag" })
      prevNonPlainType = "flag"
      tokens.push({ text: "=", type: "plain" })
      if (valuePart) {
        tokens.push({ text: valuePart, type: "string" })
        prevNonPlainType = "string"
      }
      continue
    }

    let type: TokenType =
      word === "$"
        ? "prompt"
        : word === "sau"
          ? "command"
          : KNOWN_PLATFORMS.has(word)
            ? "platform"
            : KNOWN_ACTIONS.has(word)
              ? "action"
              : word.startsWith("--")
                ? "flag"
                : isNumber(word)
                  ? "number"
                  : isPath(word)
                    ? "path"
                    : (`value` as TokenType)

    // If the previous non-plain token was a flag and this token is a plain
    // generic value (not a number, path, or keyword), paint it as a string
    // to visually bind it to the flag.
    if (
      prevNonPlainType === "flag" &&
      type === "value"
    ) {
      type = "string"
    }

    tokens.push({ text: word, type })
    if (type !== "plain") {
      prevNonPlainType = type
    }
  }

  return tokens
}

// ── CliCommand ────────────────────────────────────────────────────────────

export interface CliCommandProps {
  command: string
  className?: string
  ariaLabel?: string
}

export function CliCommand({ command, className, ariaLabel }: CliCommandProps) {
  const tokens = tokenize(command)
  return (
    <code
      className={cn("whitespace-nowrap", className)}
      aria-label={ariaLabel ?? command}
    >
      {tokens.map((token, idx) => (
        <span key={idx} className={TYPE_STYLES[token.type]}>
          {token.text}
        </span>
      ))}
    </code>
  )
}

// ── Copy hook ─────────────────────────────────────────────────────────────

function useCopyCommand(command: string) {
  const [copied, setCopied] = useState(false)
  const { addToast } = useToast()
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const copy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(command)
      setCopied(true)
      addToast("已复制", "success")
      if (timerRef.current) clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => setCopied(false), 2000)
      return true
    } catch {
      addToast("复制失败，请手动复制", "error")
      return false
    }
  }, [command, addToast])

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [])

  return { copied, copy }
}

// ── Copy button ───────────────────────────────────────────────────────────

function CopyCommandButton({
  copied,
  onCopy,
  size = "default",
}: {
  copied: boolean
  onCopy: (e: React.MouseEvent<HTMLButtonElement>) => void
  size?: "default" | "sm"
}) {
  return (
    <button
      type="button"
      onClick={onCopy}
      className={cn(
        "flex items-center justify-center gap-1 rounded-md bg-zinc-800/60 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors shrink-0",
        size === "sm"
          ? "px-1.5 py-0.5 text-[10px] min-w-[56px]"
          : "px-2 py-1 text-[10px] min-w-[64px]"
      )}
      aria-label="复制命令"
    >
      {copied ? (
        <>
          <Check className="h-3 w-3 text-emerald-400" />
          <span className="text-emerald-400">已复制</span>
        </>
      ) : (
        <>
          <Copy className="h-3 w-3" />
          <span>复制</span>
        </>
      )}
    </button>
  )
}

// ── Block wrapper ─────────────────────────────────────────────────────────

export interface CliCommandBlockProps extends CliCommandProps {
  showCopy?: boolean
  size?: "default" | "sm"
}

const SIZE_STYLES = {
  default: "p-3 text-xs",
  sm: "p-2 text-[10px]",
}

export function CliCommandBlock({
  command,
  className,
  ariaLabel,
  showCopy = true,
  size = "default",
}: CliCommandBlockProps) {
  const { copied, copy } = useCopyCommand(command)

  const handleCopyClick = useCallback(
    (e: React.MouseEvent<HTMLButtonElement>) => {
      e.stopPropagation()
      copy()
    },
    [copy],
  )

  return (
    <div
      className={cn(
        "rounded-lg font-mono overflow-x-auto overflow-y-auto cursor-pointer transition-all duration-300",
        SIZE_STYLES[size],
        copied
          ? "bg-emerald-900/20 ring-2 ring-emerald-500/50"
          : "bg-zinc-950",
        className
      )}
      onClick={() => copy()}
      title="点击复制命令"
    >
      <div className="flex items-center justify-between gap-2">
        <CliCommand command={command} ariaLabel={ariaLabel} />
        {showCopy && (
          <CopyCommandButton copied={copied} onCopy={handleCopyClick} size={size} />
        )}
      </div>
    </div>
  )
}
