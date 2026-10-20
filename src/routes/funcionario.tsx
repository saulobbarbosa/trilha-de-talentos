import { createFileRoute } from "@tanstack/react-router";
import { Award, Download, Share2, CalendarDays, QrCode } from "lucide-react";
import logo from "@/assets/lins-logo.png.asset.json";
import { AppShell, StatCard } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export const Route = createFileRoute("/funcionario")({
  head: () => ({
    meta: [
      { title: "Meus Treinamentos e Certificados · Lins" },
      { name: "description", content: "Funcionário visualiza seus treinamentos e certificados digitais verificáveis." },
      { property: "og:title", content: "Meus Treinamentos e Certificados · Lins" },
      { property: "og:description", content: "Seus certificados digitais com código de verificação." },
    ],
  }),
  component: Funcionario,
});

const certs = [
  { name: "Liderança Situacional", date: "15/10/2026", hours: "8h", code: "LINS-7F3K-92QA" },
  { name: "NR-35 Trabalho em Altura", date: "22/08/2026", hours: "8h", code: "LINS-2B8M-41TX" },
  { name: "Brigada de Incêndio", date: "10/05/2026", hours: "16h", code: "LINS-9QW1-07LC" },
];

function Funcionario() {
  return (
    <AppShell role="Funcionário" user="Rafael Souza" title="Meus treinamentos" subtitle="Acompanhe suas turmas e certificados">
      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Certificados" value="3" />
        <StatCard label="Horas de capacitação" value="32h" hint="Meta anual: 40h" />
        <StatCard label="Próximo treinamento" value="28/10" hint="NR-12 Segurança em Máquinas" />
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-5">
        <div className="xl:col-span-2">
          <h2 className="mb-3 font-bold text-primary">Certificado em destaque</h2>
          <div className="relative overflow-hidden rounded-2xl border bg-card p-6 shadow-card">
            <div className="absolute inset-x-0 top-0 h-2 bg-brand-gradient" />
            <img src={logo.url} alt="Lins" className="h-8 w-auto" />
            <p className="mt-6 text-xs font-semibold uppercase tracking-[0.3em] text-accent">Certificado de conclusão</p>
            <p className="mt-2 text-sm text-muted-foreground">Certificamos que</p>
            <p className="text-2xl font-extrabold text-primary">Rafael Souza</p>
            <p className="mt-2 text-sm text-muted-foreground">concluiu o treinamento <b className="text-foreground">Liderança Situacional</b>, com carga horária de 8h, em 15/10/2026.</p>
            <div className="mt-6 flex items-end justify-between border-t pt-4">
              <div>
                <p className="text-xs text-muted-foreground">Código de verificação</p>
                <p className="font-mono font-bold text-primary">LINS-7F3K-92QA</p>
              </div>
              <QrCode className="h-14 w-14 text-primary" />
            </div>
          </div>
          <div className="mt-3 flex gap-2">
            <Button className="flex-1"><Download className="h-4 w-4" /> Baixar PDF</Button>
            <Button variant="outline"><Share2 className="h-4 w-4" /> Compartilhar</Button>
          </div>
        </div>

        <div className="space-y-6 xl:col-span-3">
          <div className="rounded-xl border bg-card shadow-card">
            <h2 className="border-b p-5 font-bold text-primary">Todos os certificados</h2>
            <div className="divide-y">
              {certs.map((c) => (
                <div key={c.code} className="flex items-center gap-4 p-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent-soft text-accent"><Award className="h-5 w-5" /></div>
                  <div className="flex-1">
                    <p className="font-medium">{c.name}</p>
                    <p className="text-xs text-muted-foreground">{c.date} · {c.hours} · <span className="font-mono">{c.code}</span></p>
                  </div>
                  <Button variant="ghost" size="icon" aria-label="Baixar"><Download className="h-4 w-4" /></Button>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-xl border bg-card shadow-card">
            <h2 className="border-b p-5 font-bold text-primary">Próximos treinamentos</h2>
            <div className="flex items-center gap-4 p-4">
              <CalendarDays className="h-5 w-5 text-accent" />
              <div className="flex-1">
                <p className="font-medium">NR-12 Segurança em Máquinas</p>
                <p className="text-xs text-muted-foreground">28/10/2026 · 08:00 · Sala 3 · Instrutor Carlos Mendes</p>
              </div>
              <Badge className="bg-accent text-accent-foreground">Confirmado</Badge>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
