import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2 py-0.5 font-mono text-xs uppercase tracking-wider transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-primary/40 bg-primary/15 text-primary",
        secondary: "border-secondary/40 bg-secondary/20 text-secondary",
        destructive: "border-destructive/50 bg-destructive/15 text-destructive",
        outline: "border-primary/30 text-foreground",
        success: "border-emerald-500/40 bg-emerald-900/40 text-emerald-200",
        warning: "border-amber-500/40 bg-amber-900/40 text-amber-200",
        muted: "border-muted-foreground/30 bg-muted/50 text-muted-foreground",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
