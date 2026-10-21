import {
  Check,
  Copy,
  KeyRound,
  Loader2,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  UserCheck,
  UserX,
  Users,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import { AppShell, EmptyState, SectionCard, StatGrid } from "@/components/AppShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { ApiError, apiRequest } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { copyText } from "@/lib/clipboard";
import { formatDateTime, initials, roleLabel } from "@/lib/format";
import type { PeopleData, PersonRecord, RhOptions, Role } from "@/lib/types";

const EMPTY_FORM = {
  name: "",
  email: "",
  role: "funcionario" as Role,
  leader_id: "",
  is_active: true,
};

type PersonForm = typeof EMPTY_FORM;

type Feedback = { tone: "success" | "error"; message: string } | null;

type Credential = {
  name: string;
  email: string;
  password: string;
};

export function RhPeoplePage() {
  const { user } = useAuth();
  const [people, setPeople] = useState<PersonRecord[]>([]);
  const [options, setOptions] = useState<RhOptions>({ leaders: [], instructors: [] });
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [search, setSearch] = useState("");
  const [feedback, setFeedback] = useState<Feedback>(null);
  const [actionId, setActionId] = useState<number | null>(null);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<PersonRecord | null>(null);
  const [form, setForm] = useState<PersonForm>(EMPTY_FORM);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  const [credential, setCredential] = useState<Credential | null>(null);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    setLoadError("");
    try {
      const [peopleData, optionsData] = await Promise.all([
        apiRequest<PeopleData>("/api/rh/people"),
        apiRequest<RhOptions>("/api/rh/options"),
      ]);
      setPeople(peopleData.people);
      setOptions(optionsData);
    } catch (error) {
      setLoadError(
        error instanceof ApiError ? error.message : "Não foi possível carregar as pessoas.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return people;
    return people.filter(
      (person) =>
        person.name.toLowerCase().includes(term) ||
        person.email.toLowerCase().includes(term) ||
        roleLabel(person.role).toLowerCase().includes(term),
    );
  }, [people, search]);

  const stats = useMemo(
    () => [
      { label: "Pessoas", value: String(people.length) },
      { label: "Ativas", value: String(people.filter((person) => person.is_active).length) },
      {
        label: "Líderes",
        value: String(
          people.filter((person) => person.role === "lider" && person.is_active).length,
        ),
      },
      {
        label: "Instrutores",
        value: String(
          people.filter((person) => person.role === "instrutor" && person.is_active).length,
        ),
      },
    ],
    [people],
  );

  function openCreate() {
    setEditing(null);
    setForm(EMPTY_FORM);
    setFormError("");
    setDialogOpen(true);
  }

  function openEdit(person: PersonRecord) {
    setEditing(person);
    setForm({
      name: person.name,
      email: person.email,
      role: person.role,
      leader_id: person.leader_id ? String(person.leader_id) : "",
      is_active: person.is_active,
    });
    setFormError("");
    setDialogOpen(true);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError("");
    if (form.role === "funcionario" && !form.leader_id) {
      setFormError("Selecione o líder responsável pelo funcionário.");
      return;
    }

    setSaving(true);
    try {
      const payload = {
        name: form.name,
        email: form.email,
        role: form.role,
        leader_id: form.role === "funcionario" ? Number(form.leader_id) : null,
        ...(editing ? { is_active: form.is_active } : {}),
      };

      if (editing) {
        const response = await apiRequest<{ person: PersonRecord }>(
          `/api/rh/people/${editing.id}`,
          { method: "PATCH", body: payload },
        );
        setFeedback({ tone: "success", message: `${response.person.name} foi atualizado.` });
      } else {
        const response = await apiRequest<{ person: PersonRecord; temporary_password: string }>(
          "/api/rh/people",
          { method: "POST", body: payload },
        );
        setCredential({
          name: response.person.name,
          email: response.person.email,
          password: response.temporary_password,
        });
        setFeedback({
          tone: "success",
          message: `${response.person.name} foi cadastrado. A senha temporária foi gerada.`,
        });
      }
      setDialogOpen(false);
      await load();
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "Não foi possível salvar a pessoa.");
    } finally {
      setSaving(false);
    }
  }

  async function resetPassword(person: PersonRecord) {
    setActionId(person.id);
    setFeedback(null);
    try {
      const response = await apiRequest<{ ok: boolean; temporary_password: string }>(
        `/api/rh/people/${person.id}/reset-password`,
        { method: "POST" },
      );
      setCredential({
        name: person.name,
        email: person.email,
        password: response.temporary_password,
      });
      setFeedback({
        tone: "success",
        message: `Nova senha temporária gerada para ${person.name}.`,
      });
      await load();
    } catch (error) {
      setFeedback({
        tone: "error",
        message: error instanceof ApiError ? error.message : "Não foi possível redefinir a senha.",
      });
    } finally {
      setActionId(null);
    }
  }

  async function toggleActive(person: PersonRecord) {
    setActionId(person.id);
    setFeedback(null);
    try {
      await apiRequest<{ person: PersonRecord }>(`/api/rh/people/${person.id}`, {
        method: "PATCH",
        body: { is_active: !person.is_active },
      });
      setFeedback({
        tone: "success",
        message: `${person.name} foi ${person.is_active ? "desativado" : "ativado"}.`,
      });
      await load();
    } catch (error) {
      setFeedback({
        tone: "error",
        message: error instanceof ApiError ? error.message : "Não foi possível alterar o acesso.",
      });
    } finally {
      setActionId(null);
    }
  }

  async function copyCredential() {
    if (!credential) return;
    const copiedOk = await copyText(`${credential.email}\n${credential.password}`);
    setCopied(copiedOk);
    if (copiedOk) window.setTimeout(() => setCopied(false), 2500);
  }

  return (
    <AppShell title="Pessoas" subtitle="Acessos, equipes e perfis" backTo="/rh">
      <div className="space-y-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-xl font-extrabold text-primary">Gestão de pessoas</h2>
            <p className="text-sm text-muted-foreground">
              Cadastre funcionários, líderes e instrutores. A senha inicial é temporária.
            </p>
          </div>
          <Button onClick={openCreate} className="h-11 w-full sm:w-auto">
            <Plus className="h-4 w-4" />
            Nova pessoa
          </Button>
        </div>

        {feedback && (
          <div
            role="status"
            className={`rounded-2xl border px-4 py-3 text-sm font-medium ${
              feedback.tone === "success"
                ? "border-accent/30 bg-accent-soft text-primary"
                : "border-destructive/20 bg-destructive/5 text-destructive"
            }`}
          >
            {feedback.message}
          </div>
        )}

        {!loading && !loadError && <StatGrid stats={stats} />}

        {loading && (
          <div className="flex items-center justify-center gap-2 rounded-2xl border bg-card py-14 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Carregando pessoas...
          </div>
        )}

        {!loading && loadError && (
          <div className="rounded-2xl border bg-card p-6 text-center">
            <p className="font-semibold text-destructive">{loadError}</p>
            <Button variant="outline" className="mt-4" onClick={() => void load()}>
              <RefreshCw className="h-4 w-4" />
              Tentar novamente
            </Button>
          </div>
        )}

        {!loading && !loadError && (
          <SectionCard
            title="Cadastro"
            description={`${filtered.length} pessoa(s) exibida(s)`}
            action={
              <div className="relative w-full max-w-[220px]">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  aria-label="Buscar pessoa"
                  placeholder="Buscar..."
                  className="h-9 pl-9"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                />
              </div>
            }
          >
            {filtered.length ? (
              <div className="divide-y">
                {filtered.map((person) => (
                  <div key={person.id} className="p-4 sm:p-5">
                    <div className="flex items-start gap-3">
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-secondary text-sm font-bold text-primary">
                        {initials(person.name)}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <p className="font-semibold leading-snug">{person.name}</p>
                          <Badge variant="secondary" className="bg-secondary text-primary">
                            {roleLabel(person.role)}
                          </Badge>
                          {!person.is_active && (
                            <Badge
                              variant="secondary"
                              className="bg-destructive/10 text-destructive"
                            >
                              Inativo
                            </Badge>
                          )}
                          {person.must_change_password && person.is_active && (
                            <Badge variant="secondary" className="bg-amber-100 text-amber-800">
                              Senha temporária
                            </Badge>
                          )}
                        </div>
                        <p className="truncate text-xs text-muted-foreground">{person.email}</p>
                        <p className="mt-1 text-[11px] text-muted-foreground">
                          {person.role === "funcionario"
                            ? `Líder: ${person.leader_name ?? "não definido"}`
                            : "Sem vínculo de equipe"}
                          {person.last_login_at
                            ? ` · Último acesso: ${formatDateTime(person.last_login_at)}`
                            : " · Nunca acessou"}
                        </p>
                      </div>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => openEdit(person)}
                        disabled={actionId === person.id}
                      >
                        <Pencil className="h-3.5 w-3.5" />
                        Editar
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => void resetPassword(person)}
                        disabled={!person.is_active || actionId === person.id}
                      >
                        {actionId === person.id ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <KeyRound className="h-3.5 w-3.5" />
                        )}
                        Nova senha
                      </Button>
                      <Button
                        size="sm"
                        variant={person.is_active ? "ghost" : "secondary"}
                        onClick={() => void toggleActive(person)}
                        disabled={actionId === person.id || person.id === user?.id}
                        className={
                          person.is_active ? "text-destructive hover:text-destructive" : ""
                        }
                      >
                        {person.is_active ? (
                          <UserX className="h-3.5 w-3.5" />
                        ) : (
                          <UserCheck className="h-3.5 w-3.5" />
                        )}
                        {person.is_active ? "Desativar" : "Ativar"}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                icon={<Users className="h-5 w-5" />}
                title={search ? "Nenhuma pessoa encontrada" : "Nenhuma pessoa cadastrada"}
                description={
                  search
                    ? "Tente outro nome, e-mail ou perfil."
                    : "Use “Nova pessoa” para criar o primeiro acesso."
                }
              />
            )}
          </SectionCard>
        )}
      </div>

      <Dialog
        open={dialogOpen}
        onOpenChange={(open) => {
          if (!saving) setDialogOpen(open);
        }}
      >
        <DialogContent className="max-h-[92dvh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editing ? "Editar pessoa" : "Nova pessoa"}</DialogTitle>
            <DialogDescription>
              {editing
                ? "Alterações de perfil são bloqueadas quando há equipe ou turmas vinculadas."
                : "Uma senha temporária será gerada e registrada na caixa de saída."}
            </DialogDescription>
          </DialogHeader>
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <Label htmlFor="person-name">Nome completo</Label>
              <Input
                id="person-name"
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                className="h-11"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="person-email">E-mail corporativo</Label>
              <Input
                id="person-email"
                type="email"
                inputMode="email"
                autoCapitalize="none"
                value={form.email}
                onChange={(event) => setForm({ ...form, email: event.target.value })}
                className="h-11"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="person-role">Perfil de acesso</Label>
              <NativeSelect
                id="person-role"
                value={form.role}
                onChange={(event) =>
                  setForm({ ...form, role: event.target.value as Role, leader_id: "" })
                }
              >
                <option value="funcionario">Funcionário</option>
                <option value="lider">Líder</option>
                <option value="instrutor">Instrutor</option>
                <option value="rh">RH</option>
              </NativeSelect>
            </div>
            {form.role === "funcionario" && (
              <div className="space-y-2">
                <Label htmlFor="person-leader">Líder responsável</Label>
                <NativeSelect
                  id="person-leader"
                  value={form.leader_id}
                  onChange={(event) => setForm({ ...form, leader_id: event.target.value })}
                  required
                >
                  <option value="">Selecione um líder</option>
                  {options.leaders.map((leader) => (
                    <option key={leader.id} value={leader.id}>
                      {leader.name}
                    </option>
                  ))}
                </NativeSelect>
                {!options.leaders.length && (
                  <p className="text-xs text-destructive">
                    Cadastre um líder antes de criar funcionários.
                  </p>
                )}
              </div>
            )}
            {editing && (
              <label className="flex items-center gap-2 rounded-xl border px-3 py-3 text-sm">
                <input
                  type="checkbox"
                  className="h-4 w-4 accent-[var(--primary)]"
                  checked={form.is_active}
                  onChange={(event) => setForm({ ...form, is_active: event.target.checked })}
                />
                Conta ativa para login
              </label>
            )}
            {formError && (
              <div
                role="alert"
                className="rounded-xl bg-destructive/5 px-4 py-3 text-sm font-medium text-destructive"
              >
                {formError}
              </div>
            )}
            <DialogFooter className="gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setDialogOpen(false)}
                disabled={saving}
              >
                Cancelar
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                {saving ? "Salvando..." : editing ? "Salvar alterações" : "Cadastrar pessoa"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(credential)} onOpenChange={(open) => !open && setCredential(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Senha temporária gerada</DialogTitle>
            <DialogDescription>
              Entregue estas credenciais para {credential?.name}. No primeiro acesso, será
              obrigatório criar uma senha pessoal.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1">
              <Label>E-mail</Label>
              <Input readOnly value={credential?.email ?? ""} className="h-11 bg-muted/40" />
            </div>
            <div className="space-y-1">
              <Label>Senha temporária</Label>
              <Input
                readOnly
                value={credential?.password ?? ""}
                className="h-11 bg-muted/40 font-mono"
              />
            </div>
            <p className="text-[11px] leading-relaxed text-muted-foreground">
              A senha também foi registrada na caixa de saída de e-mails. Ela não é exibida
              novamente depois que esta janela for fechada.
            </p>
          </div>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setCredential(null)}>
              Fechar
            </Button>
            <Button onClick={() => void copyCredential()}>
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              {copied ? "Copiado" : "Copiar dados"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}
