"""Streamlit entrypoint for the CV & motivation letter generator."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv

from cvmakr.services.background_queue import JobRecord, ensure_worker, get_job, submit_job
from cvmakr.services.google import ensure_google_credentials
from cvmakr.services.job_metadata import extract_job_metadata, slugify_metadata
from cvmakr.services.resume_jobs import build_resume_job
from cvmakr.utils.config import LOGO_PATH, ensure_runtime_dirs


def _format_timestamp(ts: datetime | None) -> str:
    if not ts:
        return "-"
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def _section_title(key: str) -> str:
    if key == "summary":
        return "Summary"
    if key == "skills":
        return "Skills"
    if key == "projects":
        return "Projects"
    if key.startswith("experience_"):
        index = key.split("_")[1]
        return f"Experience #{index}"
    return key.replace("_", " ").title()


def _render_compliance(result: dict[str, Any]) -> None:
    compliance = result.get("compliance")
    if not compliance:
        return

    review = compliance["review"]
    missing = compliance["missing"]
    allowed_missing = compliance["allowed_missing"]
    keywords = compliance["keywords"]

    with st.expander("ATS & Authenticity Checks", expanded=False):
        if keywords:
            st.markdown(
                "**Critical keywords detected:** " + ", ".join(f"`{kw}`" for kw in keywords)
            )

        if missing and len(missing) > allowed_missing:
            st.warning(
                "Still missing keywords: " + ", ".join(f"`{kw}`" for kw in missing) + "."
            )
        elif missing:
            st.info(
                "Optional keywords not present "
                f"(tolerance {allowed_missing}): "
                + ", ".join(f"`{kw}`" for kw in missing)
            )
        else:
            st.success("All required keywords are covered.")

        if review.human_score < 0.7:
            st.warning(f"Authenticity flagged (score {review.human_score:.2f}).")
        else:
            st.success(f"Tone looks authentic (score {review.human_score:.2f}).")

        if review.risks:
            st.write("Risks to monitor:")
            for risk in review.risks:
                st.write(f"- {risk}")


def _render_letter(letter: dict[str, Any]) -> None:
    content = letter.get("content")
    if not content:
        return

    with st.expander("Motivation Letter", expanded=False):
        st.code(content, language="latex")

        letter_path = letter.get("path")
        if letter_path and Path(letter_path).exists():
            st.download_button(
                "Download Letter",
                data=Path(letter_path).read_bytes(),
                file_name=letter["filename"],
                mime="text/plain",
            )

        if letter.get("upload_error"):
            st.warning(f"Google Drive upload failed: {letter['upload_error']}")


def _render_resume_sections(sections: dict[str, str]) -> None:
    if not sections:
        return

    ordered_keys = ["summary", "skills", "projects"]
    experience_keys = sorted(
        [key for key in sections if key.startswith("experience_")],
        key=lambda x: int(x.split("_")[1]),
    )
    ordered_keys.extend(experience_keys)
    ordered_keys.extend(
        key for key in sections if key not in set(ordered_keys)
    )  # any extra keys

    for key in ordered_keys:
        content = sections.get(key)
        if not content:
            continue
        with st.expander(_section_title(key), expanded=False):
            st.code(content, language="latex")


def _render_completed_job(record: JobRecord) -> None:
    result = record.result or {}

    resume_path = result.get("resume_path")
    resume_filename = result.get("resume_filename", "resume.tex")

    metadata = result.get("metadata") or {}
    company = metadata.get("company", "unknown")
    role = metadata.get("role", "unknown")
    if company != "unknown" or role != "unknown":
        st.markdown(
            f"**Detected role:** {role if role != 'unknown' else 'N/A'} "
            f"@ {company if company != 'unknown' else 'N/A'}"
        )

    if resume_path and Path(resume_path).exists():
        st.download_button(
            "Download Resume",
            data=Path(resume_path).read_bytes(),
            file_name=resume_filename,
            mime="text/plain",
        )
    else:
        st.warning("Resume file not found on disk.")

    if result.get("upload_error"):
        st.warning(f"Google Drive upload failed: {result['upload_error']}")

    if result.get("refined"):
        st.info("Automatic refinement applied to the resume.")

    resume_changes = result.get("resume_changes") or []
    added_keywords = result.get("added_keywords") or []
    if resume_changes or added_keywords:
        with st.expander("Refinement Summary", expanded=False):
            if resume_changes:
                st.write("Changes:")
                for change in resume_changes:
                    st.write(f"- {change}")
            if added_keywords:
                st.write("Keywords added: " + ", ".join(added_keywords))

    _render_compliance(result)
    _render_resume_sections(result.get("sections", {}))
    _render_letter(result.get("letter", {}))

    metrics = result.get("metrics") or []
    if metrics:
        with st.expander("Job Metrics", expanded=False):
            st.write("Per-step timing and token usage:")
            for entry in metrics:
                duration = float(entry.get("duration_seconds", 0.0) or 0.0)
                prompt_tokens = int(entry.get("prompt_tokens", 0) or 0)
                completion_tokens = int(entry.get("completion_tokens", 0) or 0)
                total_tokens = int(entry.get("total_tokens", 0) or 0)
                step_name = entry.get("step", "unknown")
                st.write(
                    f"- {step_name}: {duration:.2f}s "
                    f"(prompt {prompt_tokens}, completion {completion_tokens}, total {total_tokens})"
                )

    resume_tex = result.get("resume_tex")
    if resume_tex:
        with st.expander("Full LaTeX Source", expanded=False):
            st.code(resume_tex, language="latex")


def _render_job(job_id: str, record: JobRecord) -> None:
    status_labels = {
        "queued": "[Queued]",
        "running": "[Processing]",
        "finished": "[Completed]",
        "failed": "[Failed]",
    }
    status = status_labels.get(record.status, record.status)

    metadata = {}
    if record.result and isinstance(record.result, dict):
        metadata = record.result.get("metadata") or {}
    session_label = st.session_state.job_labels.get(job_id, {})
    label = metadata.get("job_id") or session_label.get("slug") or job_id[:8]
    role = metadata.get("role") or session_label.get("role")
    company = metadata.get("company") or session_label.get("company")
    friendly_label = label
    if role and role != "unknown":
        friendly_label = role
        if company and company != "unknown":
            friendly_label = f"{role} @ {company}"
    elif company and company != "unknown":
        friendly_label = company

    if metadata:
        st.session_state.job_labels[job_id] = {
            "label": friendly_label,
            "slug": label,
            "company": company or "unknown",
            "role": role or "unknown",
        }

    with st.container():
        st.markdown(f"**{friendly_label}** (#{job_id[:8]}) - {status}")
        st.caption(
            f"Created: {_format_timestamp(record.created_at)} | "
            f"Started: {_format_timestamp(record.started_at)} | "
            f"Finished: {_format_timestamp(record.finished_at)}"
        )

        if record.status == "failed":
            st.error(record.error or "Unknown error.")
            return

        if record.status in {"queued", "running"}:
            st.info("Job is currently being processed. Refresh the page to update status.")
            return

        _render_completed_job(record)


def _initialise_state() -> None:
    if "tracked_jobs" not in st.session_state:
        st.session_state.tracked_jobs: list[str] = []
    if "last_submission" not in st.session_state:
        st.session_state.last_submission: dict[str, Any] | None = None
    if "job_labels" not in st.session_state:
        st.session_state.job_labels: dict[str, dict[str, str]] = {}


def main() -> None:
    """Render the Streamlit app."""

    load_dotenv()
    ensure_runtime_dirs()
    try:
        ensure_google_credentials()
    except Exception as exc:  # pragma: no cover - surface auth issues to UI
        st.error(f"Impossible de valider les identifiants Google : {exc}")
        st.stop()

    ensure_worker(build_resume_job, concurrency=3)
    _initialise_state()

    col1, col2 = st.columns([1, 2])
    with col1:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH))
    with col2:
        st.title("Resume & Motivation Letter Generator (LaTeX)")

    with st.form("resume_form"):
        job_description = st.text_area("Paste the job description here:", height=200)
        language_choice = st.selectbox(
            "Final resume language",
            options=["French", "English"],
            index=0,
        )
        offer_link = st.text_input("Paste the job offer URL here:")
        generate_letter = st.checkbox("Generate Motivation Letter")
        submitted = st.form_submit_button("Queue Resume Generation", type="primary")

    if submitted:
        if not job_description.strip():
            st.error("Please enter a job description before generating.")
        else:
            language_code = "fr" if language_choice == "French" else "en"
            company, role = extract_job_metadata(job_description)
            job_slug = slugify_metadata(company, role)
            payload = {
                "job_description": job_description,
                "language_code": language_code,
                "offer_link": offer_link,
                "generate_letter": bool(generate_letter),
                "job_id": job_slug,
                "company_name": company,
                "role_title": role,
            }
            task_id = submit_job(payload)
            st.session_state.tracked_jobs.insert(0, task_id)
            st.session_state.tracked_jobs = st.session_state.tracked_jobs[:10]
            label_text = job_slug
            if role != "unknown" or company != "unknown":
                role_part = role if role != "unknown" else ""
                company_part = company if company != "unknown" else ""
                label_text = (role_part + (" @ " if role_part and company_part else "") + company_part).strip()
            st.session_state.job_labels[task_id] = {
                "label": label_text or job_slug,
                "slug": job_slug,
                "company": company,
                "role": role,
            }
            st.session_state.last_submission = {
                "task_id": task_id,
                "language": language_choice,
                "queued_at": datetime.utcnow(),
                "label": label_text or job_slug,
            }
            st.success(
                f"Job queued successfully for {label_text or job_slug}. "
                f"Tracking ID: `{task_id}` - refresh to update its progress."
            )

    if st.session_state.last_submission:
        last = st.session_state.last_submission
        st.info(
            f"Latest submission `{last['task_id'][:8]}` "
            f"({last.get('label', 'job')}) "
            f"(language: {last['language']}) queued at "
            f"{_format_timestamp(last['queued_at'])}."
        )

    st.divider()
    st.subheader("Your Recent Jobs")

    if not st.session_state.tracked_jobs:
        st.info("No jobs queued yet. Submit the form above to start one.")
        return

    for job_id in st.session_state.tracked_jobs:
        record = get_job(job_id)
        if not record:
            st.warning(f"No record found for job `{job_id}`.")
            continue
        _render_job(job_id, record)


if __name__ == "__main__":
    main()
