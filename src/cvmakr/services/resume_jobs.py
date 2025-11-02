"""Pure functions that prepare resume generation jobs for the worker."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Optional

from langchain_community.callbacks import get_openai_callback

from cvmakr.agents.compliance import coherence_review, extract_mandatory_keywords
from cvmakr.agents.improvement import refine_resume_with_feedback
from cvmakr.agents.letter import motivation_letter_agent
from cvmakr.pipelines.resume_builder import process_resume_parallel
from cvmakr.services.google import (
    FOLDER_ID,
    append_to_sheet,
    ensure_google_credentials,
    mount_drive,
    upload_to_drive,
)
from cvmakr.services.job_logging import log_job_metrics
from cvmakr.services.storage import copy_template
from cvmakr.utils.config import (
    ASPIRATIONS_FILE,
    DEFAULT_TEMPLATE,
    EXPERIENCE_FILES,
    EXPERIENCES_FILE,
    PROJECTS_FILE,
    RESUME_OUTPUT_DIR,
    ensure_runtime_dirs,
)
from cvmakr.utils.latex import escape_latex_special_chars, strip_latex


@dataclass
class ResumeJobPayload:
    """Input data required to generate a resume."""

    job_description: str
    language_code: str
    offer_link: str
    generate_letter: bool = False
    job_id: str | None = None
    company_name: str | None = None
    role_title: str | None = None


def _resolve_output_dir() -> Path:
    mount_drive()
    output_dir = RESUME_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _evaluate_resume(job_description: str, resume_tex: str, letter_text: str | None) -> dict:
    plain = strip_latex(resume_tex)
    if letter_text:
        plain = f"{plain} {strip_latex(letter_text)}"

    keywords = extract_mandatory_keywords(job_description)
    deduped: list[str] = []
    seen: set[str] = set()
    for kw in keywords:
        key = kw.lower().strip()
        if key and key not in seen:
            seen.add(key)
            deduped.append(kw.strip())

    combined_lower = plain.casefold()
    missing = [kw for kw in deduped if kw.casefold() not in combined_lower]
    allowed_missing = max(0, int(len(deduped) * 0.2))
    review = coherence_review(job_description, plain)

    return {
        "plain": plain,
        "keywords": deduped,
        "missing": missing,
        "allowed_missing": allowed_missing,
        "review": review,
    }


def build_resume_job(payload: ResumeJobPayload | dict[str, Any]) -> dict[str, Any]:
    """Create the resume, optional letter, and metadata for UI consumption."""

    if isinstance(payload, dict):
        payload = ResumeJobPayload(**payload)

    ensure_runtime_dirs()
    ensure_google_credentials()

    job_metrics: list[dict[str, Any]] = []
    job_id = payload.job_id

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    resume_filename = f"{timestamp}_CV_Youssef.txt"
    letter_filename = f"{timestamp}_ML_Youssef.txt"

    output_dir = _resolve_output_dir()
    resume_path = output_dir / resume_filename
    copy_template(DEFAULT_TEMPLATE, resume_path)

    letter_text: Optional[str] = None
    try:
        if payload.generate_letter:
            letter_start = perf_counter()
            with get_openai_callback() as cb_letter:
                letter_text = escape_latex_special_chars(
                    motivation_letter_agent(
                        str(EXPERIENCES_FILE),
                        str(PROJECTS_FILE),
                        str(ASPIRATIONS_FILE),
                        payload.job_description,
                    )
                )
            letter_duration = perf_counter() - letter_start
            job_metrics.append(
                {
                    "step": "letter_generation",
                    "duration_seconds": letter_duration,
                    "prompt_tokens": cb_letter.prompt_tokens,
                    "completion_tokens": cb_letter.completion_tokens,
                    "total_tokens": cb_letter.total_tokens,
                }
            )

        internships = [
            (EXPERIENCE_FILES["dassault"], 3),
            (EXPERIENCE_FILES["aimovement"], 3),
            (EXPERIENCE_FILES["tnc"], 2),
            (EXPERIENCE_FILES["lear"], 1),
        ]

        sections, pipeline_metrics = asyncio.run(
            process_resume_parallel(
                payload.job_description,
                resume_path,
                internships,
                progress_callback=None,
            )
        )
        job_metrics.extend(pipeline_metrics)

        resume_tex = resume_path.read_text(encoding="utf-8")

        compliance_start = perf_counter()
        with get_openai_callback() as cb_compliance:
            compliance = _evaluate_resume(payload.job_description, resume_tex, letter_text)
        compliance_duration = perf_counter() - compliance_start
        job_metrics.append(
            {
                "step": "compliance_evaluation",
                "duration_seconds": compliance_duration,
                "prompt_tokens": cb_compliance.prompt_tokens,
                "completion_tokens": cb_compliance.completion_tokens,
                "total_tokens": cb_compliance.total_tokens,
            }
        )

        authenticity_flags: list[str] = []
        if compliance["review"].human_score < 0.7:
            authenticity_flags.append(
                f"Score d'authenticite faible ({compliance['review'].human_score:.2f})."
            )
        authenticity_flags.extend(compliance["review"].risks)

        force_language = payload.language_code != "fr"
        needs_refine = (
            len(compliance["missing"]) > compliance["allowed_missing"]
            or bool(authenticity_flags)
            or force_language
        )

        resume_changes: list[str] = []
        added_keywords: list[str] = []
        refined = False

        if needs_refine:
            refine_start = perf_counter()
            with get_openai_callback() as cb_refine:
                refinement = refine_resume_with_feedback(
                    job_description=payload.job_description,
                    resume_latex=resume_tex,
                    missing_keywords=compliance["missing"],
                    authenticity_concerns=authenticity_flags,
                    language=payload.language_code,
                )
            refine_duration = perf_counter() - refine_start
            job_metrics.append(
                {
                    "step": "resume_refinement",
                    "duration_seconds": refine_duration,
                    "prompt_tokens": cb_refine.prompt_tokens,
                    "completion_tokens": cb_refine.completion_tokens,
                    "total_tokens": cb_refine.total_tokens,
                }
            )
            resume_tex = refinement.revised_resume
            resume_path.write_text(resume_tex, encoding="utf-8")
            resume_changes = refinement.applied_changes
            added_keywords = refinement.integrated_keywords
            post_refine_start = perf_counter()
            with get_openai_callback() as cb_post_refine:
                compliance = _evaluate_resume(payload.job_description, resume_tex, letter_text)
            post_refine_duration = perf_counter() - post_refine_start
            job_metrics.append(
                {
                    "step": "compliance_post_refine",
                    "duration_seconds": post_refine_duration,
                    "prompt_tokens": cb_post_refine.prompt_tokens,
                    "completion_tokens": cb_post_refine.completion_tokens,
                    "total_tokens": cb_post_refine.total_tokens,
                }
            )
            refined = True
        else:
            resume_changes = ["Aucun ajustement automatique requis."]
            added_keywords = []

        upload_start = perf_counter()
        try:
            upload_to_drive(resume_path, FOLDER_ID)
        except Exception as exc:  # pragma: no cover - surfaced in UI
            upload_error = repr(exc)
        else:
            upload_error = None
        upload_duration = perf_counter() - upload_start
        job_metrics.append(
            {
                "step": "resume_upload_drive",
                "duration_seconds": upload_duration,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }
        )

        letter_path: Optional[Path] = None
        letter_upload_error: Optional[str] = None
        if letter_text:
            letter_path = output_dir / letter_filename
            letter_path.write_text(letter_text, encoding="utf-8")
            letter_upload_start = perf_counter()
            try:
                upload_to_drive(letter_path, FOLDER_ID)
            except Exception as exc:  # pragma: no cover - surfaced in UI
                letter_upload_error = repr(exc)
            else:
                letter_upload_error = None
            letter_upload_duration = perf_counter() - letter_upload_start
            job_metrics.append(
                {
                    "step": "letter_upload_drive",
                    "duration_seconds": letter_upload_duration,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                }
            )
        else:
            letter_path = None
            letter_upload_error = None

        sheet_start = perf_counter()
        today = datetime.now().strftime("%Y-%m-%d")
        row = [payload.offer_link, today, resume_filename, "Application Sent"]
        append_to_sheet(row)
        sheet_duration = perf_counter() - sheet_start
        job_metrics.append(
            {
                "step": "sheet_append",
                "duration_seconds": sheet_duration,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }
        )

        result = {
            "resume_path": str(resume_path),
            "resume_filename": resume_filename,
            "resume_tex": resume_tex,
            "sections": sections,
            "compliance": compliance,
            "refined": refined,
            "resume_changes": resume_changes,
            "added_keywords": added_keywords,
            "upload_error": upload_error,
            "letter": {
                "filename": letter_filename,
                "path": str(letter_path) if letter_path else None,
                "content": letter_text,
                "upload_error": letter_upload_error,
            },
            "metrics": job_metrics,
            "metadata": {
                "company": payload.company_name or "unknown",
                "role": payload.role_title or "unknown",
                "job_id": payload.job_id or "job",
            },
        }
    finally:
        log_job_metrics(job_id, job_metrics)

    return result
