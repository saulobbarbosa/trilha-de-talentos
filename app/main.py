from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import BASE_DIR, get_settings
from app.database import init_db
from app.routers import auth, certificates, face, home, instructor, leader, rh

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("trilha")
settings = get_settings()
DIST_DIR = BASE_DIR / "dist"

def _content_security_policy() -> str:
    docs_script = " https://cdn.jsdelivr.net" if settings.dev_mode else ""
    docs_style = " https://cdn.jsdelivr.net" if settings.dev_mode else ""
    docs_image = " https://fastapi.tiangolo.com" if settings.dev_mode else ""
    return (
        "default-src 'self'; "
        f"img-src 'self' data: blob:{docs_image}; "
        "media-src 'self' blob:; "
        f"style-src 'self' 'unsafe-inline' https://fonts.googleapis.com{docs_style}; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        f"script-src 'self' 'unsafe-inline'{docs_script}; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Permissions-Policy": "camera=(self), microphone=(), geolocation=()",
    "Content-Security-Policy": _content_security_policy(),
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for key, value in SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    logger.info("Banco inicializado em %s", settings.database_path)
    if settings.face_model_preload:
        try:
            from app.services.face import get_face_service

            get_face_service().ensure_loaded()
            logger.info("Modelo facial buffalo_l carregado (CPUExecutionProvider).")
        except Exception as exc:
            logger.warning("Modelo facial nao carregado neste start: %s", exc)
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    docs_url="/api/docs" if settings.dev_mode else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if settings.dev_mode else None,
    lifespan=lifespan,
)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(auth.router)
app.include_router(home.router)
app.include_router(face.router)
app.include_router(certificates.router)
app.include_router(rh.router)
app.include_router(leader.router)
app.include_router(instructor.router)


@app.get("/api/health", tags=["infra"])
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "dev_mode": settings.dev_mode}


if (DIST_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")


def _missing_frontend_page() -> HTMLResponse:
    return HTMLResponse(
        """
        <!doctype html>
        <html lang="pt-BR">
          <head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
          <title>Trilha de Talentos - frontend nao compilado</title></head>
          <body style="font-family:system-ui;background:#f4f7fb;color:#0b2a63;padding:32px">
            <main style="max-width:640px;margin:auto;background:#fff;border:1px solid #dbe4f0;border-radius:16px;padding:24px">
              <h1 style="color:#00339F">Frontend ainda nao compilado</h1>
              <p>Execute <code>setup.bat</code> ou <code>npm install &amp;&amp; npm run build</code> na raiz do projeto.</p>
              <p>Depois reinicie com <code>start.bat</code>.</p>
            </main>
          </body>
        </html>
        """,
        status_code=503,
    )


@app.get("/{full_path:path}", include_in_schema=False)
def serve_spa(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Rota de API não encontrada.")
    if not (DIST_DIR / "index.html").is_file():
        return _missing_frontend_page()

    relative = full_path.strip("/")
    if relative:
        candidate = (DIST_DIR / relative).resolve()
        try:
            candidate.relative_to(DIST_DIR.resolve())
        except ValueError:
            raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
        if candidate.is_file() and candidate.name != "index.html":
            return FileResponse(candidate)

    return FileResponse(DIST_DIR / "index.html", headers={"Cache-Control": "no-cache"})


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=404,
            content={"detail": exc.detail if isinstance(exc.detail, str) else "Recurso não encontrado."},
        )
    if (DIST_DIR / "index.html").is_file():
        return FileResponse(DIST_DIR / "index.html", headers={"Cache-Control": "no-cache"})
    return _missing_frontend_page()
