"""Centralised path configuration for the CVMakr project."""

from __future__ import annotations

import os
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PACKAGE_ROOT.parent
PROJECT_ROOT = SRC_ROOT.parent

DATA_DIR = PROJECT_ROOT / "data"
CONTENT_DIR = DATA_DIR / "content"
TEMPLATE_DIR = DATA_DIR / "templates"
ASSET_DIR = DATA_DIR / "assets"

VAR_DIR = PROJECT_ROOT / "var"
OUTPUT_DIR = VAR_DIR / "output"
RESUME_OUTPUT_DIR = OUTPUT_DIR / "resumes"
CACHE_DIR = VAR_DIR / "cache"

DEFAULT_TEMPLATE = TEMPLATE_DIR / "base_resume.tex"
LOGO_PATH = ASSET_DIR / "logo.png"

EXPERIENCE_FILES = {
    "dassault": CONTENT_DIR / "Experience_Dassault.txt",
    "aimovement": CONTENT_DIR / "Experience_Aimovement.txt",
    "tnc": CONTENT_DIR / "Experience_TNC.txt",
    "lear": CONTENT_DIR / "Experience_Lear.txt",
}

PROJECTS_FILE = CONTENT_DIR / "projects.txt"
EXPERIENCES_FILE = CONTENT_DIR / "experiences.txt"
ASPIRATIONS_FILE = CONTENT_DIR / "personalaspirations.txt"
SKILLS_CSV = CONTENT_DIR / "myskills.csv"


def env(key: str, default: str | None = None) -> str | None:
    """Convenience wrapper around ``os.getenv``."""

    return os.getenv(key, default)


def ensure_runtime_dirs() -> None:
    """Ensure runtime folders exist."""

    for path in (DATA_DIR, CONTENT_DIR, TEMPLATE_DIR, ASSET_DIR, RESUME_OUTPUT_DIR, CACHE_DIR):
        path.mkdir(parents=True, exist_ok=True)

