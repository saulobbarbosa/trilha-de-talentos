import * as React from "react";

import { cn } from "@/lib/utils";

const NativeSelect = React.forwardRef<HTMLSelectElement, React.ComponentProps<"select">>(
  ({ className, children, ...props }, ref) => (
    <select
      ref={ref}
      className={cn(
        "flex h-11 w-full rounded-md border border-input bg-transparent px-3 text-base shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  ),
);
NativeSelect.displayName = "NativeSelect";

export { NativeSelect };
