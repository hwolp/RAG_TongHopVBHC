import * as React from "react"
import { Checkbox as RadixCheckbox } from "@/components/ui/checkbox"
import { cn } from "@/lib/utils"

const Checkbox = React.forwardRef<
  React.ElementRef<typeof RadixCheckbox>,
  React.ComponentPropsWithoutRef<typeof RadixCheckbox>
>(({ className, ...props }, ref) => (
  <RadixCheckbox
    ref={ref}
    className={cn(
      "h-4 w-4 rounded border-primary bg-transparent hover:bg-primary/20 data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground",
      className
    )}
    {...props}
  />
))
Checkbox.displayName = RadixCheckbox.displayName

export { Checkbox }