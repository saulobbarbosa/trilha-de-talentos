export class ApiError extends Error {
  status: number;
  nextStep: string | undefined;

  constructor(message: string, status: number, nextStep?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.nextStep = nextStep;
  }
}

function readCookie(name: string): string | undefined {
  const prefix = `${name}=`;
  return document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(prefix))
    ?.slice(prefix.length);
}

export async function ensureCsrfToken(): Promise<string> {
  const existing = readCookie("tt_csrf");
  if (existing) return decodeURIComponent(existing);

  const response = await fetch("/api/auth/csrf", { credentials: "same-origin" });
  if (!response.ok) {
    throw new ApiError("Não foi possível iniciar a sessão de segurança.", response.status);
  }
  const data = (await response.json()) as { csrf_token: string };
  return data.csrf_token;
}

function detailMessage(payload: unknown, fallback: string): string {
  if (typeof payload === "object" && payload !== null && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => {
          if (typeof item === "object" && item !== null && "msg" in item) {
            return String((item as { msg: unknown }).msg).replace(/^Value error,\s*/i, "");
          }
          return null;
        })
        .filter(Boolean);
      if (messages.length) return messages.join(" ");
    }
  }
  return fallback;
}

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
};

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? "GET";
  const headers = new Headers();
  let body: BodyInit | undefined;

  if (options.body instanceof FormData) {
    body = options.body;
  } else if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.body);
  }

  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    headers.set("X-CSRF-Token", await ensureCsrfToken());
  }

  const init: RequestInit = {
    method,
    headers,
    credentials: "same-origin",
  };
  if (body !== undefined) init.body = body;
  if (options.signal) init.signal = options.signal;

  const response = await fetch(path, init);

  if (!response.ok) {
    let payload: unknown = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    throw new ApiError(
      detailMessage(payload, "Não foi possível concluir a operação."),
      response.status,
      response.headers.get("X-Next-Step") ?? undefined,
    );
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
