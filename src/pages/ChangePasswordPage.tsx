import { Check, Loader2, LockKeyhole, ShieldCheck } from "lucide-react";
import { useMemo, useState, type FormEvent } from "react";

import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { useRouter } from "@/lib/router";

const rules = [
  { label: "Pelo menos 8 caracteres", test: (value: string) => value.length >= 8 },
  { label: "Uma letra maiúscula", test: (value: string) => /[A-Z]/.test(value) },
  { label: "Uma letra minúscula", test: (value: string) => /[a-z]/.test(value) },
  { label: "Um número", test: (value: string) => /\d/.test(value) },
];

export function ChangePasswordPage() {
  const { user, changePassword } = useAuth();
  const { navigate } = useRouter();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const checks = useMemo(() => rules.map((rule) => ({ ...rule, ok: rule.test(next) })), [next]);
  const allRulesOk = checks.every((rule) => rule.ok);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (!allRulesOk) {
      setError("A nova senha ainda não atende aos requisitos mínimos.");
      return;
    }
    if (next !== confirm) {
      setError("A confirmação não confere com a nova senha.");
      return;
    }
    setSubmitting(true);
    try {
      const data = await changePassword(current, next);
      navigate(data.next_step, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Não foi possível alterar a senha.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppShell title="Primeiro acesso" subtitle="Troca de senha obrigatória">
      <div className="mx-auto max-w-lg space-y-4">
        <div className="rounded-2xl bg-brand-gradient p-5 text-white shadow-card">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-full bg-white/15">
              <LockKeyhole className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm text-white/75">Olá, {user?.name.split(" ")[0]}</p>
              <p className="font-bold">Crie uma senha pessoal para continuar</p>
            </div>
          </div>
          <p className="mt-4 text-xs leading-relaxed text-white/80">
            A senha temporária enviada por e-mail deve ser substituída antes de acessar as demais
            áreas do sistema.
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="space-y-5 rounded-2xl border bg-card p-5 shadow-card"
        >
          <div className="space-y-2">
            <Label htmlFor="current">Senha atual / temporária</Label>
            <Input
              id="current"
              type="password"
              autoComplete="current-password"
              className="h-12 text-base"
              value={current}
              onChange={(event) => setCurrent(event.target.value)}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="new">Nova senha</Label>
            <Input
              id="new"
              type="password"
              autoComplete="new-password"
              className="h-12 text-base"
              value={next}
              onChange={(event) => setNext(event.target.value)}
              required
            />
            <ul className="mt-2 grid grid-cols-1 gap-1 text-xs sm:grid-cols-2">
              {checks.map((rule) => (
                <li
                  key={rule.label}
                  className={`flex items-center gap-1.5 ${rule.ok ? "text-accent" : "text-muted-foreground"}`}
                >
                  <Check className={`h-3.5 w-3.5 ${rule.ok ? "opacity-100" : "opacity-40"}`} />
                  {rule.label}
                </li>
              ))}
            </ul>
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirm">Confirmar nova senha</Label>
            <Input
              id="confirm"
              type="password"
              autoComplete="new-password"
              className="h-12 text-base"
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
              required
            />
          </div>

          {error && (
            <div
              role="alert"
              className="rounded-xl bg-destructive/5 px-4 py-3 text-sm font-medium text-destructive"
            >
              {error}
            </div>
          )}

          <Button type="submit" className="h-12 w-full text-base" disabled={submitting}>
            {submitting ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <ShieldCheck className="h-5 w-5" />
            )}
            {submitting ? "Salvando..." : "Salvar nova senha"}
          </Button>
        </form>

        <p className="px-2 text-center text-[11px] leading-relaxed text-muted-foreground">
          A nova senha não pode ser igual à senha temporária. Senhas são armazenadas com hash
          Argon2.
        </p>
      </div>
    </AppShell>
  );
}
