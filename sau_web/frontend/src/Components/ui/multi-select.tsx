import * as React from "react"
import { Check, ChevronDown, X } from "lucide-react"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"

export interface MultiSelectOption {
  label: string
  value: string
  icon?: React.ReactNode
}

interface MultiSelectProps {
  options: MultiSelectOption[]
  value: string[]
  onChange: (value: string[]) => void
  placeholder?: string
  maxCount?: number
  className?: string
}

export function MultiSelect({
  options,
  value,
  onChange,
  placeholder = "选择...",
  maxCount = 3,
  className,
}: MultiSelectProps) {
  const [open, setOpen] = React.useState(false)
  const containerRef = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const handleToggle = (itemValue: string) => {
    const newValue = value.includes(itemValue)
      ? value.filter((v) => v !== itemValue)
      : [...value, itemValue]
    onChange(newValue)
  }

  const handleRemove = (itemValue: string, e: React.MouseEvent) => {
    e.stopPropagation()
    onChange(value.filter((v) => v !== itemValue))
  }

  const selectedOptions = options.filter((o) => value.includes(o.value))
  const displayCount = value.length - maxCount

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      <button
        type="button"
        className={cn(
          "flex h-9 w-full items-center justify-between rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
          open && "ring-1 ring-ring"
        )}
        onClick={() => setOpen(!open)}
      >
        <div className="flex items-center gap-1 flex-1 min-w-0 overflow-hidden">
          {selectedOptions.length === 0 ? (
            <span className="text-muted-foreground">{placeholder}</span>
          ) : (
            <>
              {selectedOptions.slice(0, maxCount).map((option) => (
                <Badge
                  key={option.value}
                  variant="secondary"
                  className="flex items-center gap-1 px-2 py-0.5 text-xs"
                >
                  {option.icon && <span className="flex-shrink-0">{option.icon}</span>}
                  <span className="truncate">{option.label}</span>
                  <button
                    type="button"
                    className="ml-0.5 rounded-full hover:bg-muted-foreground/20 p-0.5"
                    onClick={(e) => handleRemove(option.value, e)}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
              {displayCount > 0 && (
                <Badge variant="secondary" className="px-2 py-0.5 text-xs">
                  +{displayCount}
                </Badge>
              )}
            </>
          )}
        </div>
        <ChevronDown className={cn("h-4 w-4 shrink-0 text-muted-foreground transition-transform", open && "rotate-180")} />
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-md border bg-popover text-popover-foreground shadow-md">
          <ScrollArea className="max-h-[200px]">
            <div className="p-1">
              {options.map((option) => {
                const isSelected = value.includes(option.value)
                return (
                  <button
                    key={option.value}
                    type="button"
                    className={cn(
                      "flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none transition-colors hover:bg-accent hover:text-accent-foreground",
                      isSelected && "bg-accent"
                    )}
                    onClick={() => handleToggle(option.value)}
                  >
                    <div className={cn(
                      "flex h-4 w-4 items-center justify-center rounded-sm border",
                      isSelected ? "bg-primary border-primary text-primary-foreground" : "border-muted-foreground/50"
                    )}>
                      {isSelected && <Check className="h-3 w-3" />}
                    </div>
                    {option.icon && <span className="flex-shrink-0">{option.icon}</span>}
                    <span className="flex-1 text-left">{option.label}</span>
                  </button>
                )
              })}
            </div>
          </ScrollArea>
        </div>
      )}
    </div>
  )
}
