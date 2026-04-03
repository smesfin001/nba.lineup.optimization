import * as React from "react";

import { cn } from "../../lib/utils";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "default" | "ghost" | "outline" | "chip";
};

const variants: Record<NonNullable<ButtonProps["variant"]>, string> = {
  default:
    "bg-gold text-ink shadow-[0_16px_40px_rgba(242,201,76,0.28)] hover:bg-[#ffd86e] focus-visible:ring-gold/50",
  ghost: "bg-white/6 text-cream hover:bg-white/10 focus-visible:ring-white/20",
  outline:
    "border border-white/20 bg-white/5 text-cream hover:border-gold/60 hover:bg-white/10 focus-visible:ring-gold/30",
  chip:
    "border border-white/15 bg-white/6 text-cream hover:border-gold/50 hover:bg-white/12 focus-visible:ring-gold/30",
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", type = "button", ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      className={cn(
        "inline-flex items-center justify-center rounded-2xl px-4 py-2.5 text-sm font-semibold transition duration-200 focus-visible:outline-none focus-visible:ring-2 disabled:cursor-not-allowed disabled:opacity-50",
        variants[variant],
        className,
      )}
      {...props}
    />
  ),
);

Button.displayName = "Button";
