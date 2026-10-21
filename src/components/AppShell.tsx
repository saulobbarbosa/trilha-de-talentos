import { ArrowLeft, LogOut } from "lucide-react";
import type { ReactNode } from "react";

import { Brand } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";
import { useRouter } from "@/lib/router";
import { cn } from "@/lib/utils";

export function AppShell({
  title,
  subtitle,
  backTo,
  actions,
  children,
  className,
}: {
  title: string;
  subtitle?: string;
  backTo?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  const { logout } = useAuth();
  const { navigate } = useRouter();

  return (
    <div className="min-h-dvh bg-background">
      <header className="sticky top-0 z-40 border-b bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/85">
        <div className="mx-auto flex w-full max-w-5xl items-center gap-2 px-3 py-2.5 sm:px-6">
          {backTo ? (
            <Button
              variant="ghost"
              size="icon"
              aria-label="Voltar"
              className="h-10 w-10 shrink-0"
              onClick={() => navigate(backTo)}
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
          ) : (
            <Brand compact className="ml-1 shrink-0" />
          )}
          <div className="min-w-0 flex-1 px-1">
            <h1 className="truncate text-base font-bold leading-tight text-primary sm:text-lg">
              {title}
            </h1>
            {subtitle && (
              <p className="truncate text-[11px] text-muted-foreground sm:text-xs">{subtitle}</p>
            )}
          </div>
          {actions}
          <Button
            variant="ghost"
            size="icon"
            aria-label="Sair"
            className="h-10 w-10 shrink-0 text-muted-foreground"
            onClick={() => void logout()}
          >
            <LogOut className="h-5 w-5" />
          </Button>
        </div>
      </header>
      <main className={cn("mx-auto w-full max-w-5xl px-4 pb-24 pt-5 sm:px-6", className)}>
        {children}
      </main>
    </div>
  );
}

export function StatGrid({ stats }: { stats: { label: string; value: string; hint?: string }[] }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {stats.map((stat) => (
        <div key={stat.label} className="rounded-2xl border bg-card p-4 shadow-card">
          <p className="text-[11px] font-medium text-muted-foreground sm:text-sm">{stat.label}</p>
          <p className="mt-1 text-2xl font-extrabold text-primary sm:text-3xl">{stat.value}</p>
          {stat.hint && <p className="mt-1 text-[11px] font-medium text-accent">{stat.hint}</p>}
        </div>
      ))}
    </div>
  );
}

export function SectionCard({
  title,
  description,
  action,
  children,
  className,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("rounded-2xl border bg-card shadow-card", className)}>
      <div className="flex items-start justify-between gap-3 border-b px-4 py-4 sm:px-5">
        <div>
          <h2 className="font-bold text-primary">{title}</h2>
          {description && <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

export function EmptyState({
  title,
  description,
  icon,
}: {
  title: string;
  description: string;
  icon?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-2 px-6 py-10 text-center">
      {icon && (
        <div className="mb-1 flex h-11 w-11 items-center justify-center rounded-full bg-secondary text-primary">
          {icon}
        </div>
      )}
      <p className="font-semibold text-primary">{title}</p>
      <p className="max-w-sm text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
