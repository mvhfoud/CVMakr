"""Utilities to manipulate LaTeX snippets safely."""

from __future__ import annotations

import re


def escape_latex_special_chars(text: str) -> str:
    """Escape LaTeX meta-characters ahead of injection into templates."""

    text = re.sub(r"(?<!\\)&", r"\&", text)
    text = re.sub(r"(?<!\\)%", r"\%", text)
    text = re.sub(r"(?<!\\)\$", r"\$", text)
    text = re.sub(r"(?<!\\)#", r"\#", text)
    text = re.sub(r"(?<!\\)~", r"\textasciitilde{}", text)
    text = re.sub(r"(?<!\\)\^", r"\textasciicircum{}", text)
    return text


def transform_bullets(text: str) -> str:
    """
    Convert custom "-*" bullet markers into LaTeX ``\\item`` entries.

    The original monolith relied on inline replacements; this helper keeps parity
    while living in a reusable spot.
    """

    flat = text.replace("\n", " ")
    parts = [p.strip() for p in re.split(r"-\*\s*", flat) if p.strip()]
    if not parts:
        return ""

    output = "\n\\item{" + parts[0]
    for idx, part in enumerate(parts[1:], start=1):
        if idx == 1:
            output += "} \n\\item{" + part
        else:
            output += "} \n\\item{" + part
    output += "}"
    return output


_CONTROL_SEQUENCE = re.compile(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^}]*\})?")
_CURLY_BRACES = re.compile(r"[{}]")


def strip_latex(text: str) -> str:
    """Return a rough plain-text version of LaTeX content."""

    no_commands = _CONTROL_SEQUENCE.sub(" ", text)
    flattened = _CURLY_BRACES.sub(" ", no_commands)
    flattened = re.sub(r"\s+", " ", flattened)
    return flattened.strip()
