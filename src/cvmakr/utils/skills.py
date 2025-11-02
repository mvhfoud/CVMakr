"""Helpers to post-process grouped LaTeX skill sections."""

from __future__ import annotations

import re
from typing import Iterable, List, Sequence, Tuple, Union

MANDATORY_SKILLS = [
    "C++",
    "Python",
    "Bash",
    "CUDA",
    "GIT",
    "FASTAPI",
    "Docker",
    "Kubernetes",
    "React",
    "PostgreSQL",
    "Redis",
    "Pytorch",
    "JavaScript",
    "RabbitMQ",
    "ORM",
    "Transfer protocols",
    "GCP",
    "Data Structures",
]

_CATEGORY_PATTERN = re.compile(r"\\textbf\{([^}]+)\}\s*:\s*(.+)")
_CATEGORY_HINTS = {
    "langages & frameworks": {"c++", "python", "fastapi", "react", "javascript"},
    "data & backend": {"docker", "kubernetes", "postgresql", "redis", "bash", "git", "rabbitmq", "orm", "transfer protocols", "GCP"},
    "ia/ml": {"pytorch", "cuda"},
    "soft skills": set(),
}


def _parse_skill_block(block: str) -> List[Tuple[str, List[str]]]:
    categories: List[Tuple[str, List[str]]] = []
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = _CATEGORY_PATTERN.match(line)
        if not match:
            continue
        title = match.group(1).strip()
        items_part = match.group(2).rstrip("\\").strip()
        items = [item.strip() for item in items_part.split(",") if item.strip()]
        if items:
            categories.append((title, items))
    return categories


def _normalise_categories(
    categories: Sequence[Tuple[str, List[str]]],
    mandatory: Iterable[str] | None = None,
) -> List[Tuple[str, List[str]]]:
    seen = set()
    buckets: List[Tuple[str, List[str]]] = []
    for title, items in categories:
        unique_items: List[str] = []
        for item in items:
            key = item.lower()
            if key not in seen:
                seen.add(key)
                unique_items.append(item)
        if unique_items:
            buckets.append((title, unique_items))

    mandatory_list = list(mandatory or MANDATORY_SKILLS)
    missing = [skill for skill in mandatory_list if skill.lower() not in seen]
    if missing:
        mutable_buckets = [[title, items] for title, items in buckets]
        for skill in missing:
            target_idx = None
            skill_key = skill.lower()
            for idx, (title, _) in enumerate(mutable_buckets):
                hints = _CATEGORY_HINTS.get(title.lower())
                if hints and skill_key in hints:
                    target_idx = idx
                    break
            if target_idx is None and mutable_buckets:
                target_idx = 0
            if target_idx is None:
                mutable_buckets.append(["Competences cles", [skill]])
            else:
                mutable_buckets[target_idx][1].append(skill)
        buckets = [(title, items) for title, items in mutable_buckets]

    return buckets


CategoryInput = Union[Tuple[str, List[str]], dict, object]


def format_skill_categories(
    categories: Sequence[CategoryInput],
    mandatory: Iterable[str] | None = None,
) -> str:
    """Build LaTeX lines from a structured category list."""

    processed: List[Tuple[str, List[str]]] = []
    for category in categories:
        if isinstance(category, tuple):
            title, items = category
        elif isinstance(category, dict):
            title = category.get("title", "")
            items = category.get("items", [])
        else:
            title = getattr(category, "title", "")
            items = getattr(category, "items", [])
        item_list = [item.strip() for item in items if item and item.strip()]
        if title and item_list:
            processed.append((title.strip(), item_list))

    normalised = _normalise_categories(processed, mandatory=mandatory)
    lines = [
        f"\\textbf{{{title}}} : {', '.join(items)} \\\\"
        for title, items in normalised
    ]
    return "\n".join(lines)


def normalize_skill_tags(block: str, mandatory: Iterable[str] | None = None) -> str:
    """Normalise an existing LaTeX block of grouped skills."""

    categories = _parse_skill_block(block)
    if not categories:
        return block
    return format_skill_categories(categories, mandatory=mandatory)
