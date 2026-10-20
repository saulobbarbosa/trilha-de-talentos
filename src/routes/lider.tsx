import { createFileRoute } from "@tanstack/react-router";
import { CalendarDays, Clock, Users } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";

export const Route = createFileRoute("/lider")({
  head: () => ({
    meta: [
      { title: "Reservas da Equipe · Líder Lins" },
      { name: "description", content: "Líderes reservam vagas em treinamentos para o seu time." },
      { property: "og:title", content: "Reservas da Equipe · Líder Lins" },
      { property: "og:description", content: "Reserve vagas em treinamentos para sua equipe." },
    ],
  }),
  component: Lider,
});

const open = [
  { name: "NR-12 Segurança em Máquinas", date: "28/10", time: "08:00–17:00", free: 6, selected: true },
  { name: "Primeiros Socorros", date: "11/11", time: "13:00–17:00", free: 12, selected: false },
  { name: "Excel Avançado", date: "18/11", time: "09:00–12:00", free: 3, selected: false },
];
const team = [
  { name: "Rafael Souza", role: "Operador de Produção", status: "" },
  { name: "Beatriz Lima", role: "Técnica de Manutenção", status: "Reservado" },
  { name: "João Pedro Alves", role: "Operador de Produção", status: "" },
  { name: "Larissa Nunes", role: "Analista de Qualidade", status: "Certificado" },
  { name: "Thiago Rocha", role: "Mecânico", status: "" },
];

function Lider() {
  return (
    <AppShell role="Líder de Equipe" user="Marcos Oliveira" title="Reservar vagas" subtitle="Equipe Produção · Turno A">
      <div className="grid gap-6 xl:grid-cols-5">
        <div className="space-y-3 xl:col-span-2">
          <h2 className="font-bold text-primary">Treinamentos com vagas</h2>
          {open.map((t) => (
            <button key={t.name}
              className={`w-full rounded-xl border bg-card p-5 text-left shadow-card transition ${t.selected ? "border-accent ring-2 ring-accent" : "hover:border-accent"}`}>
              <p className="font-semibold">{t.name}</p>
              <div className="mt-2 flex flex-wrap gap-4 text-xs text-muted-foreground">
                <span className="flex items-center gap-1"><CalendarDays className="h-3.5 w-3.5" />{t.date}</span>
                <span className="flex items-center gap-1"><Clock className="h-3.5 w-3.5" />{t.time}</span>
                <span className="flex items-center gap-1 font-semibold text-accent"><Users className="h-3.5 w-3.5" />{t.free} vagas livres</span>
              </div>
            </button>
          ))}
        </div>

        <div className="rounded-xl border bg-card shadow-card xl:col-span-3">
          <div className="border-b p-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-accent">Selecionado</p>
            <h2 className="text-lg font-bold text-primary">NR-12 Segurança em Máquinas</h2>
            <p className="text-sm text-muted-foreground">Selecione os colaboradores · 6 vagas disponíveis</p>
          </div>
          <div className="divide-y">
            {team.map((m) => (
              <label key={m.name} className="flex cursor-pointer items-center gap-4 p-4 hover:bg-muted">
                <Checkbox disabled={!!m.status} defaultChecked={m.name === "Rafael Souza"} />
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-secondary text-sm font-bold text-primary">
                  {m.name.split(" ").map((p) => p[0]).slice(0, 2).join("")}
                </div>
                <div className="flex-1">
                  <p className="font-medium">{m.name}</p>
                  <p className="text-xs text-muted-foreground">{m.role}</p>
                </div>
                {m.status && <Badge variant="secondary">{m.status}</Badge>}
              </label>
            ))}
          </div>
          <div className="flex items-center justify-between border-t p-5">
            <p className="text-sm"><span className="font-bold text-primary">1</span> colaborador selecionado</p>
            <Button>Confirmar reserva</Button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
