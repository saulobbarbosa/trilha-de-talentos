import {
  AlertTriangle,
  Check,
  CheckCircle2,
  Copy,
  Loader2,
  Mail,
  RefreshCw,
  Search,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AppShell, EmptyState, SectionCard, StatGrid } from "@/components/AppShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError, apiRequest } from "@/lib/api";
import { copyText } from "@/lib/clipboard";
import { formatDateTime } from "@/lib/format";
import type { OutboxData } from "@/lib/types";

export function RhOutboxPage() {
  const [data, setData] = useState<OutboxData | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [search, setSearch] = useState("");
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoadError("");
    try {
      const response = await apiRequest<OutboxData>("/api/rh/outbox");
      setData(response);
    } catch (error) {
      setLoadError(
        error instanceof ApiError ? error.message : "Não foi possível carregar a caixa de saída.",
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
    if (!term) return data?.emails ?? [];
    return (data?.emails ?? []).filter(
      (email) =>
        email.recipient.toLowerCase().includes(term) || email.subject.toLowerCase().includes(term),
    );
  }, [data, search]);

  const stats = useMemo(() => {
    const emails = data?.emails ?? [];
    return [
      { label: "Mensagens", value: String(emails.length) },
      { label: "Enviadas", value: String(emails.filter((email) => email.sent).length) },
      { label: "Pendentes", value: String(emails.filter((email) => !email.sent).length) },
    ];
  }, [data]);

  async function copyMessage(id: number, recipient: string, subject: string, body: string) {
    const copied = await copyText(`Para: ${recipient}\nAssunto: ${subject}\n\n${body}`);
    if (copied) {
      setCopiedId(id);
      window.setTimeout(() => setCopiedId(null), 2500);
    }
  }

  return (
    <AppShell title="Caixa de saída" subtitle="Mensagens geradas pelo sistema" backTo="/rh">
      <div className="space-y-5">
        <div>
          <h2 className="text-xl font-extrabold text-primary">Caixa de saída</h2>
          <p className="text-sm text-muted-foreground">
            Acessos, reservas e cancelamentos geram mensagens registradas aqui para conferência.
          </p>
        </div>

        {data && (
          <div className="flex items-start gap-3 rounded-2xl border border-dashed bg-card p-4 text-sm">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-accent" />
            <div>
              <p className="font-semibold text-primary">
                {data.smtp_enabled ? "SMTP configurado" : "Modo de desenvolvimento"}
              </p>
              <p className="text-xs leading-relaxed text-muted-foreground">
                {data.smtp_enabled
                  ? "O sistema tenta enviar cada mensagem imediatamente. Falhas ficam registradas abaixo."
                  : "Nenhum e-mail real é enviado enquanto o SMTP não estiver configurado. Use esta caixa para copiar as credenciais e conferir as notificações."}
              </p>
            </div>
          </div>
        )}

        {!loading && !loadError && <StatGrid stats={stats} />}

        {loading && (
          <div className="flex items-center justify-center gap-2 rounded-2xl border bg-card py-14 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Carregando mensagens...
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

        {!loading && !loadError && data && (
          <SectionCard
            title="Mensagens"
            description={`${filtered.length} mensagem(ns) exibida(s)`}
            action={
              <div className="relative w-full max-w-[220px]">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  aria-label="Buscar mensagem"
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
                {filtered.map((message) => (
                  <details key={message.id} className="group">
                    <summary className="flex cursor-pointer list-none items-start gap-3 p-4 transition hover:bg-muted/30 sm:p-5">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-primary">
                        <Mail className="h-4 w-4" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-semibold text-primary">
                          {message.subject}
                        </p>
                        <p className="truncate text-xs text-muted-foreground">
                          Para: {message.recipient}
                        </p>
                        <p className="text-[10px] text-muted-foreground">
                          {formatDateTime(message.created_at)}
                        </p>
                      </div>
                      <Badge
                        variant="secondary"
                        className={
                          message.sent
                            ? "shrink-0 bg-accent-soft text-primary"
                            : message.error
                              ? "shrink-0 bg-destructive/10 text-destructive"
                              : "shrink-0 bg-muted text-muted-foreground"
                        }
                      >
                        {message.sent ? (
                          <span className="flex items-center gap-1">
                            <CheckCircle2 className="h-3 w-3" />
                            Enviado
                          </span>
                        ) : message.error ? (
                          "Falhou"
                        ) : (
                          "Registrado"
                        )}
                      </Badge>
                    </summary>
                    <div className="border-t bg-muted/20 p-4 sm:p-5">
                      {message.error && (
                        <p className="mb-3 rounded-xl bg-destructive/5 px-3 py-2 text-xs text-destructive">
                          {message.error}
                        </p>
                      )}
                      <pre className="whitespace-pre-wrap break-words font-sans text-sm leading-relaxed text-foreground">
                        {message.body}
                      </pre>
                      <Button
                        size="sm"
                        variant="outline"
                        className="mt-3"
                        onClick={() =>
                          void copyMessage(
                            message.id,
                            message.recipient,
                            message.subject,
                            message.body,
                          )
                        }
                      >
                        {copiedId === message.id ? (
                          <Check className="h-3.5 w-3.5" />
                        ) : (
                          <Copy className="h-3.5 w-3.5" />
                        )}
                        {copiedId === message.id ? "Copiado" : "Copiar mensagem"}
                      </Button>
                    </div>
                  </details>
                ))}
              </div>
            ) : (
              <EmptyState
                icon={<Mail className="h-5 w-5" />}
                title={search ? "Nenhuma mensagem encontrada" : "Caixa de saída vazia"}
                description={
                  search
                    ? "Tente outro destinatário ou assunto."
                    : "Cadastros de pessoas e movimentações de reservas gerarão mensagens aqui."
                }
              />
            )}
          </SectionCard>
        )}
      </div>
    </AppShell>
  );
}
