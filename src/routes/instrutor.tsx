import { createFileRoute } from "@tanstack/react-router";
import { ScanFace, CheckCircle2, Clock, Camera } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

export const Route = createFileRoute("/instrutor")({
  head: () => ({
    meta: [
      { title: "Chamada com Reconhecimento Facial · Lins" },
      { name: "description", content: "Instrutor registra presença dos participantes com validação facial." },
      { property: "og:title", content: "Chamada com Reconhecimento Facial · Lins" },
      { property: "og:description", content: "Registro de presença antifraude por reconhecimento facial." },
    ],
  }),
  component: Instrutor,
});

const list = [
  { name: "Rafael Souza", time: "08:02", ok: true, score: 98 },
  { name: "Beatriz Lima", time: "08:04", ok: true, score: 96 },
  { name: "João Pedro Alves", time: "", ok: false, score: 0 },
  { name: "Larissa Nunes", time: "08:07", ok: true, score: 99 },
  { name: "Thiago Rocha", time: "", ok: false, score: 0 },
  { name: "Fernanda Dias", time: "", ok: false, score: 0 },
];

function Instrutor() {
  return (
    <AppShell role="Instrutor" user="Carlos Mendes" title="Chamada" subtitle="NR-12 Segurança em Máquinas · 28/10/2026 · Sala 3"
      actions={<Button variant="outline">Encerrar chamada</Button>}>
      <div className="grid gap-6 xl:grid-cols-5">
        <div className="xl:col-span-3">
          <div className="relative aspect-video overflow-hidden rounded-2xl bg-sidebar">
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="relative h-64 w-52 rounded-[45%] border-4 border-accent">
                <span className="absolute -left-1 -top-1 h-8 w-8 rounded-tl-xl border-l-4 border-t-4 border-primary-foreground" />
                <span className="absolute -right-1 -top-1 h-8 w-8 rounded-tr-xl border-r-4 border-t-4 border-primary-foreground" />
                <span className="absolute -bottom-1 -left-1 h-8 w-8 rounded-bl-xl border-b-4 border-l-4 border-primary-foreground" />
                <span className="absolute -bottom-1 -right-1 h-8 w-8 rounded-br-xl border-b-4 border-r-4 border-primary-foreground" />
                <ScanFace className="absolute inset-0 m-auto h-20 w-20 text-primary-foreground opacity-40" />
                <div className="absolute inset-x-2 top-1/2 h-0.5 animate-pulse bg-accent" />
              </div>
            </div>
            <div className="absolute left-4 top-4 flex items-center gap-2 rounded-full bg-card px-3 py-1 text-xs font-semibold text-primary">
              <span className="h-2 w-2 animate-pulse rounded-full bg-destructive" /> Câmera ativa
            </div>
            <div className="absolute inset-x-4 bottom-4 rounded-xl bg-card p-4">
              <p className="text-xs text-muted-foreground">Posicione o rosto do participante dentro da moldura</p>
              <p className="font-semibold text-primary">Aguardando reconhecimento…</p>
            </div>
          </div>
          <div className="mt-4 flex gap-3">
            <Button className="flex-1"><Camera className="h-4 w-4" /> Capturar e validar</Button>
            <Button variant="outline">Registro manual</Button>
          </div>
        </div>

        <div className="rounded-xl border bg-card shadow-card xl:col-span-2">
          <div className="border-b p-5">
            <div className="flex justify-between text-sm"><span className="font-bold text-primary">Presenças</span><span className="font-semibold">3 / 6</span></div>
            <Progress value={50} className="mt-2" />
          </div>
          <div className="divide-y">
            {list.map((p) => (
              <div key={p.name} className="flex items-center gap-3 p-4">
                {p.ok ? <CheckCircle2 className="h-5 w-5 text-accent" /> : <Clock className="h-5 w-5 text-muted-foreground" />}
                <div className="flex-1">
                  <p className="font-medium">{p.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {p.ok ? `Validado às ${p.time} · similaridade ${p.score}%` : "Pendente"}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
