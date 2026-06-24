import { type KeyboardEvent, useCallback, useEffect, useRef, useState } from 'react'
import { cn } from '@/lib/utils'
import { X } from 'lucide-react'
import { toneRingClass, toneTextClass } from '@/lib/tone'

function normalizeTag(raw: string): string {
  const cleaned = raw.trim().replace(/^#+/, '').replace(/,/g, '')
  return cleaned ? `#${cleaned}` : ''
}

function parseTags(value: string): string[] {
  return value
    .split(',')
    .map((t) => normalizeTag(t))
    .filter(Boolean)
}

function tagText(tag: string): string {
  return tag.replace(/^#+/, '')
}

interface TagInputProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  maxLength?: number
  maxTags?: number
  className?: string
  disabled?: boolean
}

export function TagInput({
  value,
  onChange,
  placeholder = '输入标签后按 Enter',
  maxLength = 20,
  maxTags,
  className,
  disabled,
}: TagInputProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [inputValue, setInputValue] = useState('')
  const tags = parseTags(value)

  const emitTags = useCallback(
    (next: string[]) => {
      onChange(next.join(','))
    },
    [onChange],
  )

  const isAtLimit = maxTags !== undefined && tags.length >= maxTags

  const addTag = useCallback(
    (raw: string) => {
      if (maxTags !== undefined && tags.length >= maxTags) return
      const normalized = normalizeTag(raw)
      if (!normalized) return
      const text = tagText(normalized)
      if (text.length > maxLength) return
      const existingTexts = tags.map(tagText)
      if (existingTexts.includes(text)) return
      emitTags([...tags, normalized])
    },
    [tags, emitTags, maxLength, maxTags],
  )

  const removeTag = useCallback(
    (index: number) => {
      const next = tags.filter((_, i) => i !== index)
      emitTags(next)
    },
    [tags, emitTags],
  )

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' || e.key === ',') {
        e.preventDefault()
        if (maxTags !== undefined && tags.length >= maxTags) return
        addTag(inputValue)
        setInputValue('')
        return
      }
      if (e.key === 'Backspace' && !inputValue && tags.length > 0) {
        removeTag(tags.length - 1)
      }
    },
    [inputValue, tags, addTag, removeTag, maxTags],
  )

  const handlePaste = useCallback(
    (e: React.ClipboardEvent) => {
      const text = e.clipboardData.getData('text')
      if (text.includes(',') || text.includes('#')) {
        e.preventDefault()
        const pastedTags = text.split(/[,，]+/).map((t) => t.trim()).filter(Boolean)
        const next = [...tags]
        const existingTexts = next.map(tagText)
        let remaining = maxTags !== undefined ? maxTags - next.length : Infinity
        for (const t of pastedTags) {
          if (remaining <= 0) break
          const normalized = normalizeTag(t)
          if (!normalized) continue
          const text = tagText(normalized)
          if (text.length <= maxLength && !existingTexts.includes(text)) {
            next.push(normalized)
            existingTexts.push(text)
            remaining--
          }
        }
        emitTags(next)
      }
    },
    [tags, emitTags, maxLength, maxTags],
  )

  // Sync external value changes (reset input on clear)
  useEffect(() => {
    if (!value) setInputValue('')
  }, [value])

  // Count-color routed through `@/lib/tone` for the warning + error tier.
  // The `text-muted-foreground` baseline stays — it's not a tonal cue.
  const tagCountColor =
    maxTags !== undefined
      ? tags.length >= maxTags
        ? toneTextClass('error')
        : tags.length >= maxTags * 0.8
          ? toneTextClass('warning')
          : 'text-muted-foreground'
      : 'text-muted-foreground'

  return (
    <>
      <div
        className={cn(
          'flex min-h-9 flex-wrap items-center gap-1.5 rounded-md border border-input bg-transparent px-3 py-1.5 text-sm shadow-sm transition-colors focus-within:ring-1 focus-within:ring-ring',
          // At-limit outline: the fg color serves as a tinted outline (NOT a
          // chip rendering). The lib's vocabulary entry for `border` uses
          // --status-*-border tokens, which would shift hue too far; using
          // the fg at 40% alpha gives a subtler warning halo. Kept inline
          // intentionally — this is the ONE outlier site where fg serves
          // as an outline color, and bumping the lib to expose the shape
          // would conflict with the SSoT contract that `border[x]` means
          // "true border token".
          isAtLimit && `border-[var(--status-error-fg)]/40 focus-within:${toneRingClass('error')}/40`,
          disabled && 'cursor-not-allowed opacity-50',
          className,
        )}
        onClick={() => inputRef.current?.focus()}
      >
        {tags.map((tag, idx) => (
          <span
            key={tag}
            className={cn(
              'inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium',
              'bg-primary/10 text-primary',
            )}
          >
            <span>{tag}</span>
            {!disabled && (
              <button
                type="button"
                className="ml-0.5 inline-flex h-3.5 w-3.5 items-center justify-center rounded-full hover:bg-primary/20 transition-colors"
                onClick={(e) => {
                  e.stopPropagation()
                  removeTag(idx)
                }}
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </span>
        ))}
        <input
          ref={inputRef}
          type="text"
          className="min-w-[80px] flex-1 border-none bg-transparent py-0.5 text-sm outline-none placeholder:text-muted-foreground"
          placeholder={isAtLimit ? '已达标签上限' : tags.length === 0 ? placeholder : ''}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          disabled={disabled || isAtLimit}
          maxLength={maxLength + 1}
        />
      </div>
      {maxTags !== undefined && (
        <div className="flex justify-end mt-1">
          <span className={cn('text-xs tabular-nums', tagCountColor)}>
            {tags.length}/{maxTags}
          </span>
        </div>
      )}
    </>
  )
}
