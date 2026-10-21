import { ArrowRight, Loader2, QrCode, ShieldCheck } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Brand } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { useRouter } from "@/lib/router";

export function LoginPage() {
  const { login } = useAuth();
  const { navigate } = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const data = await login(email.trim(), password);
      navigate(data.next_step, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Não foi possível entrar. Tente novamente.");
    } finally {
      setSubmitting(false);
    }
  }

  function handleVerify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = code.trim().toUpperCase();
    if (normalized) navigate(`/verificar/${encodeURIComponent(normalized)}`);
  }

  return (
    <div className="min-h-dvh bg-background lg:grid lg:grid-cols-[1.05fr_1fr]">
      <section className="relative overflow-hidden bg-brand-gradient px-6 pb-20 pt-8 text-primary-foreground lg:flex lg:flex-col lg:justify-between lg:p-12 lg:pb-12">
        <div className="absolute -right-20 -top-24 h-72 w-72 rounded-full bg-accent opacity-30 blur-3xl" />
        <div className="absolute -bottom-24 -left-16 h-64 w-64 rounded-full bg-primary-foreground opacity-10 blur-3xl" />
        <div className="relative">
          <Brand variant="light" />
          <p className="mt-8 max-w-md text-2xl font-extrabold leading-tight sm:text-3xl lg:mt-0 lg:text-5xl">
            Capacitação que se comprova.
          </p>
          <p className="mt-3 max-w-md text-sm leading-relaxed text-white/85 sm:text-base lg:mt-4 lg:text-lg">
            Agende treinamentos, registre presença com reconhecimento facial e emita certificados
            verificáveis.
          </p>
        </div>
        <div className="relative mt-6 hidden items-center gap-2 text-sm text-white/80 lg:flex">
          <ShieldCheck className="h-4 w-4" />
          Certificados com código de verificação pública
        </div>
      </section>

      <section className="relative -mt-10 px-4 pb-10 lg:mt-0 lg:flex lg:items-center lg:justify-center lg:px-10">
        <div className="mx-auto w-full max-w-md rounded-3xl border bg-card p-6 shadow-card sm:p-8 lg:border-0 lg:bg-transparent lg:p-0 lg:shadow-none">
          <div className="mb-6 hidden lg:block">
            <Brand />
          </div>
          <h1 className="text-2xl font-extrabold text-primary sm:text-3xl">Bem-vindo</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Entre com seu e-mail corporativo. Seu perfil de acesso vem da conta.
          </p>

          <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <Label htmlFor="email">E-mail</Label>
              <Input
                id="email"
                type="email"
                inputMode="email"
                autoComplete="username"
                autoCapitalize="none"
                spellCheck={false}
                placeholder="voce@lins.com.br"
                className="h-12 text-base"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Senha</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                placeholder="Sua senha"
                className="h-12 text-base"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </div>

            {error && (
              <div
                role="alert"
                className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm font-medium text-destructive"
              >
                {error}
              </div>
            )}

            <Button type="submit" className="h-12 w-full text-base" disabled={submitting}>
              {submitting ? <Loader2 className="h-5 w-5 animate-spin" /> : null}
              {submitting ? "Entrando..." : "Entrar"}
              {!submitting && <ArrowRight className="h-4 w-4" />}
            </Button>
          </form>

          <div className="mt-7 rounded-2xl border border-dashed p-4">
            <div className="flex items-center gap-2 text-primary">
              <QrCode className="h-4 w-4 text-accent" />
              <p className="text-sm font-semibold">Verificar um certificado</p>
            </div>
            <form className="mt-3 flex gap-2" onSubmit={handleVerify}>
              <Input
                aria-label="Código do certificado"
                placeholder="LINS-XXXXX-XXXXX-XXXXX"
                className="h-11 min-w-0 flex-1 font-mono text-xs uppercase sm:text-sm"
                value={code}
                onChange={(event) => setCode(event.target.value)}
                autoCapitalize="characters"
                spellCheck={false}
              />
              <Button variant="secondary" className="h-11 shrink-0" type="submit">
                Verificar
              </Button>
            </form>
          </div>

          <p className="mt-6 text-center text-[11px] leading-relaxed text-muted-foreground">
            Acesso restrito · Universidade Lins · Dados tratados conforme a LGPD
          </p>
        </div>
      </section>
    </div>
  );
}
