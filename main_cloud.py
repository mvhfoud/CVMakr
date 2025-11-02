"""Legacy entrypoint maintained for backwards compatibility."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from cvmakr.agents.compliance import coherence_review, extract_mandatory_keywords
from cvmakr.agents.improvement import refine_resume_with_feedback
from cvmakr.agents.highlight import wrapper_agent
from cvmakr.agents.internships import run_internship_agent
from cvmakr.agents.letter import motivation_letter_agent
from cvmakr.agents.projects import projects_agent, skills_verification
from cvmakr.agents.skills import run_courses_agent, run_skills_agent
from cvmakr.agents.summary import run_summary_agent
from cvmakr.app.streamlit_app import main as streamlit_main
from cvmakr.pipelines.resume_builder import process_resume_parallel, run_in_executor
from cvmakr.services.google import (
    FOLDER_ID,
    SHEET_ID,
    append_to_sheet,
    init_services,
    mount_drive,
    oauth_creds,
    upload_to_drive,
)
from cvmakr.templates.latex_loader import replace_placeholder_in_file_inplace
from cvmakr.utils.config import (
    ASPIRATIONS_FILE,
    DEFAULT_TEMPLATE,
    EXPERIENCE_FILES,
    EXPERIENCES_FILE,
    LOGO_PATH,
    PROJECTS_FILE,
    RESUME_OUTPUT_DIR,
)
from cvmakr.utils.latex import escape_latex_special_chars, strip_latex, transform_bullets
from cvmakr.utils.skills import normalize_skill_tags
from cvmakr.utils.text import parse_first_line_column

main = streamlit_main

__all__ = [
    "append_to_sheet",
    "escape_latex_special_chars",
    "extract_mandatory_keywords",
    "EXPERIENCE_FILES",
    "EXPERIENCES_FILE",
    "FOLDER_ID",
    "LOGO_PATH",
    "mount_drive",
    "motivation_letter_agent",
    "oauth_creds",
    "parse_first_line_column",
    "process_resume_parallel",
    "projects_agent",
    "replace_placeholder_in_file_inplace",
    "RESUME_OUTPUT_DIR",
    "run_courses_agent",
    "run_in_executor",
    "run_internship_agent",
    "normalize_skill_tags",
    "run_skills_agent",
    "run_summary_agent",
    "SHEET_ID",
    "skills_verification",
    "strip_latex",
    "streamlit_main",
    "transform_bullets",
    "upload_to_drive",
    "wrapper_agent",
    "coherence_review",
    "refine_resume_with_feedback",
]

if __name__ == "__main__":
    main()
