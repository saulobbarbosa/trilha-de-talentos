import {
  ArrowLeft,
  BadgeCheck,
  Download,
  Loader2,
  Search,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";

import { Brand } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError, apiRequest } from "@/lib/api";
import { formatDate, formatDateTime } from "@/lib/format";
import { Link, useRouter } from "@/lib/router";
import type { CertificateVerification } from "@/lib/types";

export function VerifyPage({ code }: { code: string | undefined }) {
  const { navigate } = useRouter();
  const [query, setQuery] = useState(code ?? "");
  const [result, setResult] = useState<CertificateVerification | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(Boolean(code));

  useEffect(() => {
    setQuery(code ?? "");
  }, [code]);

  useEffect(() => {
    if (!code) {
      setResult(null);
      setError("");
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setResult(null);
    apiRequest<CertificateVerification>(`/api/certificates/verify/${encodeURIComponent(code)}`, {
      signal: controller.signal,
    })
      .then(setResult)
      .catch((err) => {
        if (controller.signal.aborted) return;
        setError(
          err instanceof ApiError ? err.message : "Não foi possível verificar o certificado.",
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [code]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = query.trim().toUpperCase();
    if (normalized) navigate(`/verificar/${encodeURIComponent(normalized)}`);
  }

  return (
    <div className="min-h-dvh bg-background">
      <header className="border-b bg-card">
        <div className="mx-auto flex w-full max-w-2xl items-center justify-between gap-3 px-4 py-3">
          <Link to="/" className="flex items-center gap-2 text-sm font-semibold text-primary">
            <ArrowLeft className="h-4 w-4" />
            Voltar
          </Link>
          <Brand compact />
        </div>
      </header>

      <main className="mx-auto w-full max-w-2xl px-4 py-8">
        <div className="rounded-2xl bg-brand-gradient p-5 text-white shadow-card">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-full bg-white/15">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-lg font-extrabold">Verificação de certificado</h1>
              <p className="text-xs text-white/80">Consulta pública, sem necessidade de login.</p>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="mt-5 rounded-2xl border bg-card p-4 shadow-card">
          <label htmlFor="certificate-code" className="text-sm font-semibold text-primary">
            Código de verificação
          </label>
          <div className="mt-2 flex gap-2">
            <Input
              id="certificate-code"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="LINS-XXXXX-XXXXX-XXXXX"
              className="h-12 min-w-0 flex-1 font-mono text-sm uppercase"
              autoCapitalize="characters"
              spellCheck={false}
            />
            <Button type="submit" className="h-12 shrink-0" disabled={loading}>
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Search className="h-4 w-4" />
              )}
              <span className="hidden sm:inline">Verificar</span>
            </Button>
          </div>
          <p className="mt-2 text-[11px] text-muted-foreground">
            O código aparece no PDF e no certificado digital do participante.
          </p>
        </form>

        {loading && (
          <div className="mt-5 flex items-center justify-center gap-2 rounded-2xl border bg-card py-12 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Consultando certificado...
          </div>
        )}

        {!loading && error && (
          <div className="mt-5 rounded-2xl border border-destructive/20 bg-card p-5 text-center shadow-card">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
              <ShieldAlert className="h-6 w-6" />
            </div>
            <p className="mt-3 font-bold text-destructive">Certificado não confirmado</p>
            <p className="mt-1 text-sm text-muted-foreground">{error}</p>
          </div>
        )}

        {!loading && result && (
          <div className="mt-5 overflow-hidden rounded-2xl border bg-card shadow-card">
            <div className="h-1.5 bg-brand-gradient" />
            <div className="p-5 text-center">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-accent-soft text-accent">
                <BadgeCheck className="h-8 w-8" />
              </div>
              <p className="mt-3 text-lg font-extrabold text-primary">Certificado válido</p>
              <p className="text-xs text-muted-foreground">Emitido pela Universidade Lins</p>
            </div>
            <dl className="space-y-3 border-t p-5 text-sm">
              <div>
                <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                  Participante
                </dt>
                <dd className="mt-0.5 font-semibold text-foreground">{result.holder_name}</dd>
              </div>
              <div>
                <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                  Treinamento
                </dt>
                <dd className="mt-0.5 font-semibold text-foreground">{result.training_title}</dd>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                    Data
                  </dt>
                  <dd className="mt-0.5 font-semibold text-foreground">
                    {formatDate(result.training_date)}
                  </dd>
                </div>
                <div>
                  <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                    Carga horária
                  </dt>
                  <dd className="mt-0.5 font-semibold text-foreground">{result.workload_hours}h</dd>
                </div>
              </div>
              <div>
                <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                  Código
                </dt>
                <dd className="mt-0.5 font-mono text-xs font-semibold text-primary">
                  {result.code}
                </dd>
              </div>
              <div>
                <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                  Emitido em
                </dt>
                <dd className="mt-0.5 text-xs text-muted-foreground">
                  {formatDateTime(result.issued_at)}
                </dd>
              </div>
            </dl>
            <div className="border-t p-5">
              <div className="flex flex-col items-center gap-4 sm:flex-row">
                <img
                  src={`/api/certificates/verify/${encodeURIComponent(result.code)}/qr.png`}
                  alt={`QR Code de verificação do certificado ${result.code}`}
                  className="h-32 w-32 shrink-0 rounded-xl border bg-white p-2"
                  loading="lazy"
                />
                <div className="min-w-0 flex-1 text-center sm:text-left">
                  <p className="text-sm font-semibold text-primary">Valide pelo QR Code</p>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                    Aponte a câmera para abrir esta verificação ou baixe o certificado em PDF.
                  </p>
                  <Button asChild className="mt-3 w-full sm:w-auto">
                    <a
                      href={`/api/certificates/verify/${encodeURIComponent(result.code)}/pdf`}
                      download
                    >
                      <Download className="h-4 w-4" />
                      Baixar PDF
                    </a>
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
