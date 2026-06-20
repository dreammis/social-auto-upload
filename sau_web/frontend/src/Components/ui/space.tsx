import * as React from "react"
import { cn } from "@/lib/utils"

interface SpaceProps extends React.HTMLAttributes<HTMLDivElement> {
  direction?: "horizontal" | "vertical"
  size?: number | "small" | "middle" | "large" | [number, number]
  wrap?: boolean
  align?: "start" | "end" | "center" | "baseline"
  split?: React.ReactNode
}

const Space = React.forwardRef<HTMLDivElement, SpaceProps>(
  ({ className, direction = "horizontal", size = "small", wrap, align, split, children, ...props }, ref) => {
    const getSize = () => {
      if (typeof size === "number") return size
      switch (size) {
        case "small": return 8
        case "middle": return 16
        case "large": return 24
        default: return 8
      }
    }

    const gap = getSize()

    const items = React.Children.toArray(children).filter(Boolean)

    return (
      <div
        ref={ref}
        className={cn(
          "flex",
          direction === "vertical" ? "flex-col" : "flex-row",
          wrap && "flex-wrap",
          align && {
            "items-start": align === "start",
            "items-end": align === "end",
            "items-center": align === "center",
            "items-baseline": align === "baseline",
          },
          className
        )}
        style={{
          gap: `${gap}px`,
        }}
        {...props}
      >
        {items.map((item, index) => (
          <React.Fragment key={index}>
            {item}
            {split && index < items.length - 1 && (
              <span className="text-muted-foreground">{split}</span>
            )}
          </React.Fragment>
        ))}
      </div>
    )
  }
)
Space.displayName = "Space"

export { Space }
