import { cn } from "@/lib/utils";

export function Brand({
  variant = "default",
  compact = false,
  className,
}: {
  variant?: "default" | "light";
  compact?: boolean;
  className?: string;
}) {
  const light = variant === "light";
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <img
        src="/favicon.png"
        alt="Logo Lins Agroindustrial"
        className={cn(
          "shrink-0 object-contain",
          compact ? "h-8 w-8" : "h-10 w-10",
          light && "rounded-lg bg-white p-1 shadow-sm",
        )}
      />
      {!compact && (
        <div className="leading-none">
          <p
            className={cn(
              "text-lg font-extrabold tracking-tight",
              light ? "text-white" : "text-primary",
            )}
          >
            LINS
          </p>
          <p
            className={cn(
              "mt-1 text-[9px] font-semibold uppercase tracking-[0.22em]",
              light ? "text-white/70" : "text-muted-foreground",
            )}
          >
            Agroindustrial
          </p>
        </div>
      )}
    </div>
  );
}
