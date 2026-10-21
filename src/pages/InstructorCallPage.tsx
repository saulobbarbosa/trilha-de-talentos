import {
  AlertTriangle,
  Award,
  CalendarDays,
  Camera,
  CheckCircle2,
  Clock,
  ImageUp,
  Loader2,
  MapPin,
  RefreshCw,
  ScanFace,
  Search,
  ShieldCheck,
  Trash2,
  UserCheck,
  Users,
  VideoOff,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";

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
import { Textarea } from "@/components/ui/textarea";
import { ApiError, apiRequest } from "@/lib/api";
import { formatDate, formatDateTime, initials } from "@/lib/format";
import { Link } from "@/lib/router";
import type {
  AttendanceMutationResponse,
  CallParticipant,
  InstructorCallData,
  TrainingCompletionResponse,
} from "@/lib/types";

const MAX_UPLOAD_MB = 8;
const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];

type CameraState = "idle" | "starting" | "ready" | "error";
type Feedback = {
  tone: "success" | "error";
  title: string;
  message: string;
} | null;

export function InstructorCallPage({ trainingId }: { trainingId: number }) {
  const [data, setData] = useState<InstructorCallData | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [feedback, setFeedback] = useState<Feedback>(null);
  const [cameraState, setCameraState] = useState<CameraState>("idle");
  const [cameraError, setCameraError] = useState("");
  const [recognizing, setRecognizing] = useState(false);
  const [search, setSearch] = useState("");
  const [manualTarget, setManualTarget] = useState<CallParticipant | null>(null);
  const [manualReason, setManualReason] = useState("");
  const [manualError, setManualError] = useState("");
  const [manualBusy, setManualBusy] = useState(false);
  const [removeTarget, setRemoveTarget] = useState<CallParticipant | null>(null);
  const [removeBusy, setRemoveBusy] = useState(false);
  const [completeOpen, setCompleteOpen] = useState(false);
  const [completeBusy, setCompleteBusy] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const releaseCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, []);

  useEffect(() => () => releaseCamera(), [releaseCamera]);

  useEffect(() => {
    if (cameraState !== "ready") return;
    const video = videoRef.current;
    const stream = streamRef.current;
    if (!video || !stream) return;
    video.srcObject = stream;
    const playback = video.play();
    if (playback) {
      void playback.catch(() => {
        releaseCamera();
        setCameraState("error");
        setCameraError("Não foi possível iniciar o vídeo da câmera. Tente novamente.");
      });
    }
  }, [cameraState, releaseCamera]);

  const load = useCallback(async () => {
    setLoadError("");
    try {
      const response = await apiRequest<InstructorCallData>(
        `/api/instructor/trainings/${trainingId}/attendance`,
      );
      setData(response);
    } catch (error) {
      setLoadError(
        error instanceof ApiError
          ? error.message
          : "Não foi possível carregar a chamada desta turma.",
      );
    } finally {
      setLoading(false);
    }
  }, [trainingId]);

  useEffect(() => {
    void load();
  }, [load]);

  const pending = useMemo(
    () => (data?.participants ?? []).filter((participant) => participant.status === "pendente"),
    [data],
  );
  const present = useMemo(
    () =>
      (data?.participants ?? [])
        .filter((participant) => participant.status === "presente")
        .sort((first, second) =>
          (second.attendance?.recorded_at ?? "").localeCompare(first.attendance?.recorded_at ?? ""),
        ),
    [data],
  );
  const pendingWithFace = pending.filter((participant) => participant.face_enrolled).length;
  const filteredPending = useMemo(() => {
    const query = search.trim().toLocaleLowerCase("pt-BR");
    if (!query) return pending;
    return pending.filter(
      (participant) =>
        participant.name.toLocaleLowerCase("pt-BR").includes(query) ||
        participant.email.toLocaleLowerCase("pt-BR").includes(query),
    );
  }, [pending, search]);

  async function startCamera() {
    setCameraError("");
    setFeedback(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraState("error");
      setCameraError(
        "A câmera não está disponível neste navegador. Abra por HTTPS ou envie uma foto do dispositivo.",
      );
      return;
    }

    setCameraState("starting");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: {
          facingMode: "user",
          width: { ideal: 1280 },
          height: { ideal: 960 },
        },
      });
      releaseCamera();
      streamRef.current = stream;
      setCameraState("ready");
    } catch (error) {
      releaseCamera();
      const name = error instanceof DOMException ? error.name : "";
      const message =
        name === "NotAllowedError"
          ? "A câmera foi bloqueada. Libere a permissão ou use uma foto do dispositivo."
          : name === "NotFoundError"
            ? "Nenhuma câmera foi encontrada. Use uma foto do dispositivo."
            : name === "NotReadableError"
              ? "A câmera está em uso por outro aplicativo. Feche-o e tente novamente."
              : "Não foi possível iniciar a câmera. Verifique o HTTPS local ou use uma foto.";
      setCameraState("error");
      setCameraError(message);
    }
  }

  function stopCamera() {
    releaseCamera();
    setCameraState("idle");
    setCameraError("");
  }

  async function recognizePhoto(file: Blob, filename: string) {
    setRecognizing(true);
    setFeedback(null);
    try {
      const body = new FormData();
      body.append("file", file, filename);
      const response = await apiRequest<AttendanceMutationResponse>(
        `/api/instructor/trainings/${trainingId}/attendance/face`,
        { method: "POST", body },
      );
      const score = response.attendance.score;
      setFeedback({
        tone: "success",
        title: response.already_recorded
          ? "Presença já registrada"
          : `Presença de ${response.employee.name} confirmada`,
        message: response.already_recorded
          ? `${response.employee.name} já estava presente nesta chamada.`
          : `Reconhecimento facial${score === null ? "" : ` · similaridade ${score.toFixed(3)}`}.`,
      });
      await load();
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : "Não foi possível conferir a imagem. Tente novamente.";
      const manualHint =
        error instanceof ApiError &&
        [409, 422].includes(error.status) &&
        !message.toLocaleLowerCase("pt-BR").includes("registro manual")
          ? " Você pode confirmar a presença pelo registro manual."
          : "";
      setFeedback({
        tone: "error",
        title: "Presença não confirmada",
        message: `${message}${manualHint}`,
      });
    } finally {
      setRecognizing(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function captureFromCamera() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.videoWidth === 0 || video.videoHeight === 0) {
      setFeedback({
        tone: "error",
        title: "Câmera ainda não está pronta",
        message: "Aguarde o preview carregar e tente novamente.",
      });
      return;
    }

    const scale = Math.min(960 / video.videoWidth, 960 / video.videoHeight, 1);
    canvas.width = Math.round(video.videoWidth * scale);
    canvas.height = Math.round(video.videoHeight * scale);
    const context = canvas.getContext("2d");
    if (!context) {
      setFeedback({
        tone: "error",
        title: "Falha na captura",
        message: "Não foi possível preparar a imagem.",
      });
      return;
    }
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", 0.9),
    );
    if (!blob) {
      setFeedback({
        tone: "error",
        title: "Falha na captura",
        message: "Não foi possível gerar a imagem.",
      });
      return;
    }
    await recognizePhoto(blob, "chamada-facial.jpg");
  }

  function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!ACCEPTED_TYPES.includes(file.type)) {
      setFeedback({
        tone: "error",
        title: "Formato não aceito",
        message: "Escolha uma imagem JPG, PNG ou WebP.",
      });
      event.target.value = "";
      return;
    }
    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
      setFeedback({
        tone: "error",
        title: "Imagem muito grande",
        message: `A imagem deve ter no máximo ${MAX_UPLOAD_MB} MB.`,
      });
      event.target.value = "";
      return;
    }
    void recognizePhoto(file, file.name);
  }

  function openManual(participant: CallParticipant) {
    setManualTarget(participant);
    setManualReason("");
    setManualError("");
  }

  async function confirmManual() {
    if (!manualTarget) return;
    setManualBusy(true);
    setManualError("");
    try {
      const response = await apiRequest<AttendanceMutationResponse>(
        `/api/instructor/trainings/${trainingId}/attendance/manual`,
        {
          method: "POST",
          body: {
            employee_id: manualTarget.employee_id,
            justification: manualReason,
          },
        },
      );
      setFeedback({
        tone: "success",
        title: `Presença de ${response.employee.name} registrada`,
        message: "Registro manual confirmado pelo instrutor.",
      });
      setManualTarget(null);
      setManualReason("");
      await load();
    } catch (error) {
      setManualError(
        error instanceof ApiError ? error.message : "Não foi possível registrar a presença manual.",
      );
    } finally {
      setManualBusy(false);
    }
  }

  async function confirmRemove() {
    if (!removeTarget?.attendance) return;
    setRemoveBusy(true);
    setFeedback(null);
    try {
      await apiRequest<{ ok: boolean }>(
        `/api/instructor/trainings/${trainingId}/attendance/${removeTarget.attendance.id}`,
        { method: "DELETE" },
      );
      setFeedback({
        tone: "success",
        title: "Presença removida",
        message: `${removeTarget.name} voltou para a lista de pendentes.`,
      });
      setRemoveTarget(null);
      await load();
    } catch (error) {
      setFeedback({
        tone: "error",
        title: "Não foi possível remover",
        message: error instanceof ApiError ? error.message : "Tente novamente em instantes.",
      });
      setRemoveTarget(null);
    } finally {
      setRemoveBusy(false);
    }
  }

  async function confirmComplete() {
    if (!data?.completion.can_complete) return;
    setCompleteBusy(true);
    setFeedback(null);
    try {
      const response = await apiRequest<TrainingCompletionResponse>(
        `/api/instructor/trainings/${trainingId}/complete`,
        { method: "POST" },
      );
      setFeedback({
        tone: "success",
        title: "Turma concluída",
        message:
          response.certificates_issued > 0
            ? `${response.certificates_issued} certificado${
                response.certificates_issued === 1 ? "" : "s"
              } emitido${response.certificates_issued === 1 ? "" : "s"}.`
            : "A turma foi concluída sem certificados.",
      });
      setCompleteOpen(false);
      await load();
    } catch (error) {
      setFeedback({
        tone: "error",
        title: "Não foi possível concluir a turma",
        message: error instanceof ApiError ? error.message : "Tente novamente em instantes.",
      });
      setCompleteOpen(false);
    } finally {
      setCompleteBusy(false);
    }
  }

  const progress =
    data && data.summary.reserved > 0
      ? Math.round((data.summary.present / data.summary.reserved) * 100)
      : 0;

  const stats = data
    ? [
        { label: "Reservados", value: String(data.summary.reserved) },
        {
          label: "Presentes",
          value: String(data.summary.present),
          hint:
            data.summary.reserved === 0
              ? "Sem participantes"
              : data.summary.pending
                ? `${data.summary.pending} pendente${data.summary.pending === 1 ? "" : "s"}`
                : "Chamada completa",
        },
        { label: "Facial", value: String(data.summary.face) },
        { label: "Manual", value: String(data.summary.manual) },
      ]
    : [];

  const canRemove = data ? data.training.status !== "concluido" : false;

  return (
    <AppShell
      title="Chamada de presença"
      subtitle={data?.training.title ?? "Reconhecimento facial e fallback manual"}
      backTo="/instrutor"
    >
      <div className="space-y-5">
        {feedback && (
          <div
            role="status"
            aria-live="polite"
            className={`rounded-2xl border px-4 py-3 text-sm ${
              feedback.tone === "success"
                ? "border-accent/30 bg-accent-soft text-primary"
                : "border-destructive/20 bg-destructive/5 text-destructive"
            }`}
          >
            <p className="font-semibold">{feedback.title}</p>
            <p className="mt-0.5 text-xs leading-relaxed">{feedback.message}</p>
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center gap-2 rounded-2xl border bg-card py-16 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Carregando chamada...
          </div>
        )}

        {!loading && loadError && (
          <div className="rounded-2xl border bg-card p-6 text-center">
            <p className="font-semibold text-destructive">{loadError}</p>
            <div className="mt-4 flex justify-center gap-2">
              <Button variant="outline" onClick={() => void load()}>
                <RefreshCw className="h-4 w-4" />
                Tentar novamente
              </Button>
              <Button asChild variant="ghost">
                <a href="/instrutor">Voltar ao painel</a>
              </Button>
            </div>
          </div>
        )}

        {!loading && data && (
          <>
            <section className="relative overflow-hidden rounded-2xl bg-brand-gradient p-5 text-white shadow-card">
              <div className="absolute -right-12 -top-12 h-36 w-36 rounded-full bg-accent/30 blur-2xl" />
              <div className="relative">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-white/70">
                      Chamada de presença
                    </p>
                    <h2 className="mt-1 text-xl font-extrabold leading-tight">
                      {data.training.title}
                    </h2>
                  </div>
                  <StatusBadge status={data.training.status} />
                </div>
                <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-white/80">
                  <span className="flex items-center gap-1">
                    <CalendarDays className="h-3.5 w-3.5" />
                    {formatDate(data.training.date)} · {data.training.start_time} às{" "}
                    {data.training.end_time}
                  </span>
                  <span className="flex items-center gap-1">
                    <MapPin className="h-3.5 w-3.5" />
                    {data.training.location}
                  </span>
                  <span className="flex items-center gap-1">
                    <Users className="h-3.5 w-3.5" />
                    {data.training.instructor}
                  </span>
                </div>
                <div className="mt-4">
                  <div className="mb-1 flex items-center justify-between gap-3 text-xs">
                    <span className="font-semibold">
                      {data.summary.present} de {data.summary.reserved} presenças
                    </span>
                    <span className="text-white/75">{progress}%</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-white/20">
                    <div
                      className="h-full rounded-full bg-accent transition-all"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </div>
              </div>
            </section>

            <StatGrid stats={stats} />

            {!data.is_today && data.can_record && (
              <div className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-900">
                <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
                <div>
                  <p className="text-sm font-semibold">Esta turma não é hoje</p>
                  <p className="text-xs leading-relaxed">
                    Confirme com o RH antes de registrar presenças fora da data do treinamento.
                  </p>
                </div>
              </div>
            )}

            {!data.can_record && (
              <div className="flex items-start gap-3 rounded-2xl border border-destructive/20 bg-destructive/5 p-4 text-destructive">
                <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
                <div>
                  <p className="text-sm font-semibold">Chamada indisponível</p>
                  <p className="text-xs leading-relaxed">{data.blocked_reason}</p>
                </div>
              </div>
            )}

            {data.training.status !== "cancelado" &&
              (data.training.status === "concluido" || data.summary.reserved > 0) && (
                <SectionCard
                  title="Encerramento da turma"
                  description="Emissão de certificados"
                  action={
                    <Badge
                      variant="secondary"
                      className={
                        data.training.status === "concluido"
                          ? "bg-accent-soft text-primary"
                          : "bg-muted text-muted-foreground"
                      }
                    >
                      {data.training.status === "concluido"
                        ? "Encerrada"
                        : `${data.completion.eligible_count} elegíve${
                            data.completion.eligible_count === 1 ? "l" : "is"
                          }`}
                    </Badge>
                  }
                >
                  {data.training.status === "concluido" ? (
                    <div className="flex items-start gap-3 p-4 sm:p-5">
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent">
                        <Award className="h-5 w-5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-primary">Turma concluída</p>
                        <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
                          {data.completion.certificate_count} certificado
                          {data.completion.certificate_count === 1 ? "" : "s"} emitido
                          {data.completion.certificate_count === 1 ? "" : "s"} para os participantes
                          presentes. Os certificados estão disponíveis na lista de presenças e no
                          painel de cada funcionário.
                        </p>
                        {data.training.completed_at && (
                          <p className="mt-2 text-[11px] text-muted-foreground">
                            Encerrada em {formatDateTime(data.training.completed_at)}
                          </p>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-4 p-4 sm:p-5">
                      <div className="flex items-start gap-3">
                        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent">
                          <Award className="h-5 w-5" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-semibold text-primary">
                            Concluir e emitir certificados
                          </p>
                          <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
                            {data.completion.eligible_count} participante
                            {data.completion.eligible_count === 1 ? "" : "s"} com presença
                            registrada{" "}
                            {data.completion.eligible_count === 1 ? "receberá" : "receberão"}{" "}
                            certificado. Esta ação não pode ser desfeita.
                          </p>
                        </div>
                      </div>
                      {data.completion.warnings.map((warning) => (
                        <p
                          key={warning}
                          className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] leading-relaxed text-amber-900"
                        >
                          {warning}
                        </p>
                      ))}
                      <Button
                        className="w-full sm:w-auto"
                        onClick={() => setCompleteOpen(true)}
                        disabled={!data.completion.can_complete}
                      >
                        <Award className="h-4 w-4" />
                        Encerrar turma
                      </Button>
                    </div>
                  )}
                </SectionCard>
              )}

            <div className="grid gap-5 lg:grid-cols-2">
              <SectionCard
                title="Reconhecimento facial"
                description="Enquadre uma pessoa por vez"
                action={
                  <Badge variant="secondary" className="bg-accent-soft text-primary">
                    {pendingWithFace} com rosto
                  </Badge>
                }
              >
                <div className="space-y-4 p-4 sm:p-5">
                  {!data.can_record ? (
                    <div className="flex flex-col items-center gap-2 rounded-2xl border bg-secondary/60 px-5 py-10 text-center">
                      <AlertTriangle className="h-8 w-8 text-destructive" />
                      <p className="font-semibold text-primary">Chamada indisponível</p>
                      <p className="max-w-xs text-sm text-muted-foreground">
                        {data.blocked_reason}
                      </p>
                    </div>
                  ) : pending.length === 0 ? (
                    <div className="flex flex-col items-center gap-2 rounded-2xl border border-accent/30 bg-accent-soft px-5 py-10 text-center">
                      <CheckCircle2 className="h-8 w-8 text-accent" />
                      <p className="font-semibold text-primary">Chamada completa</p>
                      <p className="max-w-xs text-sm text-muted-foreground">
                        Todos os participantes reservados já tiveram a presença registrada.
                      </p>
                    </div>
                  ) : pendingWithFace === 0 ? (
                    <div className="flex flex-col items-center gap-2 rounded-2xl border bg-secondary/60 px-5 py-10 text-center">
                      <UserCheck className="h-8 w-8 text-primary" />
                      <p className="font-semibold text-primary">Use o registro manual</p>
                      <p className="max-w-xs text-sm text-muted-foreground">
                        Os participantes pendentes não possuem cadastro facial ativo.
                      </p>
                    </div>
                  ) : (
                    <>
                      <div className="relative aspect-[4/3] overflow-hidden rounded-2xl border border-slate-800 bg-slate-950">
                        {cameraState === "ready" ? (
                          <video
                            ref={videoRef}
                            autoPlay
                            muted
                            playsInline
                            className="h-full w-full scale-x-[-1] object-cover"
                          />
                        ) : (
                          <div className="flex h-full flex-col items-center justify-center gap-2 px-6 text-center text-white/70">
                            <ScanFace className="h-10 w-10" />
                            <p className="text-sm font-semibold text-white/90">Câmera desligada</p>
                            <p className="max-w-[240px] text-xs leading-relaxed">
                              Ative a câmera ou envie uma foto para conferir a presença.
                            </p>
                          </div>
                        )}

                        {cameraState === "ready" && (
                          <div className="pointer-events-none absolute inset-[10%] rounded-[42%] border-2 border-white/70 shadow-[0_0_0_999px_rgba(0,0,0,0.18)]" />
                        )}

                        {recognizing && (
                          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-slate-950/70 text-white">
                            <Loader2 className="h-6 w-6 animate-spin text-accent" />
                            <p className="text-xs font-semibold">Conferindo rosto...</p>
                          </div>
                        )}
                      </div>

                      <canvas ref={canvasRef} className="hidden" />
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept={ACCEPTED_TYPES.join(",")}
                        className="hidden"
                        onChange={handleFile}
                      />

                      {cameraError && (
                        <p className="rounded-xl border border-destructive/20 bg-destructive/5 px-3 py-2 text-xs text-destructive">
                          {cameraError}
                        </p>
                      )}

                      <div className="flex flex-wrap gap-2">
                        {cameraState === "ready" ? (
                          <>
                            <Button
                              className="min-w-[160px] flex-1"
                              onClick={() => void captureFromCamera()}
                              disabled={recognizing}
                            >
                              {recognizing ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <ScanFace className="h-4 w-4" />
                              )}
                              Registrar presença
                            </Button>
                            <Button variant="outline" onClick={stopCamera} disabled={recognizing}>
                              <VideoOff className="h-4 w-4" />
                              Desligar
                            </Button>
                          </>
                        ) : (
                          <>
                            <Button
                              className="min-w-[150px] flex-1"
                              onClick={() => void startCamera()}
                              disabled={cameraState === "starting" || recognizing}
                            >
                              {cameraState === "starting" ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <Camera className="h-4 w-4" />
                              )}
                              Ativar câmera
                            </Button>
                            <Button
                              variant="outline"
                              onClick={() => fileInputRef.current?.click()}
                              disabled={recognizing}
                            >
                              <ImageUp className="h-4 w-4" />
                              Usar foto
                            </Button>
                          </>
                        )}
                      </div>

                      {cameraState === "ready" && (
                        <button
                          type="button"
                          className="text-xs font-semibold text-accent underline-offset-2 hover:underline"
                          onClick={() => fileInputRef.current?.click()}
                          disabled={recognizing}
                        >
                          Prefiro enviar uma foto do dispositivo
                        </button>
                      )}
                    </>
                  )}

                  <p className="flex items-start gap-2 text-[11px] leading-relaxed text-muted-foreground">
                    <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent" />A imagem é
                    processada localmente para esta chamada e não é armazenada. A comparação usa
                    apenas participantes com reserva ativa nesta turma.
                  </p>
                </div>
              </SectionCard>

              <SectionCard
                title="Participantes pendentes"
                description={`${pending.length} aguardando confirmação`}
                action={
                  <Badge variant="secondary">
                    {data.summary.present}/{data.summary.reserved}
                  </Badge>
                }
              >
                <div className="space-y-3 p-4 sm:p-5">
                  <div className="relative">
                    <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      value={search}
                      onChange={(event) => setSearch(event.target.value)}
                      placeholder="Buscar por nome ou e-mail"
                      className="pl-9"
                      aria-label="Buscar participante"
                    />
                  </div>

                  {filteredPending.length ? (
                    <div className="divide-y overflow-hidden rounded-2xl border">
                      {filteredPending.map((participant) => (
                        <div
                          key={participant.employee_id}
                          className="flex flex-wrap items-center gap-3 p-3"
                        >
                          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-secondary text-xs font-bold text-primary">
                            {initials(participant.name)}
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-semibold">{participant.name}</p>
                            <p className="truncate text-[11px] text-muted-foreground">
                              {participant.email}
                            </p>
                            <Badge
                              variant="secondary"
                              className={`mt-1 text-[9px] ${
                                participant.face_enrolled
                                  ? "bg-accent-soft text-primary"
                                  : "bg-muted text-muted-foreground"
                              }`}
                            >
                              {participant.face_enrolled ? "Face ativa" : "Sem cadastro facial"}
                            </Badge>
                          </div>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => openManual(participant)}
                            disabled={!data.can_record}
                          >
                            <UserCheck className="h-3.5 w-3.5" />
                            Registrar
                          </Button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <EmptyState
                      icon={<Users className="h-5 w-5" />}
                      title={
                        data.summary.reserved === 0
                          ? "Sem participantes"
                          : pending.length
                            ? "Nenhum resultado"
                            : "Todos confirmados"
                      }
                      description={
                        data.summary.reserved === 0
                          ? "A chamada será liberada quando houver reservas ativas nesta turma."
                          : pending.length
                            ? "Ajuste a busca para localizar outro participante."
                            : "As presenças desta turma já foram registradas."
                      }
                    />
                  )}
                </div>
              </SectionCard>
            </div>

            <SectionCard
              title="Presenças registradas"
              description={`${data.summary.face} por reconhecimento facial · ${data.summary.manual} ${
                data.summary.manual === 1 ? "manual" : "manuais"
              }`}
            >
              {present.length ? (
                <div className="divide-y">
                  {present.map((participant) => (
                    <div
                      key={participant.employee_id}
                      className="flex flex-wrap items-start gap-3 p-4"
                    >
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent-soft text-primary">
                        <CheckCircle2 className="h-5 w-5 text-accent" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="text-sm font-semibold">{participant.name}</p>
                          <Badge variant="secondary" className="bg-accent-soft text-primary">
                            {participant.attendance?.method === "face" ? "Facial" : "Manual"}
                          </Badge>
                        </div>
                        <p className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {formatDateTime(participant.attendance?.recorded_at ?? "")}
                          </span>
                          {participant.attendance?.method === "face" &&
                            participant.attendance.score !== null && (
                              <span>
                                Similaridade{" "}
                                {participant.attendance.score.toLocaleString("pt-BR", {
                                  minimumFractionDigits: 3,
                                  maximumFractionDigits: 3,
                                })}
                              </span>
                            )}
                        </p>
                        {participant.attendance?.justification && (
                          <p className="mt-1 rounded-lg bg-muted px-2 py-1 text-[11px] leading-relaxed text-muted-foreground">
                            {participant.attendance.justification}
                          </p>
                        )}
                        {participant.certificate && (
                          <Link
                            to={`/verificar/${participant.certificate.code}`}
                            className="mt-2 inline-flex max-w-full items-center gap-1.5 rounded-lg bg-accent-soft px-2 py-1 font-mono text-[10px] font-semibold text-primary underline-offset-2 hover:underline"
                          >
                            <Award className="h-3.5 w-3.5 shrink-0 text-accent" />
                            <span className="truncate">{participant.certificate.code}</span>
                          </Link>
                        )}
                      </div>
                      {canRemove && (
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-9 w-9 shrink-0 text-muted-foreground hover:text-destructive"
                          aria-label={`Remover presença de ${participant.name}`}
                          title="Remover presença"
                          onClick={() => setRemoveTarget(participant)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState
                  icon={<ScanFace className="h-5 w-5" />}
                  title="Nenhuma presença registrada"
                  description="Use o reconhecimento facial ou o registro manual para iniciar a chamada."
                />
              )}
            </SectionCard>
          </>
        )}
      </div>

      <Dialog
        open={Boolean(manualTarget)}
        onOpenChange={(open) => {
          if (!open && !manualBusy) {
            setManualTarget(null);
            setManualError("");
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Registrar presença manual</DialogTitle>
            <DialogDescription>
              Confirme a identidade de {manualTarget?.name} e informe o motivo do registro sem
              reconhecimento facial.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="manual-reason">Motivo</Label>
            <Textarea
              id="manual-reason"
              value={manualReason}
              onChange={(event) => {
                setManualReason(event.target.value);
                setManualError("");
              }}
              placeholder="Ex.: aluno sem cadastro facial ou câmera indisponível."
              rows={3}
              maxLength={300}
              autoFocus
            />
            <div className="flex items-center justify-between text-[11px] text-muted-foreground">
              <span>Mínimo de 5 caracteres.</span>
              <span>{manualReason.length}/300</span>
            </div>
            {manualError && <p className="text-xs font-medium text-destructive">{manualError}</p>}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setManualTarget(null)} disabled={manualBusy}>
              Cancelar
            </Button>
            <Button
              onClick={() => void confirmManual()}
              disabled={manualBusy || manualReason.trim().length < 5}
            >
              {manualBusy ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <UserCheck className="h-4 w-4" />
              )}
              Confirmar presença
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog
        open={Boolean(removeTarget)}
        onOpenChange={(open) => {
          if (!open && !removeBusy) setRemoveTarget(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remover presença?</AlertDialogTitle>
            <AlertDialogDescription>
              A presença de {removeTarget?.name} será apagada e voltará para a lista de pendentes. O
              instrutor poderá registrá-la novamente.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={removeBusy}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={(event) => {
                event.preventDefault();
                void confirmRemove();
              }}
              disabled={removeBusy}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {removeBusy ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4" />
              )}
              Remover presença
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog
        open={completeOpen}
        onOpenChange={(open) => {
          if (!open && !completeBusy) setCompleteOpen(false);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Encerrar turma e emitir certificados?</AlertDialogTitle>
            <AlertDialogDescription>
              A turma será marcada como concluída e não aceitará novas presenças.{" "}
              {(data?.completion.eligible_count ?? 0) === 1
                ? "Será emitido 1 certificado"
                : `Serão emitidos ${data?.completion.eligible_count ?? 0} certificados`}{" "}
              para os participantes com presença registrada.
            </AlertDialogDescription>
          </AlertDialogHeader>
          {Boolean(data?.completion.pending) && (
            <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-relaxed text-amber-900">
              {data?.completion.pending} participante
              {(data?.completion.pending ?? 0) === 1 ? "" : "s"} sem presença{" "}
              {(data?.completion.pending ?? 0) === 1 ? "ficará" : "ficarão"} sem certificado.
            </p>
          )}
          <AlertDialogFooter>
            <AlertDialogCancel disabled={completeBusy}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={(event) => {
                event.preventDefault();
                void confirmComplete();
              }}
              disabled={completeBusy || !data?.completion.can_complete}
            >
              {completeBusy ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Award className="h-4 w-4" />
              )}
              Encerrar turma
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AppShell>
  );
}
