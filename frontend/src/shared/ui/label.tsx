import * as React from "react";

import { cn } from "@/shared/lib/utils";

const Label = React.forwardRef<HTMLLabelElement, React.LabelHTMLAttributes<HTMLLabelElement>>(
  ({ className, ...props }, ref) => (
    // La asociación (`htmlFor`) llega por props en tiempo de ejecución; el análisis estático no
    // puede verla (mismo descarte que shadcn/ui upstream).
    /* eslint-disable-next-line jsx-a11y/label-has-associated-control */
    <label
      ref={ref}
      className={cn(
        "text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70",
        className,
      )}
      {...props}
    />
  ),
);
Label.displayName = "Label";

export { Label };
