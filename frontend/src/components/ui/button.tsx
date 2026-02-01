import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "../../utils"

// Constantes de configuraciÃ³n
const DEFAULT_HEIGHT = 10
const SMALL_HEIGHT = 9
const LARGE_HEIGHT = 11
const ICON_SIZE = 10
const DEFAULT_PADDING_X = 4
const DEFAULT_PADDING_Y = 2
const SMALL_PADDING_X = 3
const LARGE_PADDING_X = 8
const ICON_SPINNER_SIZE = 4
const ICON_SPINNER_MARGIN = 2
const CIRCLE_RADIUS = 10
const CIRCLE_STROKE_WIDTH = 4
const SPRING_STIFFNESS = 200

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline:
          "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
        success: "bg-green-600 text-white hover:bg-green-700",
        warning: "bg-yellow-600 text-white hover:bg-yellow-700",
      },
      size: {
        default: `h-${DEFAULT_HEIGHT} px-${DEFAULT_PADDING_X} py-${DEFAULT_PADDING_Y}`,
        sm: `h-${SMALL_HEIGHT} rounded-md px-${SMALL_PADDING_X}`,
        lg: `h-${LARGE_HEIGHT} rounded-md px-${LARGE_PADDING_X}`,
        icon: `h-${ICON_SIZE} w-${ICON_SIZE}`,
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
  loading?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, loading = false, children, disabled, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={disabled || loading}
        {...props}
      >
        {loading && (
          <svg
            className={`mr-${ICON_SPINNER_MARGIN} h-${ICON_SPINNER_SIZE} w-${ICON_SPINNER_SIZE} animate-spin`}
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r={CIRCLE_RADIUS}
              stroke="currentColor"
              strokeWidth={CIRCLE_STROKE_WIDTH}
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        )}
        {children}
      </button>
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
