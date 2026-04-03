import * as React from "react";

import { cn } from "../../lib/utils";

type BadgeProps = React.HTMLAttributes<HTMLSpanElement> & {
  variant?: "default" | "gold" | "subtle" | "caution";
};

const variants: Record<NonNullable<BadgeProps["variant"]>, string> = {
  default: "bg-white/10 text-white",
  gold: "bg-gold/20 text-gold",
  subtle: "bg-white/6 text-white/75",
  caution: "bg-[#ff8f6b]/18 text-[#ffb59a]",
};

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold tracking-[0.02em]",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}
