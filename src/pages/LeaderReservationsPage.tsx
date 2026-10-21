import {
  CalendarDays,
  CheckCircle2,
  Clock,
  Loader2,
  MapPin,
  RefreshCw,
  TicketCheck,
  Users,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AppShell, EmptyState, SectionCard, StatGrid } from "@/components/AppShell";
import { StatusBadge } from "@/components/StatusBadge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { ApiError, apiRequest } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { LeaderReservationItem, LeaderReservationsData, TrainingRecord } from "@/lib/types";

type Feedback = { tone: "success" | "error"; message: string } | null;

export function LeaderReservationsPage() {
  const [data, setData] = useState<LeaderReservationsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [feedback, setFeedback] = useState<Feedback>(null);

  const [selectedTraining, setSelectedTraining] = useState<TrainingRecord | null>(null);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [dialogError, setDialogError] = useState("");

  const [cancelTarget, setCancelTarget] = useState<LeaderReservationItem | null>(null);
  const [cancelBusy, setCancelBusy] = useState(false);

  const load = useCallback(async () => {
    setLoadError("");
    try {
      const response = await apiRequest<LeaderReservationsData>("/api/leader/reservations");
      setData(response);
    } catch (error) {
      setLoadError(
        error instanceof ApiError ? error.message : "Não foi possível carregar as reservas.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const stats = useMemo(() => {
    if (!data) return [];
    const active = data.reservations.filter((reservation) => reservation.status === "ativa");
    return [
      { label: "Pessoas no time", value: String(data.team.length) },
      { label: "Reservas ativas", value: String(active.length) },
      {
        label: "Turmas com vagas",
        value: String(data.trainings.filter((training) => training.available > 0).length),
      },
    ];
  }, [data]);

  const teamById = useMemo(
    () => new Map((data?.team ?? []).map((member) => [member.id, member])),
    [data],
  );

  function openReserve(training: TrainingRecord) {
    setSelectedTraining(training);
    setSelectedIds([]);
    setDialogError("");
  }

  function toggleEmployee(employeeId: number, checked: boolean) {
    if (!selectedTraining) return;
    if (checked) {
      if (selectedIds.length >= selectedTraining.available) return;
      setSelectedIds((current) => [...current, employeeId]);
    } else {
      setSelectedIds((current) => current.filter((id) => id !== employeeId));
    }
  }

  async function reserve() {
    if (!selectedTraining || !selectedIds.length) return;
    setSubmitting(true);
    setDialogError("");
    try {
      const response = await apiRequest<{ ok: boolean; created: number }>(
        "/api/leader/reservations",
        {
          method: "POST",
          body: { training_id: selectedTraining.id, employee_ids: selectedIds },
        },
      );
      setFeedback({
        tone: "success",
        message: `${response.created} reserva(s) confirmada(s) para “${selectedTraining.title}”.`,
      });
      setSelectedTraining(null);
      setSelectedIds([]);
      await load();
    } catch (error) {
      setDialogError(
        error instanceof ApiError ? error.message : "Não foi possível concluir a reserva.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function confirmCancel() {
    if (!cancelTarget) return;
    setCancelBusy(true);
    setFeedback(null);
    try {
      await apiRequest<{ ok: boolean }>(`/api/leader/reservations/${cancelTarget.id}/cancel`, {
        method: "POST",
      });
      setFeedback({
        tone: "success",
        message: `Reserva de ${cancelTarget.employee_name} cancelada.`,
      });
      setCancelTarget(null);
      await load();
    } catch (error) {
      setFeedback({
        tone: "error",
        message: error instanceof ApiError ? error.message : "Não foi possível cancelar a reserva.",
      });
      setCancelTarget(null);
    } finally {
      setCancelBusy(false);
    }
  }

  const alreadyReserved = new Set(selectedTraining?.team_reserved_ids ?? []);

  return (
    <AppShell title="Reservas do time" subtitle="Vagas e confirmações" backTo="/lider">
      <div className="space-y-5">
        <div>
          <h2 className="text-xl font-extrabold text-primary">Reservar vagas</h2>
          <p className="text-sm text-muted-foreground">
            Escolha uma turma e selecione quem do seu time vai participar. Cada pessoa recebe um
            e-mail de confirmação.
          </p>
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

        {!loading && !loadError && data && <StatGrid stats={stats} />}

        {loading && (
          <div className="flex items-center justify-center gap-2 rounded-2xl border bg-card py-14 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Carregando reservas...
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
          <>
            {!data.team.length && (
              <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-900">
                <p className="text-sm font-semibold">Seu time ainda está vazio</p>
                <p className="text-xs leading-relaxed">
                  O RH precisa vincular funcionários ao seu perfil antes de reservar vagas.
                </p>
              </div>
            )}

            <SectionCard
              title="Turmas disponíveis"
              description="Somente treinamentos futuros com vagas abertas"
            >
              {data.trainings.length ? (
                <div className="divide-y">
                  {data.trainings.map((training) => {
                    const reservedInTeam = training.team_reserved_ids ?? [];
                    const full = training.available <= 0;
                    const allReserved =
                      data.team.length > 0 && reservedInTeam.length >= data.team.length;
                    const percent =
                      training.seats > 0 ? (training.reserved / training.seats) * 100 : 0;
                    return (
                      <div key={training.id} className="p-4 sm:p-5">
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div className="min-w-0 flex-1">
                            <p className="font-semibold leading-snug">{training.title}</p>
                            <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted-foreground sm:text-xs">
                              <span className="flex items-center gap-1">
                                <CalendarDays className="h-3.5 w-3.5" />
                                {formatDate(training.date)}
                              </span>
                              <span className="flex items-center gap-1">
                                <Clock className="h-3.5 w-3.5" />
                                {training.start_time}–{training.end_time}
                              </span>
                              <span className="flex items-center gap-1">
                                <MapPin className="h-3.5 w-3.5" />
                                {training.location}
                              </span>
                            </div>
                          </div>
                          <StatusBadge status={training.status} />
                        </div>

                        <div className="mt-3 flex items-center gap-3">
                          <div className="flex-1">
                            <div className="mb-1 flex justify-between text-[11px] text-muted-foreground">
                              <span>{training.instructor}</span>
                              <span className="font-semibold text-foreground">
                                {training.available} de {training.seats} vaga(s) livre(s)
                              </span>
                            </div>
                            <Progress value={Math.min(percent, 100)} className="h-1.5" />
                          </div>
                        </div>

                        {reservedInTeam.length > 0 && (
                          <p className="mt-2 text-[11px] text-muted-foreground">
                            Já reservado para:{" "}
                            <span className="font-medium text-foreground">
                              {reservedInTeam
                                .map((id) => teamById.get(id)?.name)
                                .filter(Boolean)
                                .join(", ")}
                            </span>
                          </p>
                        )}

                        <div className="mt-3">
                          <Button
                            size="sm"
                            onClick={() => openReserve(training)}
                            disabled={full || allReserved || !data.team.length}
                          >
                            <TicketCheck className="h-4 w-4" />
                            {full
                              ? "Turma lotada"
                              : allReserved
                                ? "Time já reservado"
                                : "Reservar time"}
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <EmptyState
                  icon={<CalendarDays className="h-5 w-5" />}
                  title="Nenhuma turma disponível"
                  description="O RH ainda não publicou turmas futuras com vagas."
                />
              )}
            </SectionCard>

            <SectionCard
              title="Reservas do time"
              description={`${data.reservations.filter((item) => item.status === "ativa").length} ativa(s)`}
            >
              {data.reservations.length ? (
                <div className="divide-y">
                  {data.reservations.map((reservation) => (
                    <div key={reservation.id} className="p-4 sm:p-5">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-semibold">{reservation.employee_name}</p>
                          <p className="font-semibold leading-snug text-primary">
                            {reservation.title}
                          </p>
                          <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
                            <span className="flex items-center gap-1">
                              <CalendarDays className="h-3.5 w-3.5" />
                              {formatDate(reservation.date)}
                            </span>
                            <span className="flex items-center gap-1">
                              <Clock className="h-3.5 w-3.5" />
                              {reservation.start_time}–{reservation.end_time}
                            </span>
                            <span className="flex items-center gap-1">
                              <MapPin className="h-3.5 w-3.5" />
                              {reservation.location}
                            </span>
                          </div>
                          {reservation.training_status === "cancelado" && (
                            <p className="mt-1 text-[11px] font-medium text-destructive">
                              A turma foi cancelada pelo RH.
                            </p>
                          )}
                        </div>
                        <StatusBadge status={reservation.status} />
                      </div>
                      {reservation.status === "ativa" && (
                        <div className="mt-3">
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-destructive hover:text-destructive"
                            onClick={() => setCancelTarget(reservation)}
                          >
                            <XCircle className="h-3.5 w-3.5" />
                            Cancelar reserva
                          </Button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState
                  icon={<Users className="h-5 w-5" />}
                  title="Nenhuma reserva registrada"
                  description="Ao reservar uma turma, as confirmações aparecerão aqui."
                />
              )}
            </SectionCard>
          </>
        )}
      </div>

      <Dialog
        open={Boolean(selectedTraining)}
        onOpenChange={(open) => {
          if (!open && !submitting) {
            setSelectedTraining(null);
            setSelectedIds([]);
          }
        }}
      >
        <DialogContent className="max-h-[92dvh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Reservar vagas</DialogTitle>
            <DialogDescription>
              {selectedTraining?.title} ·{" "}
              {selectedTraining ? formatDate(selectedTraining.date) : ""} ·{" "}
              {selectedTraining?.available} vaga(s) livre(s)
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-2">
            {data?.team.map((member) => {
              const reserved = alreadyReserved.has(member.id);
              const checked = selectedIds.includes(member.id);
              const limitReached =
                Boolean(selectedTraining) &&
                selectedIds.length >= (selectedTraining?.available ?? 0) &&
                !checked;
              return (
                <label
                  key={member.id}
                  className={`flex items-center gap-3 rounded-xl border p-3 ${
                    reserved ? "bg-muted/40" : "cursor-pointer hover:border-accent/50"
                  }`}
                >
                  <Checkbox
                    checked={reserved || checked}
                    disabled={reserved || limitReached || submitting}
                    onCheckedChange={(value) => toggleEmployee(member.id, value === true)}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold">{member.name}</p>
                    <p className="truncate text-[11px] text-muted-foreground">{member.email}</p>
                  </div>
                  {reserved && (
                    <span className="flex items-center gap-1 text-[10px] font-semibold text-accent">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Já reservado
                    </span>
                  )}
                </label>
              );
            })}
          </div>

          <p className="text-xs text-muted-foreground">
            {selectedIds.length} pessoa(s) selecionada(s). É possível reservar até{" "}
            {selectedTraining?.available} vaga(s) nesta turma.
          </p>

          {dialogError && (
            <div
              role="alert"
              className="rounded-xl bg-destructive/5 px-4 py-3 text-sm font-medium text-destructive"
            >
              {dialogError}
            </div>
          )}

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => setSelectedTraining(null)}
              disabled={submitting}
            >
              Voltar
            </Button>
            <Button onClick={() => void reserve()} disabled={!selectedIds.length || submitting}>
              {submitting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <TicketCheck className="h-4 w-4" />
              )}
              {submitting ? "Reservando..." : "Confirmar reservas"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog
        open={Boolean(cancelTarget)}
        onOpenChange={(open) => {
          if (!open && !cancelBusy) setCancelTarget(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Cancelar reserva?</AlertDialogTitle>
            <AlertDialogDescription>
              A reserva de {cancelTarget?.employee_name} em “{cancelTarget?.title}” será cancelada e
              a vaga voltará a ficar disponível.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={cancelBusy}>Voltar</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={cancelBusy}
              onClick={(event) => {
                event.preventDefault();
                void confirmCancel();
              }}
            >
              {cancelBusy ? "Cancelando..." : "Cancelar reserva"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AppShell>
  );
}
