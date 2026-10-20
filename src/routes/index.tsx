import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Briefcase, Users, GraduationCap, UserRound, ShieldCheck } from "lucide-react";
import logo from "@/assets/lins-logo.png.asset.json";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Entrar · Lins Treinamentos" },
      { name: "description", content: "Acesse a plataforma de treinamentos Lins como funcionário, RH, líder ou instrutor." },
      { property: "og:title", content: "Entrar · Lins Treinamentos" },
      { property: "og:description", content: "Acesse a plataforma de treinamentos Lins Agroindustrial." },
    ],
  }),
  component: Login,
});

const roles = [
  { id: "funcionario", label: "Funcionário", icon: UserRound, to: "/funcionario" },
  { id: "rh", label: "RH", icon: Briefcase, to: "/rh" },
  { id: "lider", label: "Líder", icon: Users, to: "/lider" },
  { id: "instrutor", label: "Instrutor", icon: GraduationCap, to: "/instrutor" },
] as const;

function Login() {
  const [role, setRole] = useState<(typeof roles)[number]>(roles[0]);
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <section className="relative hidden overflow-hidden bg-brand-gradient p-12 text-primary-foreground lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -right-24 -top-24 h-96 w-96 rounded-full bg-accent opacity-30 blur-3xl" />
        <p className="text-sm font-semibold uppercase tracking-[0.3em] opacity-80">Universidade Lins</p>
        <div className="relative max-w-md">
          <h2 className="text-5xl font-extrabold leading-tight">Capacitação que se comprova.</h2>
          <p className="mt-4 text-lg opacity-85">
            Agende treinamentos, registre presença com reconhecimento facial e emita certificados verificáveis.
          </p>
        </div>
        <div className="relative flex items-center gap-2 text-sm opacity-85">
          <ShieldCheck className="h-4 w-4" /> Certificados com código de verificação pública
        </div>
      </section>

      <section className="flex items-center justify-center p-6">
        <div className="w-full max-w-md">
          <img src={logo.url} alt="Lins Agroindustrial" className="mb-10 h-16 w-auto" />
          <h1 className="text-3xl font-bold text-primary">Bem-vindo</h1>
          <p className="mt-1 text-muted-foreground">Selecione seu perfil de acesso e entre.</p>

          <div className="mt-8 grid grid-cols-4 gap-2">
            {roles.map((r) => (
              <button
                key={r.id}
                onClick={() => setRole(r)}
                className={`flex flex-col items-center gap-2 rounded-xl border p-3 text-xs font-semibold transition ${
                  role.id === r.id
                    ? "border-accent bg-accent-soft text-primary"
                    : "bg-card text-muted-foreground hover:border-accent"
                }`}
              >
                <r.icon className="h-5 w-5" />
                {r.label}
              </button>
            ))}
          </div>

          <form className="mt-6 space-y-4" onSubmit={(e) => e.preventDefault()}>
            <div className="space-y-2">
              <Label htmlFor="mat">Matrícula ou e-mail</Label>
              <Input id="mat" placeholder="ex.: 104582" className="h-11" />
            </div>
            <div className="space-y-2">
              <div className="flex justify-between">
                <Label htmlFor="pw">Senha</Label>
                <a href="#" className="text-sm font-medium text-accent">Esqueci a senha</a>
              </div>
              <Input id="pw" type="password" placeholder="••••••••" className="h-11" />
            </div>
            <Button asChild className="h-11 w-full text-base">
              <Link to={role.to}>Entrar como {role.label}</Link>
            </Button>
          </form>

          <div className="mt-8 rounded-xl border border-dashed p-4 text-sm">
            <p className="font-semibold text-primary">Verificar um certificado</p>
            <div className="mt-2 flex gap-2">
              <Input placeholder="Código ex.: LINS-7F3K-92QA" />
              <Button variant="secondary">Verificar</Button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
