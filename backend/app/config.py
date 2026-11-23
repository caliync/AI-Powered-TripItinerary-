"""Settings read from environment variables, with defaults for local dev."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _env_url(name: str, default: str) -> str | None:
    return os.getenv(name, default) or None


@dataclass(frozen=True)
class Settings:
    db_path: Path = field(default_factory=lambda: Path(os.getenv("DB_PATH", BACKEND_DIR / "data" / "app.db")))
    seed_dir: Path = BACKEND_DIR / "data"
    # Public OSRM demo server: fine for beta testing, self-host before launch.
    # Set either URL to an empty string to turn that service off.
    osrm_url: str | None = field(default_factory=lambda: _env_url("OSRM_URL", "https://router.project-osrm.org"))
    nominatim_url: str | None = field(
        default_factory=lambda: _env_url("NOMINATIM_URL", "https://nominatim.openstreetmap.org"))
    # Nominatim's usage policy asks for an identifying User-Agent.
    user_agent: str = field(default_factory=lambda: os.getenv("HTTP_USER_AGENT", "calamba-trip-planner-beta/0.1"))
    http_timeout_s: float = 4.0
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(o for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o)
    )


def get_settings() -> Settings:
    return Settings()
