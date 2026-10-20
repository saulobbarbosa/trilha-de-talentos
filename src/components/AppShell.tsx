import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { LogOut, Bell } from "lucide-react";
import logo from "@/assets/lins-logo.png.asset.json";

const nav = [
  { to: "/rh", label: "RH · Treinamentos" },
  { to: "/lider", label: "Líder · Reservas" },
  { to: "/instrutor", label: "Instrutor · Chamada" },
  { to: "/funcionario", label: "Meus Certificados" },
] as const;

export function AppShell({
  role,
  user,
  title,
  subtitle,
  actions,
  children,
}: {
  role: string;
  user: string;
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-background">
      <aside className="hidden w-64 shrink-0 flex-col bg-sidebar text-sidebar-foreground lg:flex">
        <div className="m-4 rounded-xl bg-card p-3">
          <img src={logo.url} alt="Lins Agroindustrial" className="h-10 w-auto" />
        </div>
        <p className="px-6 pt-4 text-xs font-semibold uppercase tracking-widest opacity-60">Navegação</p>
        <nav className="mt-2 flex flex-col gap-1 px-3">
          {nav.map((n) => (
            <Link
              key={n.to}
              to={n.to}
              className="rounded-lg px-3 py-2.5 text-sm font-medium opacity-80 transition hover:bg-sidebar-accent hover:opacity-100"
              activeProps={{ className: "bg-sidebar-accent !opacity-100 border-l-4 border-sidebar-primary" }}
            >
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="mt-auto border-t border-sidebar-border p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-sidebar-primary text-sm font-bold">
              {user.split(" ").map((p) => p[0]).slice(0, 2).join("")}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold">{user}</p>
              <p className="text-xs opacity-70">{role}</p>
            </div>
            <Link to="/" aria-label="Sair" className="opacity-70 hover:opacity-100">
              <LogOut className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </aside>
      <main className="flex-1">
        <header className="flex items-center justify-between border-b bg-card px-6 py-4 lg:px-10">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-primary">{title}</h1>
            {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
          </div>
          <div className="flex items-center gap-3">
            {actions}
            <button className="rounded-full p-2 text-muted-foreground hover:bg-muted" aria-label="Notificações">
              <Bell className="h-5 w-5" />
            </button>
          </div>
        </header>
        <div className="p-6 lg:p-10">{children}</div>
      </main>
    </div>
  );
}

export function StatCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border bg-card p-5 shadow-card">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-1 text-3xl font-extrabold text-primary">{value}</p>
      {hint && <p className="mt-1 text-xs font-medium text-accent">{hint}</p>}
    </div>
  );
}
