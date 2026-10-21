import {
  AlertTriangle,
  Camera,
  CheckCircle2,
  ImageUp,
  Loader2,
  LockKeyhole,
  RefreshCw,
  RotateCcw,
  ScanFace,
  ShieldCheck,
  Trash2,
  VideoOff,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState, type ChangeEvent } from "react";

import { AppShell, SectionCard } from "@/components/AppShell";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { ApiError, apiRequest } from "@/lib/api";
import { homeForRole, useAuth } from "@/lib/auth";
import { formatDate, formatDateTime } from "@/lib/format";
import { useRouter } from "@/lib/router";
import type { FaceConsentTerm, FaceEnrollmentStatus, FaceSampleResponse } from "@/lib/types";

const MAX_UPLOAD_MB = 8;
const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];
const CAPTURE_TIPS = [
  "Olhe de frente para a câmera e mantenha o rosto dentro do guia.",
  "Vire levemente o rosto para a esquerda, sem sair do enquadramento.",
  "Vire levemente o rosto para a direita para concluir as capturas.",
];

type CameraState = "idle" | "starting" | "ready" | "error";
type Feedback = { tone: "success" | "error"; message: string } | null;

export function FaceEnrollmentPage() {
  const { user, refresh } = useAuth();
  const { navigate } = useRouter();
  const [term, setTerm] = useState<FaceConsentTerm | null>(null);
  const [status, setStatus] = useState<FaceEnrollmentStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [consentChecked, setConsentChecked] = useState(false);
  const [accepting, setAccepting] = useState(false);
  const [cameraState, setCameraState] = useState<CameraState>("idle");
  const [cameraError, setCameraError] = useState("");
  const [capturing, setCapturing] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [revoking, setRevoking] = useState(false);
  const [feedback, setFeedback] = useState<Feedback>(null);

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
      const [termData, statusData] = await Promise.all([
        apiRequest<FaceConsentTerm>("/api/face/term"),
        apiRequest<FaceEnrollmentStatus>("/api/face/status"),
      ]);
      setTerm(termData);
      setStatus(statusData);
    } catch (error) {
      setLoadError(
        error instanceof ApiError ? error.message : "Não foi possível carregar o cadastro facial.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleAcceptConsent() {
    if (!term || !consentChecked) return;
    setAccepting(true);
    setFeedback(null);
    try {
      const response = await apiRequest<{ status: FaceEnrollmentStatus }>("/api/face/consent", {
        method: "POST",
        body: { term_version: term.version, accepted: true },
      });
      setStatus(response.status);
      setFeedback({
        tone: "success",
        message: "Consentimento registrado. Agora vamos capturar seu rosto.",
      });
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (error) {
      setFeedback({
        tone: "error",
        message: error instanceof ApiError ? error.message : "Não foi possível registrar o aceite.",
      });
    } finally {
      setAccepting(false);
    }
  }

  async function startCamera() {
    setFeedback(null);
    setCameraError("");
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraState("error");
      setCameraError(
        "A câmera não está disponível neste navegador. Abra por HTTPS ou use uma foto do dispositivo.",
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
          ? "A câmera foi bloqueada. Libere a permissão no navegador ou use uma foto do dispositivo."
          : name === "NotFoundError"
            ? "Nenhuma câmera foi encontrada. Use uma foto do dispositivo para continuar."
            : name === "NotReadableError"
              ? "A câmera está em uso por outro aplicativo. Feche-o e tente novamente."
              : "Não foi possível iniciar a câmera. Verifique o HTTPS local ou use uma foto do dispositivo.";
      setCameraState("error");
      setCameraError(message);
    }
  }

  function stopCamera() {
    releaseCamera();
    setCameraState("idle");
    setCameraError("");
  }

  async function uploadSample(file: Blob, filename: string) {
    setCapturing(true);
    setFeedback(null);
    try {
      const body = new FormData();
      body.append("file", file, filename);
      const response = await apiRequest<FaceSampleResponse>("/api/face/enrollment/samples", {
        method: "POST",
        body,
      });
      setStatus(response.status);
      setFeedback({ tone: "success", message: response.sample.message });
      if (response.status.enrollment.complete) {
        releaseCamera();
        setCameraState("idle");
        void refresh();
      }
    } catch (error) {
      setFeedback({
        tone: "error",
        message:
          error instanceof ApiError
            ? error.message
            : "Não foi possível validar esta captura. Tente novamente.",
      });
    } finally {
      setCapturing(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function captureFromCamera() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.videoWidth === 0 || video.videoHeight === 0) {
      setFeedback({
        tone: "error",
        message: "A câmera ainda não está pronta. Aguarde um instante.",
      });
      return;
    }
    const scale = Math.min(960 / video.videoWidth, 960 / video.videoHeight, 1);
    canvas.width = Math.round(video.videoWidth * scale);
    canvas.height = Math.round(video.videoHeight * scale);
    const context = canvas.getContext("2d");
    if (!context) {
      setFeedback({ tone: "error", message: "Não foi possível preparar a captura." });
      return;
    }
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", 0.9),
    );
    if (!blob) {
      setFeedback({ tone: "error", message: "Não foi possível gerar a imagem da captura." });
      return;
    }
    await uploadSample(blob, "captura-facial.jpg");
  }

  function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!ACCEPTED_TYPES.includes(file.type)) {
      setFeedback({ tone: "error", message: "Escolha uma imagem JPG, PNG ou WebP." });
      event.target.value = "";
      return;
    }
    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
      setFeedback({ tone: "error", message: `A imagem deve ter no máximo ${MAX_UPLOAD_MB} MB.` });
      event.target.value = "";
      return;
    }
    void uploadSample(file, file.name);
  }

  async function resetEnrollment() {
    setResetting(true);
    setFeedback(null);
    try {
      const response = await apiRequest<{ status: FaceEnrollmentStatus }>("/api/face/enrollment", {
        method: "DELETE",
      });
      setStatus(response.status);
      setFeedback({
        tone: "success",
        message: "Capturas removidas. Você pode fazer o cadastro novamente.",
      });
      await refresh();
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (error) {
      setFeedback({
        tone: "error",
        message: error instanceof ApiError ? error.message : "Não foi possível refazer o cadastro.",
      });
    } finally {
      setResetting(false);
    }
  }

  async function revokeConsent() {
    setRevoking(true);
    setFeedback(null);
    releaseCamera();
    setCameraState("idle");
    try {
      const response = await apiRequest<{ status: FaceEnrollmentStatus }>("/api/face/consent", {
        method: "DELETE",
      });
      setStatus(response.status);
      setConsentChecked(false);
      setFeedback({
        tone: "success",
        message: "Consentimento revogado e vetores faciais excluídos.",
      });
      await refresh();
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (error) {
      setFeedback({
        tone: "error",
        message:
          error instanceof ApiError ? error.message : "Não foi possível revogar o consentimento.",
      });
    } finally {
      setRevoking(false);
    }
  }

  const home = user ? homeForRole(user.role) : "/";
  const enrollment = status?.enrollment;
  const samples = enrollment?.samples ?? 0;
  const required = enrollment?.required ?? 3;
  const fullyEnrolled = enrollment?.complete ?? false;
  const consentAccepted = status?.term.accepted ?? false;
  const nextTip = CAPTURE_TIPS[Math.min(samples, CAPTURE_TIPS.length - 1)] ?? CAPTURE_TIPS[0];

  return (
    <AppShell title="Cadastro facial" subtitle="Consentimento e captura guiada" backTo={home}>
      <div className="mx-auto max-w-2xl space-y-4">
        {loading && (
          <div className="flex items-center justify-center gap-2 rounded-2xl border bg-card py-16 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Carregando cadastro facial...
          </div>
        )}

        {!loading && loadError && (
          <div className="rounded-2xl border bg-card p-6 text-center">
            <p className="font-semibold text-destructive">{loadError}</p>
            <Button
              variant="outline"
              className="mt-4"
              onClick={() => {
                setLoading(true);
                void load();
              }}
            >
              <RefreshCw className="h-4 w-4" />
              Tentar novamente
            </Button>
          </div>
        )}

        {!loading && status && term && (
          <>
            <StepBar
              consentDone={consentAccepted}
              captureDone={fullyEnrolled}
              current={!consentAccepted ? 1 : fullyEnrolled ? 3 : 2}
            />

            {feedback && (
              <div
                role={feedback.tone === "error" ? "alert" : "status"}
                className={
                  feedback.tone === "error"
                    ? "flex items-start gap-2 rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm font-medium text-destructive"
                    : "flex items-start gap-2 rounded-xl border border-accent/30 bg-accent-soft px-4 py-3 text-sm font-medium text-primary"
                }
              >
                {feedback.tone === "error" ? (
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                ) : (
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                )}
                {feedback.message}
              </div>
            )}

            {!consentAccepted ? (
              <section className="space-y-4">
                <div className="overflow-hidden rounded-2xl bg-brand-gradient p-5 text-white shadow-card">
                  <div className="flex items-center gap-3">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-white/15">
                      <ShieldCheck className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-white/70">
                        Etapa 1 de 3
                      </p>
                      <h2 className="text-lg font-extrabold">Seu consentimento é opcional</h2>
                    </div>
                  </div>
                  <p className="mt-4 text-sm leading-relaxed text-white/85">{term.summary}</p>
                  <p className="mt-2 text-[11px] leading-relaxed text-white/65">
                    Versão {term.version} · Atualizado em {formatDate(term.updated_at)}
                  </p>
                </div>

                <SectionCard
                  title="Termo de consentimento LGPD"
                  description="Leia com atenção antes de autorizar o cadastro"
                >
                  <div className="max-h-96 space-y-4 overflow-y-auto p-4 sm:p-5">
                    {term.sections.map((section) => (
                      <div key={section.heading}>
                        <h3 className="text-sm font-bold text-primary">{section.heading}</h3>
                        <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                          {section.body}
                        </p>
                      </div>
                    ))}
                  </div>
                  <div className="space-y-4 border-t p-4 sm:p-5">
                    <div className="flex items-start gap-3">
                      <Checkbox
                        id="face-consent"
                        checked={consentChecked}
                        onCheckedChange={(value) => setConsentChecked(value === true)}
                        className="mt-0.5 h-5 w-5"
                      />
                      <Label
                        htmlFor="face-consent"
                        className="cursor-pointer text-sm leading-relaxed"
                      >
                        Li e concordo com o tratamento do meu modelo facial para conferência de
                        presença nos treinamentos. Entendo que posso revogar este consentimento a
                        qualquer momento.
                      </Label>
                    </div>
                    <Button
                      className="h-12 w-full text-base"
                      disabled={!consentChecked || accepting}
                      onClick={() => void handleAcceptConsent()}
                    >
                      {accepting ? (
                        <Loader2 className="h-5 w-5 animate-spin" />
                      ) : (
                        <LockKeyhole className="h-5 w-5" />
                      )}
                      {accepting ? "Registrando..." : "Aceitar e continuar"}
                    </Button>
                    <Button
                      variant="ghost"
                      className="w-full"
                      onClick={() => navigate(home)}
                      disabled={accepting}
                    >
                      Agora não, voltar ao painel
                    </Button>
                  </div>
                </SectionCard>

                <p className="px-2 pb-4 text-center text-[11px] leading-relaxed text-muted-foreground">
                  A recusa não impede sua participação nos treinamentos. Nesse caso, o instrutor
                  poderá registrar a presença manualmente.
                </p>
              </section>
            ) : fullyEnrolled ? (
              <section className="space-y-4">
                <div className="rounded-2xl border border-accent/30 bg-card p-6 text-center shadow-card">
                  <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-accent-soft text-accent">
                    <CheckCircle2 className="h-8 w-8" />
                  </div>
                  <h2 className="mt-4 text-xl font-extrabold text-primary">
                    Cadastro facial concluído
                  </h2>
                  <p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-muted-foreground">
                    Seu modelo facial está pronto para a conferência de presença dos treinamentos.
                    Nenhuma foto foi armazenada.
                  </p>
                  <Button className="mt-5 h-11 w-full sm:w-auto" onClick={() => navigate(home)}>
                    Voltar ao painel
                  </Button>
                </div>

                <SectionCard
                  title="Privacidade e consentimento"
                  description="Você controla seus dados biométricos"
                >
                  <div className="space-y-4 p-4 sm:p-5">
                    <div className="rounded-xl bg-secondary/70 p-4 text-xs leading-relaxed text-muted-foreground">
                      <p className="font-semibold text-primary">Consentimento ativo</p>
                      <p className="mt-1">
                        Termo versão {status.term.current_version}
                        {status.term.accepted_at
                          ? ` aceito em ${formatDateTime(status.term.accepted_at)}`
                          : ""}
                        . Processamento local em CPU, sem envio de imagens para a nuvem.
                      </p>
                    </div>
                    <div className="flex flex-col gap-2 sm:flex-row">
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button variant="outline" disabled={resetting || revoking}>
                            {resetting ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <RotateCcw className="h-4 w-4" />
                            )}
                            Refazer cadastro
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Refazer o cadastro facial?</AlertDialogTitle>
                            <AlertDialogDescription>
                              As três capturas atuais serão excluídas. Seu consentimento será
                              mantido e você poderá iniciar uma nova sequência.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancelar</AlertDialogCancel>
                            <AlertDialogAction onClick={() => void resetEnrollment()}>
                              Refazer cadastro
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>

                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button
                            variant="outline"
                            className="border-destructive/30 text-destructive hover:bg-destructive/5 hover:text-destructive"
                            disabled={resetting || revoking}
                          >
                            {revoking ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Trash2 className="h-4 w-4" />
                            )}
                            Revogar consentimento
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Revogar o consentimento?</AlertDialogTitle>
                            <AlertDialogDescription>
                              Os vetores faciais e o registro de consentimento serão excluídos. Você
                              poderá continuar nos treinamentos com registro manual de presença.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Manter consentimento</AlertDialogCancel>
                            <AlertDialogAction
                              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                              onClick={() => void revokeConsent()}
                            >
                              Revogar e excluir
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  </div>
                </SectionCard>
              </section>
            ) : (
              <section className="space-y-4">
                <SectionCard
                  title={`Captura guiada · ${samples} de ${required}`}
                  description="Use a câmera ou envie fotos nítidas do seu rosto"
                >
                  <div className="space-y-4 p-4 sm:p-5">
                    <div>
                      <Progress value={(samples / required) * 100} className="h-2" />
                      <div className="mt-3 flex items-start gap-2 rounded-xl bg-accent-soft px-3 py-2.5 text-xs font-medium text-primary">
                        <ScanFace className="mt-0.5 h-4 w-4 shrink-0" />
                        {nextTip}
                      </div>
                    </div>

                    <div className="relative aspect-[4/5] overflow-hidden rounded-2xl bg-slate-900 sm:aspect-video">
                      <video
                        ref={videoRef}
                        autoPlay
                        muted
                        playsInline
                        aria-label="Prévia da câmera para cadastro facial"
                        className={`h-full w-full -scale-x-100 object-cover ${
                          cameraState === "ready" ? "opacity-100" : "opacity-0"
                        }`}
                      />
                      {cameraState === "ready" ? (
                        <>
                          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                            <div className="h-[72%] w-[54%] rounded-[50%] border-2 border-dashed border-white/85 shadow-[0_0_0_999px_rgba(2,6,23,0.35)]" />
                          </div>
                          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-slate-950/80 to-transparent px-4 pb-3 pt-8 text-center text-xs font-medium text-white">
                            Enquadre o rosto dentro da guia
                          </div>
                        </>
                      ) : (
                        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 px-6 text-center text-white/80">
                          {cameraState === "starting" ? (
                            <Loader2 className="h-8 w-8 animate-spin text-accent" />
                          ) : cameraState === "error" ? (
                            <VideoOff className="h-9 w-9 text-white/50" />
                          ) : (
                            <Camera className="h-9 w-9 text-accent" />
                          )}
                          <div>
                            <p className="text-sm font-semibold text-white">
                              {cameraState === "starting"
                                ? "Solicitando permissão da câmera..."
                                : cameraState === "error"
                                  ? "Câmera indisponível"
                                  : "Sua câmera será usada apenas para esta captura"}
                            </p>
                            <p className="mt-1 max-w-xs text-[11px] leading-relaxed text-white/60">
                              {cameraState === "error"
                                ? cameraError
                                : "A foto é processada localmente e não fica armazenada no sistema."}
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                    <canvas ref={canvasRef} className="hidden" />

                    <div className="grid gap-2 sm:grid-cols-2">
                      {cameraState === "ready" ? (
                        <>
                          <Button
                            className="h-12"
                            disabled={capturing || samples >= required}
                            onClick={() => void captureFromCamera()}
                          >
                            {capturing ? (
                              <Loader2 className="h-5 w-5 animate-spin" />
                            ) : (
                              <Camera className="h-5 w-5" />
                            )}
                            {capturing ? "Validando..." : `Capturar foto ${samples + 1}`}
                          </Button>
                          <Button
                            variant="outline"
                            className="h-12"
                            disabled={capturing}
                            onClick={stopCamera}
                          >
                            <VideoOff className="h-4 w-4" />
                            Desligar câmera
                          </Button>
                        </>
                      ) : (
                        <Button
                          className="h-12"
                          disabled={cameraState === "starting" || capturing}
                          onClick={() => void startCamera()}
                        >
                          {cameraState === "starting" ? (
                            <Loader2 className="h-5 w-5 animate-spin" />
                          ) : (
                            <Camera className="h-5 w-5" />
                          )}
                          {cameraState === "error" ? "Tentar câmera novamente" : "Ativar câmera"}
                        </Button>
                      )}
                      <Button
                        variant="outline"
                        className="h-12"
                        disabled={capturing}
                        onClick={() => fileInputRef.current?.click()}
                      >
                        <ImageUp className="h-4 w-4" />
                        Usar foto do dispositivo
                      </Button>
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept="image/jpeg,image/png,image/webp"
                        className="hidden"
                        onChange={handleFile}
                      />
                    </div>

                    <div className="flex items-center justify-between gap-3 rounded-xl border bg-background px-3 py-2.5">
                      <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                        <ShieldCheck className="h-4 w-4 shrink-0 text-accent" />
                        Imagens não são armazenadas. Apenas o vetor biométrico fica no servidor
                        local.
                      </div>
                      <span className="shrink-0 text-xs font-bold text-primary">
                        {samples}/{required}
                      </span>
                    </div>
                  </div>
                </SectionCard>

                <SectionCard title="Consentimento e privacidade">
                  <div className="space-y-3 p-4 text-xs leading-relaxed text-muted-foreground sm:p-5">
                    <p>
                      Consentimento ativo desde{" "}
                      {status.term.accepted_at ? formatDateTime(status.term.accepted_at) : "agora"}.
                      Você pode interromper o cadastro e revogar o consentimento a qualquer momento.
                    </p>
                    <div className="flex flex-col gap-2 sm:flex-row">
                      {samples > 0 && (
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button variant="outline" size="sm" disabled={resetting || revoking}>
                              <RotateCcw className="h-4 w-4" />
                              Reiniciar capturas
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Reiniciar as capturas?</AlertDialogTitle>
                              <AlertDialogDescription>
                                As capturas já validadas serão removidas. O consentimento será
                                mantido.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancelar</AlertDialogCancel>
                              <AlertDialogAction onClick={() => void resetEnrollment()}>
                                Reiniciar
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      )}
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button
                            variant="outline"
                            size="sm"
                            className="border-destructive/30 text-destructive hover:bg-destructive/5 hover:text-destructive"
                            disabled={resetting || revoking}
                          >
                            <Trash2 className="h-4 w-4" />
                            Revogar consentimento
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Revogar o consentimento?</AlertDialogTitle>
                            <AlertDialogDescription>
                              As capturas e o consentimento serão excluídos. A presença nos
                              treinamentos poderá ser registrada manualmente.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Manter consentimento</AlertDialogCancel>
                            <AlertDialogAction
                              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                              onClick={() => void revokeConsent()}
                            >
                              Revogar e excluir
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  </div>
                </SectionCard>
              </section>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}

function StepBar({
  consentDone,
  captureDone,
  current,
}: {
  consentDone: boolean;
  captureDone: boolean;
  current: number;
}) {
  const steps = [
    { number: 1, label: "Consentimento", shortLabel: "Aceite", done: consentDone },
    { number: 2, label: "Capturas", shortLabel: "Captura", done: captureDone },
    { number: 3, label: "Pronto", shortLabel: "Pronto", done: captureDone },
  ];
  return (
    <div className="grid grid-cols-3 gap-2 rounded-2xl border bg-card p-2 shadow-card">
      {steps.map((step) => {
        const active = step.number === current;
        return (
          <div
            key={step.number}
            className={`flex items-center gap-2 rounded-xl px-2 py-2 ${
              active ? "bg-accent-soft" : ""
            }`}
          >
            <span
              className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                step.done
                  ? "bg-accent text-white"
                  : active
                    ? "bg-primary text-white"
                    : "bg-muted text-muted-foreground"
              }`}
            >
              {step.done ? <CheckCircle2 className="h-4 w-4" /> : step.number}
            </span>
            <span
              className={`truncate text-[11px] font-semibold ${
                active ? "text-primary" : "text-muted-foreground"
              }`}
            >
              <span className="hidden sm:inline">{step.label}</span>
              <span className="sm:hidden">{step.shortLabel}</span>
            </span>
          </div>
        );
      })}
    </div>
  );
}
