import * as React from "react"
import { cn } from "@/lib/utils"

interface ColProps extends React.HTMLAttributes<HTMLDivElement> {
  span?: number
  xs?: number
  sm?: number
  md?: number
  lg?: number
  xl?: number
}

const Col = React.forwardRef<HTMLDivElement, ColProps>(
  ({ className, span, xs, sm, md, lg, xl, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "col-span-1",
          span && `col-span-${span}`,
          xs && `max-xs:col-span-${xs}`,
          sm && `sm:col-span-${sm}`,
          md && `md:col-span-${md}`,
          lg && `lg:col-span-${lg}`,
          xl && `xl:col-span-${xl}`,
          className
        )}
        {...props}
      />
    )
  }
)
Col.displayName = "Col"

interface RowProps extends React.HTMLAttributes<HTMLDivElement> {
  gutter?: number | [number, number]
}

const Row = React.forwardRef<HTMLDivElement, RowProps>(
  ({ className, gutter = 0, children, ...props }, ref) => {
    const [horizontal, vertical] = Array.isArray(gutter) ? gutter : [gutter, gutter]

    return (
      <div
        ref={ref}
        className={cn("grid grid-cols-12 gap-4", className)}
        style={{
          marginLeft: `-${horizontal / 2}px`,
          marginRight: `-${horizontal / 2}px`,
        }}
        {...props}
      >
        {React.Children.map(children, (child) => {
          if (React.isValidElement(child)) {
            return React.cloneElement(child as React.ReactElement<any>, {
              style: {
                paddingLeft: `${horizontal / 2}px`,
                paddingRight: `${horizontal / 2}px`,
                paddingTop: `${vertical / 2}px`,
                paddingBottom: `${vertical / 2}px`,
              },
            })
          }
          return child
        })}
      </div>
    )
  }
)
Row.displayName = "Row"

export { Row, Col }
