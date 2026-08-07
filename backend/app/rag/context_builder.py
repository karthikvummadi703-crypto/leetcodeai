"""
Context builder — renders retrieved documents into clean, AI-readable
markdown snippets.
"""

from __future__ import annotations

from typing import Any

from app.core import get_logger
from app.rag.loader import DataDocument

log = get_logger("rag.context")

# Section header → raw field names to pull from a document.
_SECTION_FIELDS: list[tuple[str, tuple[str, ...]]] = [
    ("Hints", ("hints", "approach_hints", "progressive_hints")),
    ("Common Mistakes", ("common_mistakes", "pitfalls", "gotchas")),
    ("Similar Problems", ("similar_problems", "related_problems", "recommended_problems")),
    ("Key Points", ("key_points", "important_points", "must_know")),
    ("Use Cases", ("use_cases", "when_to_use")),
    ("How To Identify", ("how_to_identify", "identification", "recognition")),
    ("Template", ("template", "framework", "skeleton", "pseudocode")),
]

# Solution tiers → human label. Documents may store code under a
# "solutions" dict with one entry per tier.
_SOLUTION_TIERS: list[tuple[str, str]] = [
    ("brute_force", "Brute Force"),
    ("better", "Better"),
    ("optimal", "Optimal"),
]


def _as_lines(value: Any) -> list[str]:
    """Coerce a raw field into a list of bullet lines."""
    if value is None:
        return []
    if isinstance(value, str):
        lines = [line.strip() for line in value.split("\n") if line.strip()]
        return lines if len(lines) > 1 else lines
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, dict):
        return [f"{k}: {v}".strip() for k, v in value.items() if str(v).strip()]
    return [str(value).strip()]


def _complexity_lines(doc: DataDocument) -> list[str]:
    """Extract time/space complexity lines when present."""
    lines: list[str] = []
    time_c = doc.sections.get("time_complexity") or doc.sections.get("time")
    space_c = doc.sections.get("space_complexity") or doc.sections.get("space")
    if time_c:
        lines.append(f"Time: {time_c}")
    if space_c:
        lines.append(f"Space: {space_c}")
    if doc.sections.get("complexity"):
        lines.append(str(doc.sections["complexity"]))
    return lines


def _code_lines(value: Any) -> list[str]:
    """Coerce a code payload (string or list of lines) into fenced code."""
    if value is None:
        return []
    if isinstance(value, list):
        code = "\n".join(str(line) for line in value if str(line).strip() or line == "")
        if code.strip():
            return [f"```python\n{code}\n```"]
    text = str(value).strip()
    if text:
        return [f"```python\n{text}\n```"]
    return []


def _solutions_lines(doc: DataDocument) -> list[str]:
    """
    Render a document's per-tier solutions (brute force / better / optimal)
    as readable context. Each tier renders its explanation, fenced code,
    and complexity when present.
    """
    solutions = doc.sections.get("solutions")
    if not isinstance(solutions, dict):
        return []

    lines: list[str] = []
    for key, label in _SOLUTION_TIERS:
        tier = solutions.get(key)
        if not isinstance(tier, dict):
            continue
        parts: list[str] = []
        approach = tier.get("description") or tier.get("approach") or tier.get("explanation")
        if approach:
            parts.append(str(approach).strip())
        parts.extend(_code_lines(tier.get("code")))
        complexity = []
        if tier.get("time_complexity"):
            complexity.append(f"Time: {tier['time_complexity']}")
        if tier.get("space_complexity"):
            complexity.append(f"Space: {tier['space_complexity']}")
        if complexity:
            parts.append(" | ".join(complexity))
        if parts:
            lines.append(f"**{label}:**")
            lines.extend(parts)
    return lines


def format_document(doc: DataDocument) -> str:
    """
    Render a single document as clean, readable context text.

    Never passes the raw JSON to the model — only the curated fields are
    turned into markdown-style bullet points.
    """
    parts: list[str] = []
    header = doc.title

    if doc.number is not None:
        header = f"{header} (#{doc.number})"

    meta: list[str] = []
    if doc.difficulty:
        meta.append(doc.difficulty)
    if doc.pattern:
        meta.append(f"Pattern: {doc.pattern}")
    if doc.algorithm:
        meta.append(f"Algorithm: {doc.algorithm}")
    if doc.tags:
        meta.append(f"Tags: {', '.join(doc.tags)}")

    parts.append(f"### {header}")
    if meta:
        parts.append(" | ".join(meta))

    if doc.description:
        parts.append(doc.description.strip())

    complexity = _complexity_lines(doc)
    if complexity:
        parts.append("*Complexity:*")
        parts.extend(f"- {line}" for line in complexity)

    solutions = _solutions_lines(doc)
    if solutions:
        parts.append("**Solutions (Brute Force → Better → Optimal):**")
        parts.extend(solutions)

    for label, keys in _SECTION_FIELDS:
        value = None
        for key in keys:
            if key in doc.sections:
                value = doc.sections[key]
                break
        lines = _as_lines(value) if value is not None else []
        if lines:
            parts.append(f"**{label}:**")
            parts.extend(f"- {line}" for line in lines)

    return "\n".join(parts).strip()
