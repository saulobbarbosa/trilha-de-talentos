import { createFileRoute } from "@tanstack/react-router";
import { Plus, Pencil, Trash2, Search, CalendarDays, MapPin } from "lucide-react";
import { AppShell, StatCard } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

export const Route = createFileRoute("/rh")({
  head: () => ({
    meta: [
      { title: "Gestão de Treinamentos · RH Lins" },
      { name: "description", content: "Cadastro e gerenciamento de treinamentos, vagas e datas pelo RH." },
      { property: "og:title", content: "Gestão de Treinamentos · RH Lins" },
      { property: "og:description", content: "Cadastre treinamentos com vagas e datas." },
    ],
  }),
  component: RH,
});

const trainings = [
  { name: "NR-12 Segurança em Máquinas", date: "28/10/2026", place: "Sala 3 · Unidade Lins", instructor: "Carlos Mendes", seats: 30, used: 24, status: "Aberto" },
  { name: "Boas Práticas de Fabricação", date: "04/11/2026", place: "Auditório", instructor: "Ana Ribeiro", seats: 50, used: 50, status: "Lotado" },
  { name: "Primeiros Socorros", date: "11/11/2026", place: "Sala 1", instructor: "Paulo Silva", seats: 20, used: 8, status: "Aberto" },
  { name: "Liderança Situacional", date: "15/10/2026", place: "Online", instructor: "Marina Costa", seats: 25, used: 25, status: "Concluído" },
];

function RH() {
  return (
    <AppShell role="Recursos Humanos" user="Juliana Prado" title="Treinamentos" subtitle="Cadastre e gerencie turmas, vagas e datas"
      actions={<Button><Plus className="h-4 w-4" /> Novo treinamento</Button>}>
      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="Treinamentos ativos" value="12" hint="+3 este mês" />
        <StatCard label="Vagas ofertadas" value="420" />
        <StatCard label="Taxa de ocupação" value="78%" hint="+6% vs. setembro" />
        <StatCard label="Certificados emitidos" value="1.284" />
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-3">
        <div className="rounded-xl border bg-card shadow-card xl:col-span-2">
          <div className="flex items-center justify-between gap-4 border-b p-5">
            <h2 className="font-bold text-primary">Turmas cadastradas</h2>
            <div className="relative w-64">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Buscar treinamento" className="pl-9" />
            </div>
          </div>
          <div className="divide-y">
            {trainings.map((t) => (
              <div key={t.name} className="flex flex-wrap items-center gap-4 p-5">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="font-semibold">{t.name}</p>
                    <Badge variant={t.status === "Aberto" ? "default" : "secondary"}
                      className={t.status === "Aberto" ? "bg-accent text-accent-foreground" : ""}>{t.status}</Badge>
                  </div>
                  <div className="mt-1 flex flex-wrap gap-4 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1"><CalendarDays className="h-3.5 w-3.5" />{t.date}</span>
                    <span className="flex items-center gap-1"><MapPin className="h-3.5 w-3.5" />{t.place}</span>
                    <span>Instrutor: {t.instructor}</span>
                  </div>
                </div>
                <div className="w-40">
                  <div className="mb-1 flex justify-between text-xs"><span>Vagas</span><span className="font-semibold">{t.used}/{t.seats}</span></div>
                  <Progress value={(t.used / t.seats) * 100} />
                </div>
                <div className="flex gap-1">
                  <Button variant="ghost" size="icon" aria-label="Editar"><Pencil className="h-4 w-4" /></Button>
                  <Button variant="ghost" size="icon" aria-label="Excluir"><Trash2 className="h-4 w-4" /></Button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <form className="space-y-4 rounded-xl border bg-card p-5 shadow-card" onSubmit={(e) => e.preventDefault()}>
          <h2 className="font-bold text-primary">Cadastrar treinamento</h2>
          <div className="space-y-2"><Label>Título</Label><Input placeholder="Nome do treinamento" /></div>
          <div className="space-y-2"><Label>Descrição</Label><Textarea placeholder="Objetivos e conteúdo programático" /></div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2"><Label>Data</Label><Input type="date" /></div>
            <div className="space-y-2"><Label>Horário</Label><Input type="time" /></div>
            <div className="space-y-2"><Label>Vagas</Label><Input type="number" placeholder="30" /></div>
            <div className="space-y-2"><Label>Carga horária</Label><Input placeholder="8h" /></div>
          </div>
          <div className="space-y-2"><Label>Local</Label><Input placeholder="Sala / unidade / online" /></div>
          <div className="space-y-2"><Label>Instrutor</Label><Input placeholder="Selecionar instrutor" /></div>
          <Button className="w-full">Salvar treinamento</Button>
        </form>
      </div>
    </AppShell>
  );
}
