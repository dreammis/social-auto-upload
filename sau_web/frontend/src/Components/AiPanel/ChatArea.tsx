import { useMemo } from 'react'
import { Sparkles, Loader2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useChatStore } from '@/stores/useChatStore'
import type { ChatMessage } from '@/lib/chat/types'

export const MarkdownContent = ({ content }: { content: string }) => (
  <ReactMarkdown
    remarkPlugins={[remarkGfm]}
    className="prose prose-sm max-w-none dark:prose-invert [&_p]:my-0.5 [&_ul]:my-0.5 [&_ol]:my-0.5 [&_pre]:my-1 [&_h1]:text-sm [&_h2]:text-xs [&_h3]:text-xs"
  >
    {content}
  </ReactMarkdown>
)

interface ChatAreaProps {
  /** Optional extra className for the scroll container. */
  className?: string
}

/**
 * Read-only view of the current chat session + in-flight stream.
 *
 * Renders directly from `useChatStore` — no props other than styling.
 * Lives below the input / generate controls in the AI sidebar so users
 * can see their turns alongside the AI's drafts.
 *
 * Empty state: when there is no active session OR no messages yet, show
 * a single inviting hint. The user creates the first session implicitly
 * by clicking "一键生成" / "一键全流程".
 */
export function ChatArea({ className }: ChatAreaProps) {
  const activeSessionId = useChatStore((s) => s.activeSessionId)
  const session = useChatStore((s) => (activeSessionId ? s.sessions[activeSessionId] : null))
  const messages = session?.messages
  const streamingDraft = useChatStore((s) => s.streamingDraft)
  const jobStatus = useChatStore((s) => s.jobStatus)
  const error = useChatStore((s) => s.error)

  const isStreaming = jobStatus === 'generating' && streamingDraft.length > 0

  const empty = useMemo(
    () => !messages || messages.length === 0,
    [messages],
  )

  return (
    <div className={className}>
      {error && jobStatus === 'error' && (
        <div className="mb-2 rounded-md border border-destructive/30 bg-destructive/5 px-2.5 py-1.5 text-[11px] text-destructive">
          {error}
        </div>
      )}

      {empty && !isStreaming && (
        <p className="flex items-center gap-1.5 rounded-md border border-dashed border-border/60 bg-muted/30 px-3 py-3 text-[11px] leading-relaxed text-muted-foreground">
          <Sparkles className="h-3 w-3 shrink-0 text-primary" />
          点击上方「一键生成」开始第一次对话。后续追问会保留上下文。
        </p>
      )}

      <ul className="space-y-1.5">
        {messages?.map((m) => (
          <ChatBubble key={m.id} message={m} />
        ))}
        {isStreaming && (
          <li className="flex items-start gap-1.5">
            <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Loader2 className="h-2.5 w-2.5 animate-spin" />
            </span>
            <div className="rounded-md bg-muted/60 px-2.5 py-1.5 text-[12px] leading-relaxed text-foreground/90">
              <MarkdownContent content={streamingDraft} />
              <span className="ml-0.5 inline-block h-3 w-0.5 animate-pulse rounded-full bg-primary align-middle" />
            </div>
          </li>
        )}
      </ul>
    </div>
  )
}

function ChatBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'
  const isAssistant = message.role === 'assistant'
  const isSystem = message.role === 'system'

  if (isSystem) {
    return (
      <li className="rounded-md bg-muted/30 px-2.5 py-1 text-[10px] italic leading-relaxed text-muted-foreground">
        {message.content}
      </li>
    )
  }

  return (
    <li className={isUser ? 'flex justify-end' : 'flex justify-start'}>
      <div
        className={
          isUser
            ? 'max-w-[85%] rounded-2xl rounded-br-sm bg-primary/10 px-2.5 py-1.5 text-[12px] leading-relaxed text-foreground/90'
            : 'max-w-[85%] rounded-2xl rounded-bl-sm bg-muted/60 px-2.5 py-1.5 text-[12px] leading-relaxed text-foreground/90'
        }
      >
        {isAssistant && (
          <div className="mb-0.5 flex items-center gap-1 text-[9px] font-medium uppercase tracking-wider text-primary/70">
            <Sparkles className="h-2.5 w-2.5" />
            AI
          </div>
        )}
        <div className="whitespace-pre-wrap break-words">
          {isAssistant ? <MarkdownContent content={message.content} /> : message.content}
        </div>
        {message.appliedTo && message.appliedTo.length > 0 && (
          <div className="mt-1 text-[9px] text-muted-foreground">
            已应用到: {message.appliedTo.join('、')}
          </div>
        )}
      </div>
    </li>
  )
}
