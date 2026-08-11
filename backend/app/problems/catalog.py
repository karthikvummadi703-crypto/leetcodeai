"""
Problem catalog — an in-memory index of every LeetCode problem.

Backed by ``backend/data/leetcode_catalog.json`` (a compact, vendorable
snapshot of the full problemset built by ``scripts/build_leetcode_catalog.py``).
It provides fast lookups by number / title / slug / topic and powers the
"what should I solve next" recommendation engine.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.core import get_logger

log = get_logger("problems.catalog")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
CATALOG_FILE = DATA_DIR / "leetcode_catalog.json"

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class Problem(BaseModel):
    """A single entry from the LeetCode problem catalog."""

    number: int = Field(..., description="LeetCode problem number")
    title: str = Field(..., description="Problem title")
    title_slug: str = Field(..., description="URL slug, e.g. two-sum")
    difficulty: str = Field(default="Unknown", description="Easy | Medium | Hard")
    acceptance: float | None = Field(default=None, description="Acceptance rate 0..1")
    paid_only: bool = Field(default=False, description="Requires LeetCode premium")
    has_solution: bool = Field(default=True, description="Official solution article exists")
    topics: list[str] = Field(default_factory=list, description="Topic tags")

    @property
    def url(self) -> str:
        return f"https://leetcode.com/problems/{self.title_slug}/"

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "title_slug": self.title_slug,
            "difficulty": self.difficulty,
            "acceptance": self.acceptance,
            "paid_only": self.paid_only,
            "has_solution": self.has_solution,
            "topics": self.topics,
            "url": self.url,
        }


class ProblemCatalog:
    """In-memory repository of all LeetCode problems."""

    def __init__(self, catalog_file: Path = CATALOG_FILE) -> None:
        self._file = catalog_file
        self._problems: list[Problem] = []
        self._by_number: dict[int, Problem] = {}
        self._by_slug: dict[str, Problem] = {}
        self._loaded = False

    # ── Loading ─────────────────────────────────────────────────

    def load(self) -> list[Problem]:
        """Load the catalog file once and cache the index."""
        if self._loaded:
            return self._problems

        if not self._file.exists():
            log.warning(
                "LeetCode catalog not found at {path} — run "
                "scripts/build_leetcode_catalog.py to generate it.",
                path=self._file,
            )
            self._loaded = True
            return self._problems

        try:
            raw = json.loads(self._file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            log.error("Failed to load LeetCode catalog: {exc}", exc=exc)
            self._loaded = True
            return self._problems

        self._problems = [Problem(**entry) for entry in raw if isinstance(entry, dict)]
        self._by_number = {p.number: p for p in self._problems}
        self._by_slug = {p.title_slug: p for p in self._problems}
        self._loaded = True

        log.info(
            "LeetCode catalog loaded: {total} problems from {path}",
            total=len(self._problems),
            path=self._file,
        )
        return self._problems

    # ── Accessors ───────────────────────────────────────────────

    @property
    def problems(self) -> list[Problem]:
        if not self._loaded:
            self.load()
        return self._problems

    @property
    def total(self) -> int:
        return len(self.problems)

    @property
    def topics(self) -> list[str]:
        """Every distinct topic tag across the catalog (sorted)."""
        topics: set[str] = set()
        for problem in self.problems:
            topics.update(problem.topics)
        return sorted(topics)

    def get_by_number(self, number: int) -> Problem | None:
        self.load()
        return self._by_number.get(number)

    def get_by_slug(self, slug: str) -> Problem | None:
        self.load()
        return self._by_slug.get(slug)

    def get_by_title(self, title: str) -> Problem | None:
        """Fuzzy title lookup (case-insensitive, token based)."""
        normalized = _normalize(title)
        if not normalized:
            return None
        best: tuple[int, Problem] | None = None
        for problem in self.problems:
            similarity = _similarity(normalized, _normalize(problem.title))
            if similarity > 0 and (best is None or similarity > best[0]):
                best = (similarity, problem)
        if best and best[0] >= 2:
            return best[1]
        return None

    def search(self, query: str, limit: int = 10) -> list[Problem]:
        """
        Search problems by number, title or topic.

        A bare number matches that problem exactly; otherwise problems
        are ranked by token overlap with title / slug / topics.
        """
        query = query.strip()
        if not query:
            return []

        if query.isdigit():
            problem = self.get_by_number(int(query))
            return [problem] if problem else []

        terms = _TOKEN_RE.findall(query.lower())
        if not terms:
            return []

        scored: list[tuple[int, Problem]] = []
        for problem in self.problems:
            title_tokens = set(_TOKEN_RE.findall(problem.title.lower()))
            slug_tokens = set(_TOKEN_RE.findall(problem.title_slug.lower()))
            topic_tokens = set()
            for topic in problem.topics:
                topic_tokens.update(_TOKEN_RE.findall(topic.lower()))
            score = sum(
                3 if t in title_tokens else 2 if t in slug_tokens else 1 if t in topic_tokens else 0
                for t in terms
            )
            if score:
                scored.append((score, problem))

        scored.sort(key=lambda item: (-item[0], item[1].number))
        return [problem for _, problem in scored[:limit]]


def _normalize(text: str) -> str:
    return " ".join(_TOKEN_RE.findall(text.lower()))


def _similarity(a: str, b: str) -> int:
    """Token-overlap count between two normalised strings."""
    a_tokens = set(a.split())
    b_tokens = set(b.split())
    if not a_tokens or not b_tokens:
        return 0
    return len(a_tokens & b_tokens)


# Module-level singleton so the whole process shares one index.
_catalog: ProblemCatalog | None = None


def get_catalog() -> ProblemCatalog:
    """Return the shared problem-catalog singleton (loads on first use)."""
    global _catalog
    if _catalog is None:
        _catalog = ProblemCatalog()
        _catalog.load()
    return _catalog


def warm_catalog() -> ProblemCatalog:
    """Eagerly load the catalog (used at application startup)."""
    catalog = get_catalog()
    catalog.load()
    return catalog


def search_problems(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Public helper returning catalog search results as plain dicts."""
    return [problem.to_dict() for problem in get_catalog().search(query, limit)]
