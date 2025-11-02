"""Helpers to derive a human-friendly identifier for resume jobs."""

from __future__ import annotations

import json
import re
from typing import Tuple

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You extract concise metadata from job descriptions. "
                "Given a snippet of text, respond with a JSON object containing "
                '`"company"` and `"role"` keys. '
                'If either value is unknown, return "unknown". No explanations.'
            ),
        ),
        (
            "human",
            "Snippet: {snippet}\n\nReturn JSON with company and role.",
        ),
    ]
)


def extract_job_metadata(job_description: str) -> Tuple[str, str]:
    """Return (company, role) inferred from the first 100 characters."""

    snippet = (job_description or "")[:100]
    if not snippet.strip():
        return "unknown", "unknown"

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0, max_tokens=64)
    messages = _PROMPT.format_messages(snippet=snippet)
    try:
        response = llm.invoke(messages)
    except Exception:
        return "unknown", "unknown"

    try:
        data = json.loads(response.content)
    except (json.JSONDecodeError, AttributeError, TypeError):
        return "unknown", "unknown"

    company = str(data.get("company", "unknown")).strip() or "unknown"
    role = str(data.get("role", "unknown")).strip() or "unknown"
    return company, role


def slugify_metadata(company: str, role: str) -> str:
    """Build a compact identifier from company and role names."""

    parts = [company or "", role or ""]
    combined = "-".join(p for p in parts if p and p.lower() != "unknown").lower()
    combined = combined[:80]  # stay compact for storage
    slug = re.sub(r"[^a-z0-9]+", "-", combined).strip("-")
    return slug or "job"
