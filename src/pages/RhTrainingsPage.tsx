import {
  CalendarDays,
  Clock,
  Loader2,
  MapPin,
  Pencil,
  Plus,
  RefreshCw,
  Trash2,
  Users,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

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
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, apiRequest } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { RhOptions, TrainingRecord, TrainingsData } from "@/lib/types";

function nextDay(): string {
  const now = new Date();
  now.setDate(now.getDate() + 1);
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

const EMPTY_FORM = {
  title: "",
  description: "",
  instructor_id: "",
  date: nextDay(),
  start_time: "08:00",
  end_time: "12:00",
  location: "",
  seats: "20",
  workload_hours: "4",
};

type TrainingForm = typeof EMPTY_FORM;
type Feedback = { tone: "success" | "error"; message: string } | null;

export function RhTrainingsPage() {
  const [trainings, setTrainings] = useState<TrainingRecord[]>([]);
  const [options, setOptions] = useState<RhOptions>({ leaders: [], instructors: [] });
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [statusFilter, setStatusFilter] = useState("todos");
  const [feedback, setFeedback] = useState<Feedback>(null);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<TrainingRecord | null>(null);
  const [form, setForm] = useState<TrainingForm>(EMPTY_FORM);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  const [cancelTarget, setCancelTarget] = useState<TrainingRecord | null>(null);
  const [cancelReason, setCancelReason] = useState("");
  const [cancelBusy, setCancelBusy] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState<TrainingRecord | null>(null);

  const load = useCallback(async () => {
    setLoadError("");
    try {
      const [trainingData, optionsData] = await Promise.all([
        apiRequest<TrainingsData>("/api/rh/trainings"),
        apiRequest<RhOptions>("/api/rh/options"),
      ]);
      setTrainings(trainingData.trainings);
      setOptions(optionsData);
    } catch (error) {
      setLoadError(
        error instanceof ApiError ? error.message : "Não foi possível carregar os treinamentos.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(
    () =>
      statusFilter === "todos"
        ? trainings
        : trainings.filter((training) => training.status === statusFilter),
    [statusFilter, trainings],
  );

  const stats = useMemo(
    () => [
      { label: "Treinamentos", value: String(trainings.length) },
      {
        label: "Agendados",
        value: String(trainings.filter((training) => training.status === "agendado").length),
      },
      {
        label: "Reservas ativas",
        value: String(trainings.reduce((total, training) => total + training.reserved, 0)),
      },
      {
        label: "Vagas livres",
        value: String(
          trainings
            .filter((training) => training.status === "agendado")
            .reduce((total, training) => total + training.available, 0),
        ),
      },
    ],
    [trainings],
  );

  function openCreate() {
    setEditing(null);
    setForm(EMPTY_FORM);
    setFormError("");
    setDialogOpen(true);
  }

  function openEdit(training: TrainingRecord) {
    setEditing(training);
    setForm({
      title: training.title,
      description: training.description,
      instructor_id: String(training.instructor_id),
      date: training.date,
      start_time: training.start_time,
      end_time: training.end_time,
      location: training.location,
      seats: String(training.seats),
      workload_hours: String(training.workload_hours),
    });
    setFormError("");
    setDialogOpen(true);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError("");
    if (!form.instructor_id) {
      setFormError("Selecione o instrutor da turma.");
      return;
    }
    if (form.end_time <= form.start_time) {
      setFormError("O horário de término deve ser posterior ao início.");
      return;
    }

    setSaving(true);
    try {
      const payload = {
        title: form.title,
        description: form.description,
        instructor_id: Number(form.instructor_id),
        date: form.date,
        start_time: form.start_time,
        end_time: form.end_time,
        location: form.location,
        seats: Number(form.seats),
        workload_hours: Number(form.workload_hours),
      };

      if (editing) {
        const response = await apiRequest<{ training: TrainingRecord }>(
          `/api/rh/trainings/${editing.id}`,
          { method: "PATCH", body: payload },
        );
        setFeedback({
          tone: "success",
          message: `“${response.training.title}” foi atualizado.`,
        });
      } else {
        const response = await apiRequest<{ training: TrainingRecord }>("/api/rh/trainings", {
          method: "POST",
          body: payload,
        });
        setFeedback({
          tone: "success",
          message: `“${response.training.title}” foi criado.`,
        });
      }
      setDialogOpen(false);
      await load();
    } catch (error) {
      setFormError(
        error instanceof ApiError ? error.message : "Não foi possível salvar o treinamento.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function confirmCancel() {
    if (!cancelTarget) return;
    setCancelBusy(true);
    setFeedback(null);
    try {
      const response = await apiRequest<{
        cancelled_reservations: number;
        training: TrainingRecord;
      }>(`/api/rh/trainings/${cancelTarget.id}/cancel`, {
        method: "POST",
        body: { reason: cancelReason.trim() || null },
      });
      setFeedback({
        tone: "success",
        message: `Treinamento cancelado. ${response.cancelled_reservations} reserva(s) foram canceladas.`,
      });
      setCancelTarget(null);
      setCancelReason("");
      await load();
    } catch (error) {
      setFeedback({
        tone: "error",
        message:
          error instanceof ApiError ? error.message : "Não foi possível cancelar o treinamento.",
      });
    } finally {
      setCancelBusy(false);
    }
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    setFeedback(null);
    try {
      await apiRequest<{ ok: boolean }>(`/api/rh/trainings/${deleteTarget.id}`, {
        method: "DELETE",
      });
      setFeedback({ tone: "success", message: `“${deleteTarget.title}” foi excluído.` });
      setDeleteTarget(null);
      await load();
    } catch (error) {
      setFeedback({
        tone: "error",
        message: error instanceof ApiError ? error.message : "Não foi possível excluir.",
      });
      setDeleteTarget(null);
    }
  }

  return (
    <AppShell title="Treinamentos" subtitle="Turmas, vagas e instrutores" backTo="/rh">
      <div className="space-y-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-xl font-extrabold text-primary">Agenda de capacitação</h2>
            <p className="text-sm text-muted-foreground">
              Crie turmas, ajuste vagas e cancele quando necessário.
            </p>
          </div>
          <Button onClick={openCreate} className="h-11 w-full sm:w-auto">
            <Plus className="h-4 w-4" />
            Novo treinamento
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
            Carregando treinamentos...
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
            title="Turmas cadastradas"
            description={`${filtered.length} treinamento(s) exibido(s)`}
            action={
              <NativeSelect
                aria-label="Filtrar por status"
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
                className="h-9 w-auto min-w-[140px] text-xs"
              >
                <option value="todos">Todos os status</option>
                <option value="agendado">Agendados</option>
                <option value="em_andamento">Em andamento</option>
                <option value="concluido">Concluídos</option>
                <option value="cancelado">Cancelados</option>
              </NativeSelect>
            }
          >
            {filtered.length ? (
              <div className="divide-y">
                {filtered.map((training) => {
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

                      {training.description && (
                        <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
                          {training.description}
                        </p>
                      )}

                      <div className="mt-3">
                        <div className="mb-1 flex flex-wrap items-center justify-between gap-2 text-[11px] text-muted-foreground">
                          <span>
                            {training.instructor || "Instrutor não definido"} ·{" "}
                            {training.workload_hours}h
                          </span>
                          <span className="flex items-center gap-1 font-semibold text-foreground">
                            <Users className="h-3.5 w-3.5" />
                            {training.reserved}/{training.seats} reservas
                          </span>
                        </div>
                        <Progress value={Math.min(percent, 100)} className="h-1.5" />
                      </div>

                      <div className="mt-3 flex flex-wrap gap-2">
                        {training.can_edit && (
                          <Button size="sm" variant="outline" onClick={() => openEdit(training)}>
                            <Pencil className="h-3.5 w-3.5" />
                            Editar
                          </Button>
                        )}
                        {training.can_cancel && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setCancelTarget(training);
                              setCancelReason("");
                            }}
                          >
                            <XCircle className="h-3.5 w-3.5" />
                            Cancelar
                          </Button>
                        )}
                        {training.can_delete && (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-destructive hover:text-destructive"
                            onClick={() => setDeleteTarget(training)}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                            Excluir
                          </Button>
                        )}
                        {!training.can_edit && !training.can_delete && (
                          <span className="self-center text-[11px] text-muted-foreground">
                            Histórico preservado para auditoria.
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <EmptyState
                icon={<CalendarDays className="h-5 w-5" />}
                title="Nenhum treinamento neste filtro"
                description="Crie uma turma ou altere o filtro de status."
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
            <DialogTitle>{editing ? "Editar treinamento" : "Novo treinamento"}</DialogTitle>
            <DialogDescription>
              {editing && editing.reserved > 0
                ? `Esta turma já tem ${editing.reserved} reserva(s). As vagas não podem ficar abaixo disso.`
                : "Defina data, horário, local, instrutor e número de vagas."}
            </DialogDescription>
          </DialogHeader>
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <Label htmlFor="training-title">Título</Label>
              <Input
                id="training-title"
                value={form.title}
                onChange={(event) => setForm({ ...form, title: event.target.value })}
                className="h-11"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="training-description">Descrição</Label>
              <Textarea
                id="training-description"
                value={form.description}
                onChange={(event) => setForm({ ...form, description: event.target.value })}
                rows={3}
                maxLength={2000}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="training-instructor">Instrutor</Label>
              <NativeSelect
                id="training-instructor"
                value={form.instructor_id}
                onChange={(event) => setForm({ ...form, instructor_id: event.target.value })}
                required
              >
                <option value="">Selecione um instrutor</option>
                {options.instructors.map((instructor) => (
                  <option key={instructor.id} value={instructor.id}>
                    {instructor.name}
                  </option>
                ))}
              </NativeSelect>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="training-date">Data</Label>
                <Input
                  id="training-date"
                  type="date"
                  value={form.date}
                  onChange={(event) => setForm({ ...form, date: event.target.value })}
                  className="h-11"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="training-location">Local</Label>
                <Input
                  id="training-location"
                  value={form.location}
                  onChange={(event) => setForm({ ...form, location: event.target.value })}
                  className="h-11"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="training-start">Início</Label>
                <Input
                  id="training-start"
                  type="time"
                  value={form.start_time}
                  onChange={(event) => setForm({ ...form, start_time: event.target.value })}
                  className="h-11"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="training-end">Término</Label>
                <Input
                  id="training-end"
                  type="time"
                  value={form.end_time}
                  onChange={(event) => setForm({ ...form, end_time: event.target.value })}
                  className="h-11"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="training-seats">Vagas</Label>
                <Input
                  id="training-seats"
                  type="number"
                  min={1}
                  max={500}
                  value={form.seats}
                  onChange={(event) => setForm({ ...form, seats: event.target.value })}
                  className="h-11"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="training-workload">Carga horária</Label>
                <Input
                  id="training-workload"
                  type="number"
                  min={0.5}
                  max={100}
                  step={0.5}
                  value={form.workload_hours}
                  onChange={(event) => setForm({ ...form, workload_hours: event.target.value })}
                  className="h-11"
                  required
                />
              </div>
            </div>
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
                {saving ? "Salvando..." : editing ? "Salvar alterações" : "Criar treinamento"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog
        open={Boolean(cancelTarget)}
        onOpenChange={(open) => {
          if (!open && !cancelBusy) setCancelTarget(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancelar treinamento</DialogTitle>
            <DialogDescription>
              A turma “{cancelTarget?.title}” será cancelada e as reservas ativas serão canceladas
              automaticamente. Os participantes serão avisados na caixa de saída.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="cancel-reason">Motivo (opcional)</Label>
            <Textarea
              id="cancel-reason"
              value={cancelReason}
              onChange={(event) => setCancelReason(event.target.value)}
              rows={3}
              maxLength={300}
              placeholder="Ex.: mudança de agenda do instrutor"
            />
          </div>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setCancelTarget(null)} disabled={cancelBusy}>
              Voltar
            </Button>
            <Button
              variant="destructive"
              onClick={() => void confirmCancel()}
              disabled={cancelBusy}
            >
              {cancelBusy ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <XCircle className="h-4 w-4" />
              )}
              {cancelBusy ? "Cancelando..." : "Confirmar cancelamento"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir treinamento?</AlertDialogTitle>
            <AlertDialogDescription>
              “{deleteTarget?.title}” será removido permanentemente. Esta ação só é permitida quando
              não há reservas ou presenças.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Voltar</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => void confirmDelete()}
            >
              Excluir
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AppShell>
  );
}
