"""
Local JSON knowledge-base loader.

The knowledge base lives under ``backend/data/`` and is organised into a
set of folders — ``leetcode/``, ``patterns/``, ``topics/``,
``algorithms/``, ``complexities/`` and ``roadmaps/``.

This module:

* recursively scans the data directory once at startup,
* loads every ``.json`` file,
* validates it against a lightweight per-category schema,
* skips invalid files gracefully (with a warning), and
* caches the normalised documents in memory for the lifetime of the process.

No file is ever re-read after the initial load.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.core import get_logger

log = get_logger("rag.loader")

# Root data directory: backend/data
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

# Folders that are scanned for knowledge-base JSON files.
SUPPORTED_CATEGORIES = (
    "leetcode",
    "patterns",
    "topics",
    "algorithms",
    "complexities",
    "roadmaps",
)


class DataDocument(BaseModel):
    """
    A single normalised knowledge-base entry ready for search.

    All raw JSON payloads are normalised into this shape so the retriever
    can score documents uniformly regardless of source folder.
    """

    doc_id: str = Field(..., description="Unique identifier within the KB")
    source: str = Field(..., description="Source category, e.g. 'leetcode'")
    file: str = Field(..., description="Relative path of the source JSON file")
    title: str = Field(..., description="Human readable title/name")
    number: int | None = Field(default=None, description="Problem number (LeetCode only)")
    difficulty: str | None = Field(default=None, description="Easy | Medium | Hard")
    tags: list[str] = Field(default_factory=list, description="Searchable tags/topics")
    pattern: str | None = Field(default=None, description="Primary pattern name")
    algorithm: str | None = Field(default=None, description="Primary algorithm name")
    description: str = Field(default="", description="Body / description text")
    sections: dict[str, Any] = Field(default_factory=dict, description="Remaining raw fields")
    index_text: str = Field(default="", description="Pre-built lowercase text used for scoring")

    @property
    def category(self) -> str:
        return self.source


# ─── Field extraction helpers ────────────────────────────────────

def _first_str(data: dict[str, Any], *keys: str) -> str | None:
    """Return the first non-empty string found under any of ``keys``."""
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _as_list(value: Any) -> list[str]:
    """Coerce a raw value (list, string, single value) into a list of strings."""
    if value is None:
        return []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            if isinstance(item, str):
                out.append(item.strip())
            elif isinstance(item, (int, float)):
                out.append(str(item))
        return [x for x in out if x]
    if isinstance(value, (list, tuple, set)):
        return [str(x).strip() for x in value if str(x).strip()]
    text = str(value).strip()
    if not text:
        return []
    if "," in text:
        return [part.strip() for part in text.split(",") if part.strip()]
    return [text]


def _first_list(data: dict[str, Any], *keys: str) -> list[str]:
    """Return the first non-empty list found under any of ``keys``."""
    for key in keys:
        value = data.get(key)
        if value is None:
            continue
        items = _as_list(value)
        if items:
            return items
    return []


def _flatten_text(value: Any, seen: set[int] | None = None) -> str:
    """Recursively flatten a JSON payload into a plain-text search index."""
    if seen is None:
        seen = set()
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_flatten_text(item, seen) for item in value)
    if isinstance(value, dict):
        parts: list[str] = []
        for k, v in value.items():
            if id(v) in seen:
                continue
            seen.add(id(v))
            parts.append(f"{k}: {_flatten_text(v, seen)}")
        return " ".join(parts)
    return str(value)


# ─── Normalisation ───────────────────────────────────────────────

def normalize_document(
    source: str,
    file: str,
    raw: dict[str, Any],
) -> DataDocument | None:
    """Normalise one raw JSON object into a :class:`DataDocument`.

    Returns ``None`` when the payload does not satisfy the minimal schema
    for its category (missing name/title and description).
    """
    title = _first_str(raw, "title", "name", "problem_name", "problem", "topic_name", "topic")
    description = _first_str(
        raw,
        "description",
        "problem_statement",
        "statement",
        "content",
        "overview",
        "summary",
        "about",
        "body",
    )

    if not title:
        log.warning("Skipping {file}: missing title/name", file=file)
        return None

    if not description and source != "roadmaps":
        log.warning("Skipping {file}: missing description/body", file=file)
        return None

    number = raw.get("number") or raw.get("problem_number") or raw.get("id")
    if isinstance(number, str):
        number = int(number) if number.isdigit() else None
    if not isinstance(number, int):
        number = None

    doc_id_raw = str(number) if number else title
    doc_id = hashlib.md5(f"{source}:{doc_id_raw}".encode("utf-8")).hexdigest()[:16]

    tags = _first_list(raw, "tags", "topics", "categories", "subtopics", "keywords")
    difficulty = _first_str(raw, "difficulty", "level")
    pattern = _first_str(raw, "pattern", "patterns", "primary_pattern")
    algorithm = _first_str(raw, "algorithm", "algorithms", "approach", "technique")

    # Everything left over is retained as structured sections for the
    # context builder (hints, common_mistakes, similar_problems, ...).
    known = {"title", "name", "problem_name", "problem", "topic_name", "topic"}
    known |= {
        "description", "problem_statement", "statement", "content", "overview",
        "summary", "about", "body", "number", "problem_number", "id",
        "tags", "topics", "categories", "subtopics", "keywords",
        "difficulty", "level", "pattern", "patterns", "primary_pattern",
        "algorithm", "algorithms", "approach", "technique",
    }
    sections = {k: v for k, v in raw.items() if k not in known}

    index_text = " ".join(
        filter(
            None,
            [
                title,
                difficulty or "",
                pattern or "",
                algorithm or "",
                " ".join(tags),
                str(number) if number is not None else "",
                _flatten_text(sections) if sections else "",
                description,
            ],
        )
    ).lower()

    return DataDocument(
        doc_id=doc_id,
        source=source,
        file=file,
        title=title,
        number=number,
        difficulty=difficulty,
        tags=tags,
        pattern=pattern,
        algorithm=algorithm,
        description=description,
        sections=sections,
        index_text=index_text,
    )


# ─── Knowledge base ──────────────────────────────────────────────

class KnowledgeBase:
    """In-memory repository of every valid JSON document in the data dir."""

    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self._data_dir = data_dir
        self._documents: list[DataDocument] = []
        self._loaded = False
        self._stats: dict[str, int] = {}

    # ── Loading ─────────────────────────────────────────────────

    def load(self) -> list[DataDocument]:
        """Scan the data directory once and cache the results in memory.

        Calling this multiple times is safe — the files are only read the
        first time. Returns the list of loaded documents.
        """
        if self._loaded:
            return self._documents

        self._documents = []
        self._stats = {}
        loaded_count = 0
        skipped_count = 0

        for category in SUPPORTED_CATEGORIES:
            category_dir = self._data_dir / category
            if not category_dir.exists():
                log.debug("Data folder missing, skipping: {path}", path=category_dir)
                continue

            category_docs: list[DataDocument] = []
            seen_ids: set[str] = set()

            for filepath in sorted(category_dir.rglob("*.json")):
                raw_data = self._read_json_file(filepath, category)
                if raw_data is None:
                    skipped_count += 1
                    continue

                entries = raw_data if isinstance(raw_data, list) else [raw_data]
                for entry in entries:
                    if not isinstance(entry, dict):
                        log.warning("Skipping non-object entry in {path}", path=filepath)
                        skipped_count += 1
                        continue
                    doc = normalize_document(category, str(filepath.relative_to(self._data_dir)), entry)
                    if doc is None:
                        skipped_count += 1
                        continue
                    if doc.doc_id in seen_ids:
                        continue
                    seen_ids.add(doc.doc_id)
                    category_docs.append(doc)

            self._documents.extend(category_docs)
            self._stats[category] = len(category_docs)
            loaded_count += len(category_docs)

        self._loaded = True
        log.info(
            "Knowledge base loaded: {total} documents from {data_dir} ({stats}) — skipped {skipped}",
            total=loaded_count,
            data_dir=self._data_dir,
            stats=self._stats,
            skipped=skipped_count,
        )
        return self._documents

    def _read_json_file(self, filepath: Path, category: str) -> Any | None:
        """Read and parse one JSON file, returning ``None`` on any failure."""
        try:
            content = filepath.read_text(encoding="utf-8")
            data = json.loads(content)
        except FileNotFoundError:
            log.warning("JSON file disappeared while loading: {path}", path=filepath)
            return None
        except json.JSONDecodeError as exc:
            log.warning("Invalid JSON in {path}: {msg}", path=filepath, msg=exc.msg)
            return None
        except OSError as exc:
            log.warning("Could not read {path}: {exc}", path=filepath, exc=exc)
            return None

        if data is None or data == {} and category != "roadmaps":
            log.warning("Empty JSON payload in {path}", path=filepath)
            return None
        return data

    # ── Accessors ───────────────────────────────────────────────

    @property
    def documents(self) -> list[DataDocument]:
        """The full cached list of documents (loads on first access)."""
        if not self._loaded:
            self.load()
        return self._documents

    @property
    def stats(self) -> dict[str, int]:
        """Per-category document counts."""
        if not self._loaded:
            self.load()
        return self._stats

    @property
    def is_loaded(self) -> bool:
        return self._loaded


# Module-level singleton so the whole process shares one cache.
_knowledge_base = KnowledgeBase()


def get_knowledge_base() -> KnowledgeBase:
    """Return the shared knowledge-base singleton."""
    return _knowledge_base


def warm_knowledge_base() -> KnowledgeBase:
    """Eagerly load the knowledge base (used at application startup)."""
    kb = get_knowledge_base()
    kb.load()
    return kb
