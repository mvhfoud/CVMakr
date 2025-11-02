"""Resume generation helpers decoupled from the Streamlit UI."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Sequence

from langchain_community.callbacks import get_openai_callback

from cvmakr.agents.highlight import wrapper_agent
from cvmakr.agents.internships import run_internship_agent
from cvmakr.agents.projects import projects_agent, skills_verification
from cvmakr.agents.skills import run_skills_agent
from cvmakr.agents.summary import run_summary_agent
from cvmakr.templates.latex_loader import replace_placeholder_in_file_inplace
from cvmakr.utils.config import PROJECTS_FILE
from cvmakr.utils.latex import escape_latex_special_chars, transform_bullets
from cvmakr.utils.skills import normalize_skill_tags


executor = ThreadPoolExecutor(max_workers=4)


async def run_in_executor(func, *args):
    """Run a synchronous function in the shared executor."""

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args)


async def _execute_with_metrics(
    step_name: str,
    func: Callable[..., str],
    *args,
) -> tuple[str, dict[str, Any]]:
    start = perf_counter()
    with get_openai_callback() as cb:
        result = await run_in_executor(func, *args)
    duration = perf_counter() - start
    metrics = {
        "step": step_name,
        "duration_seconds": duration,
        "prompt_tokens": cb.prompt_tokens,
        "completion_tokens": cb.completion_tokens,
        "total_tokens": cb.total_tokens,
    }
    return result, metrics


async def process_resume_parallel(
    job_description: str,
    resume_path: Path,
    internships: Sequence[tuple[Path, int]],
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """Fill the resume template by running the multi-phase pipeline.

    The function keeps the existing placeholder-based template updates but now
    reports progress through the optional callback so it can run outside the UI
    thread. It returns the generated LaTeX snippets for later display.
    """

    total_steps = 7
    step = 0
    metrics: list[dict[str, Any]] = []

    if progress_callback:
        progress_callback(step, total_steps, "queued")

    internship_tasks = [
        _execute_with_metrics(
            f"internship_{idx}",
            run_internship_agent,
            job_description,
            str(filename),
            count,
        )
        for idx, (filename, count) in enumerate(internships, start=1)
    ]
    project_task = _execute_with_metrics(
        "projects_generation",
        projects_agent,
        str(PROJECTS_FILE),
        job_description,
    )
    combined_tasks = internship_tasks + [project_task]

    if progress_callback:
        progress_callback(step, total_steps, "gathering_internships")

    results = await asyncio.gather(*combined_tasks)

    sections: dict[str, str] = {}

    for (result, metric), idx in zip(results[:-1], range(1, len(internships) + 1)):
        transformed = escape_latex_special_chars(transform_bullets(result))
        replace_placeholder_in_file_inplace(resume_path, idx + 3, transformed)
        sections[f"experience_{idx}"] = transformed
        metrics.append(metric)
        step += 1
        if progress_callback:
            progress_callback(step, total_steps, f"experience_{idx}")

    raw_projects, project_metrics = results[-1]
    raw_projects = wrapper_agent(raw_projects, job_description)
    safe_projects = escape_latex_special_chars(raw_projects)
    replace_placeholder_in_file_inplace(resume_path, 8, safe_projects)
    step += 1
    sections["projects"] = safe_projects
    metrics.append(project_metrics)
    if progress_callback:
        progress_callback(step, total_steps, "projects")

    skills_raw, skills_metrics = await _execute_with_metrics(
        "skills_generation",
        run_skills_agent,
        job_description,
        str(resume_path),
        "",
    )
    verified_skills, skills_verify_metrics = await _execute_with_metrics(
        "skills_verification",
        skills_verification,
        skills_raw,
        job_description,
    )
    skills_tex = normalize_skill_tags(verified_skills)
    skills_tex = escape_latex_special_chars(skills_tex)
    replace_placeholder_in_file_inplace(resume_path, 9, skills_tex)
    step += 1
    sections["skills"] = skills_tex
    metrics.extend([skills_metrics, skills_verify_metrics])
    if progress_callback:
        progress_callback(step, total_steps, "skills")

    summary_tex, summary_metrics = await _execute_with_metrics(
        "summary_generation",
        run_summary_agent,
        job_description,
        str(resume_path),
    )
    summary_safe = escape_latex_special_chars(summary_tex)
    replace_placeholder_in_file_inplace(resume_path, 0, summary_safe)
    step += 1
    sections["summary"] = summary_safe
    metrics.append(summary_metrics)
    if progress_callback:
        progress_callback(step, total_steps, "summary")

    if progress_callback:
        progress_callback(total_steps, total_steps, "completed")

    return sections, metrics
