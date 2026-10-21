from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "Trilha de Talentos"
    dev_mode: bool = True
    secret_key: str = "dev-secret-key-apenas-para-desenvolvimento"
    database_url: str = "sqlite:///./data/app.db"

    app_host: str = "0.0.0.0"
    app_port: int = 8000
    session_cookie_name: str = "tt_session"
    csrf_cookie_name: str = "tt_csrf"
    session_max_age_seconds: int = 12 * 60 * 60
    session_cookie_secure: bool = False

    public_base_url: str = ""

    use_https: bool = False
    https_cert_file: str = "data/certs/lins-local.crt"
    https_key_file: str = "data/certs/lins-local.key"

    face_threshold: float = 0.45
    face_margin: float = 0.05
    face_model_root: str = "data/insightface"
    face_model_preload: bool = True
    face_det_size: int = 640
    face_enroll_samples: int = 3
    face_enroll_min_similarity: float = 0.30
    face_min_det_score: float = 0.65
    face_min_face_pixels: int = 120
    face_max_image_pixels: int = 20_000_000
    max_upload_mb: int = 8

    login_max_attempts: int = 8
    login_window_seconds: int = 300

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "nao-responda@lins.local"
    smtp_use_tls: bool = True

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def database_path(self) -> Path:
        url = self.database_url
        if url.startswith("sqlite:///./"):
            return BASE_DIR / url.removeprefix("sqlite:///./")
        if url.startswith("sqlite:///"):
            return Path(url.removeprefix("sqlite:///"))
        return BASE_DIR / "data" / "app.db"

    @property
    def model_root_path(self) -> Path:
        path = Path(self.face_model_root)
        return path if path.is_absolute() else BASE_DIR / path

    @property
    def https_cert_path(self) -> Path:
        path = Path(self.https_cert_file)
        return path if path.is_absolute() else BASE_DIR / path

    @property
    def https_key_path(self) -> Path:
        path = Path(self.https_key_file)
        return path if path.is_absolute() else BASE_DIR / path

    def resolved_database_url(self) -> str:
        if self.database_url.startswith("sqlite:///./"):
            return f"sqlite:///{(BASE_DIR / self.database_url.removeprefix('sqlite:///./')).as_posix()}"
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
