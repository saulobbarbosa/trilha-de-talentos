import {
  Award,
  Briefcase,
  CalendarDays,
  CheckCircle2,
  Clock,
  Download,
  Loader2,
  Mail,
  MapPin,
  QrCode,
  RefreshCw,
  ScanFace,
  Users,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";

import { AppShell, EmptyState, SectionCard, StatGrid } from "@/components/AppShell";
import { StatusBadge } from "@/components/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { useAuth } from "@/lib/auth";
import { ApiError, apiRequest } from "@/lib/api";
import { formatDate, formatShortDate, greeting, initials, roleLabel } from "@/lib/format";
import { Link } from "@/lib/router";
import type { HomeData, Role, TrainingSummary } from "@/lib/types";

const PAGE_CONFIG: Record<Role, { title: string; subtitle: string }> = {
  rh: { title: "Painel do RH", subtitle: "Treinamentos, vagas e indicadores" },
  lider: { title: "Minha equipe", subtitle: "Pessoas e reservas do seu time" },
  instrutor: { title: "Minhas chamadas", subtitle: "Turmas atribuídas a você" },
  funcionario: { title: "Meus treinamentos", subtitle: "Próximas turmas e certificados" },
};

export function DashboardPage({ role }: { role: Role }) {
  const { user } = useAuth();
  const [data, setData] = useState<HomeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    apiRequest<HomeData>("/api/home", { signal: controller.signal })
      .then(setData)
      .catch((err) => {
        if (controller.signal.aborted) return;
        setError(err instanceof ApiError ? err.message : "Não foi possível carregar o painel.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [role]);

  const config = PAGE_CONFIG[role];
  const firstName = user?.name.split(" ")[0] ?? "";

  return (
    <AppShell title={config.title} subtitle={config.subtitle}>
      <div className="space-y-5">
        <section className="relative overflow-hidden rounded-2xl bg-brand-gradient p-5 text-white shadow-card">
          <div className="absolute -right-14 -top-14 h-40 w-40 rounded-full bg-accent/30 blur-2xl" />
          <p className="text-sm text-white/75">{greeting()},</p>
          <h2 className="text-2xl font-extrabold">{firstName}</h2>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-white/15 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide">
              {roleLabel(role)}
            </span>
            <span className="rounded-full bg-white/10 px-3 py-1 text-[11px] text-white/80">
              {new Date().toLocaleDateString("pt-BR", { day: "2-digit", month: "long" })}
            </span>
          </div>
        </section>

        {loading && (
          <div className="flex items-center justify-center gap-2 rounded-2xl border bg-card py-14 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Carregando painel...
          </div>
        )}

        {!loading && error && (
          <div className="rounded-2xl border bg-card p-6 text-center">
            <p className="font-semibold text-destructive">{error}</p>
            <Button variant="outline" className="mt-4" onClick={() => window.location.reload()}>
              <RefreshCw className="h-4 w-4" />
              Recarregar
            </Button>
          </div>
        )}

        {!loading && data && (
          <>
            <StatGrid stats={data.stats} />
            {role === "rh" && <RHContent data={data} />}
            {role === "lider" && <LeaderContent data={data} />}
            {role === "instrutor" && <InstructorContent data={data} />}
            {role === "funcionario" && (
              <EmployeeContent data={data} faceEnrolled={Boolean(user?.face_enrolled)} />
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}

function TrainingList({
  trainings,
  emptyTitle,
  emptyDescription,
  showAttendance = false,
  callBase,
}: {
  trainings: TrainingSummary[];
  emptyTitle: string;
  emptyDescription: string;
  showAttendance?: boolean;
  callBase?: string;
}) {
  if (!trainings.length) {
    return (
      <EmptyState
        icon={<CalendarDays className="h-5 w-5" />}
        title={emptyTitle}
        description={emptyDescription}
      />
    );
  }
  return (
    <div className="divide-y">
      {trainings.map((training) => {
        const percent =
          training.seats > 0 ? Math.min(100, (training.reserved / training.seats) * 100) : 0;
        return (
          <div key={training.id} className="p-4 sm:p-5">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <p className="font-semibold leading-snug text-foreground">{training.title}</p>
                <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted-foreground sm:text-xs">
                  <span className="flex items-center gap-1">
                    <CalendarDays className="h-3.5 w-3.5" />
                    {formatDate(training.date)} · {training.start_time}
                  </span>
                  <span className="flex items-center gap-1">
                    <MapPin className="h-3.5 w-3.5" />
                    {training.location}
                  </span>
                </div>
              </div>
              <StatusBadge status={training.status} />
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <div className="min-w-[150px] flex-1">
                <div className="mb-1 flex justify-between gap-3 text-[11px] text-muted-foreground">
                  <span>{training.instructor}</span>
                  <span className="font-semibold text-foreground">
                    {training.reserved}/{training.seats} vagas
                  </span>
                </div>
                <Progress value={percent} className="h-1.5" />
              </div>
              {showAttendance && (
                <span className="flex items-center gap-1 rounded-full bg-accent-soft px-2.5 py-1 text-[10px] font-bold text-primary">
                  <CheckCircle2 className="h-3 w-3 text-accent" />
                  {training.attendance_count ?? 0} presenças
                </span>
              )}
              {showAttendance && Boolean(training.certificate_count) && (
                <span className="flex items-center gap-1 rounded-full bg-secondary px-2.5 py-1 text-[10px] font-bold text-primary">
                  <Award className="h-3 w-3 text-accent" />
                  {training.certificate_count} certificados
                </span>
              )}
              {callBase && (
                <Button asChild size="sm" variant="outline" className="w-full sm:w-auto">
                  <Link to={`${callBase}/${training.id}`}>
                    <ScanFace className="h-4 w-4" />
                    {training.status === "cancelado" || training.status === "concluido"
                      ? "Ver chamada"
                      : "Abrir chamada"}
                  </Link>
                </Button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function QuickAction({
  title,
  description,
  icon,
  to,
  badge,
}: {
  title: string;
  description: string;
  icon: ReactNode;
  to?: string;
  badge?: string;
}) {
  const content = (
    <div className="flex h-full items-start gap-3 rounded-2xl border bg-card p-4 shadow-card transition hover:border-accent">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-primary">
        {icon}
      </div>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-semibold text-primary">{title}</p>
          {badge && (
            <span className="rounded-full bg-muted px-2 py-0.5 text-[9px] font-bold uppercase text-muted-foreground">
              {badge}
            </span>
          )}
        </div>
        <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{description}</p>
      </div>
    </div>
  );
  return to ? <Link to={to}>{content}</Link> : content;
}

function RHContent({ data }: { data: HomeData }) {
  return (
    <>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <QuickAction
          title="Pessoas"
          description="Crie acessos, defina líderes e redefina senhas."
          icon={<Users className="h-5 w-5" />}
          to="/rh/pessoas"
        />
        <QuickAction
          title="Treinamentos"
          description="Cadastre turmas, vagas, datas e instrutores."
          icon={<Briefcase className="h-5 w-5" />}
          to="/rh/trainings"
        />
        <QuickAction
          title="Caixa de saída"
          description="Confira os e-mails gerados pelo sistema."
          icon={<Mail className="h-5 w-5" />}
          to="/rh/outbox"
          badge="DEV"
        />
        <QuickAction
          title="Verificar certificado"
          description="Abra a página pública de validação por código."
          icon={<QrCode className="h-5 w-5" />}
          to="/verificar"
        />
      </div>
      <SectionCard
        title="Turmas cadastradas"
        description={`${data.trainings?.length ?? 0} treinamentos recentes`}
      >
        <TrainingList
          trainings={data.trainings ?? []}
          emptyTitle="Nenhum treinamento cadastrado"
          emptyDescription="As turmas criadas pelo RH aparecerão aqui."
        />
      </SectionCard>
    </>
  );
}

function LeaderContent({ data }: { data: HomeData }) {
  return (
    <>
      <SectionCard
        title="Turmas com vagas"
        description="Reservas para o seu time"
        action={
          <Button asChild size="sm" variant="secondary">
            <Link to="/lider/reservas">Gerenciar reservas</Link>
          </Button>
        }
      >
        <TrainingList
          trainings={(data.trainings ?? []).filter((training) => training.available > 0)}
          emptyTitle="Nenhuma turma aberta"
          emptyDescription="Quando o RH publicar novas turmas com vagas, elas aparecerão aqui."
        />
      </SectionCard>
      <SectionCard title="Meu time" description={`${data.team?.length ?? 0} pessoas vinculadas`}>
        {data.team?.length ? (
          <div className="divide-y">
            {data.team.map((member) => (
              <div key={member.id} className="flex items-center gap-3 p-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-secondary text-sm font-bold text-primary">
                  {initials(member.name)}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold">{member.name}</p>
                  <p className="truncate text-[11px] text-muted-foreground">{member.email}</p>
                </div>
                <Badge
                  variant="secondary"
                  className={
                    member.face_enrolled
                      ? "bg-accent-soft text-primary"
                      : "bg-muted text-muted-foreground"
                  }
                >
                  {member.face_enrolled ? "Face ok" : "Face pendente"}
                </Badge>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<Users className="h-5 w-5" />}
            title="Seu time ainda está vazio"
            description="Os funcionários criados por você aparecerão nesta lista."
          />
        )}
      </SectionCard>
    </>
  );
}

function InstructorContent({ data }: { data: HomeData }) {
  return (
    <SectionCard title="Turmas atribuídas" description="Presenças e chamadas">
      <TrainingList
        trainings={data.trainings ?? []}
        emptyTitle="Nenhuma turma atribuída"
        emptyDescription="O RH vinculará você aos treinamentos que você ministra."
        showAttendance
        callBase="/instrutor/chamadas"
      />
    </SectionCard>
  );
}

function EmployeeContent({ data, faceEnrolled }: { data: HomeData; faceEnrolled: boolean }) {
  const reservations = data.reservations ?? [];
  const certificates = data.certificates ?? [];

  return (
    <>
      {!faceEnrolled && (
        <div className="flex flex-col gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-900 sm:flex-row sm:items-center">
          <div className="flex items-start gap-3">
            <Clock className="mt-0.5 h-5 w-5 shrink-0" />
            <div>
              <p className="text-sm font-semibold">Cadastro facial pendente</p>
              <p className="text-xs leading-relaxed">
                Faça o cadastro guiado agora para agilizar sua presença nos treinamentos.
              </p>
            </div>
          </div>
          <Button asChild size="sm" className="w-full shrink-0 sm:ml-auto sm:w-auto">
            <Link to="/cadastro-facial">
              <ScanFace className="h-4 w-4" />
              Cadastrar
            </Link>
          </Button>
        </div>
      )}

      <SectionCard title="Próximos treinamentos" description="Turmas reservadas para você">
        {reservations.length ? (
          <div className="divide-y">
            {reservations.map((reservation) => (
              <div key={reservation.id} className="flex items-start gap-3 p-4">
                <div className="flex h-11 w-11 shrink-0 flex-col items-center justify-center rounded-xl bg-accent-soft text-primary">
                  <span className="text-[10px] font-bold uppercase leading-none">
                    {formatShortDate(reservation.date).split("/")[1]}
                  </span>
                  <span className="text-base font-extrabold leading-tight">
                    {formatShortDate(reservation.date).split("/")[0]}
                  </span>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold leading-snug">{reservation.title}</p>
                  <p className="mt-1 text-[11px] text-muted-foreground">
                    {reservation.start_time} · {reservation.location} · {reservation.instructor}
                  </p>
                </div>
                <StatusBadge status={reservation.status} />
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<CalendarDays className="h-5 w-5" />}
            title="Nenhuma turma reservada"
            description="Seu líder reservará vagas nos treinamentos do time."
          />
        )}
      </SectionCard>

      <SectionCard title="Meus certificados" description="Documentos emitidos após a conclusão">
        {certificates.length ? (
          <div className="divide-y">
            {certificates.map((certificate) => (
              <div key={certificate.id} className="flex items-center gap-3 p-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent">
                  <Award className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold">{certificate.title}</p>
                  <p className="truncate font-mono text-[10px] text-muted-foreground">
                    {certificate.code}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <a
                    href={`/api/certificates/verify/${encodeURIComponent(certificate.code)}/pdf`}
                    download
                    className="inline-flex items-center gap-1 text-xs font-semibold text-primary"
                  >
                    <Download className="h-3.5 w-3.5" />
                    PDF
                  </a>
                  <Link
                    to={`/verificar/${certificate.code}`}
                    className="text-xs font-semibold text-accent"
                  >
                    Abrir
                  </Link>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<Award className="h-5 w-5" />}
            title="Nenhum certificado ainda"
            description="Após a chamada e o encerramento do treinamento, seu certificado digital aparece aqui."
          />
        )}
      </SectionCard>

      <SectionCard title="Acesso rápido">
        <div className="grid gap-3 p-4 sm:grid-cols-2">
          <QuickAction
            title="Verificar certificado"
            description="Valide um código na página pública."
            icon={<QrCode className="h-5 w-5" />}
            to="/verificar"
          />
          <QuickAction
            title="Cadastro facial"
            description={
              faceEnrolled
                ? "Seu modelo facial está ativo. Revise ou refaça quando precisar."
                : "Consentimento LGPD e captura guiada do seu rosto."
            }
            icon={<ScanFace className="h-5 w-5" />}
            to="/cadastro-facial"
            badge={faceEnrolled ? "Ativo" : "Pendente"}
          />
        </div>
      </SectionCard>
    </>
  );
}
