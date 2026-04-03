import * as React from "react";

import { cn } from "../../lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "flex h-12 w-full rounded-2xl border border-white/10 bg-white/8 px-4 py-3 text-sm text-white outline-none transition placeholder:text-white/35 focus:border-gold/50 focus:ring-2 focus:ring-gold/25",
        className,
      )}
      {...props}
    />
  ),
);

Input.displayName = "Input";
