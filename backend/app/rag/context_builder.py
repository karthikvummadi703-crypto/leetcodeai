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
