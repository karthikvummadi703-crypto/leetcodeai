"""
Next-problem recommendation engine.

Given a user's set of solved LeetCode problems (slug + optional topic/difficulty
info), this module picks the most useful *unsolved* problems from the local
catalog. It nudges the user towards:

* topics they have not touched yet (weak / blind spots),
* the difficulty level right above their current comfort zone,
* high-acceptance, free, solvable problems with official solutions,
* a varied mix so recommendations stay fresh across calls.
"""

from __future__ import annotations

import random
import re
from typing import Any

from app.core import get_logger
from app.problems.catalog import Problem, get_catalog

log = get_logger("problems.recommender")

# Difficulty ladder for "next step" suggestions.
_DIFFICULTY_LADDER = ("Easy", "Medium", "Hard")

# Topics that are not classic DSA practice (mostly LeetCode's SQL / shell /
# dataframe problems). These are heavily penalised so recommendations stay
# focused on data structures & algorithms.
_NON_DSA_TOPICS = {
    "database",
    "pandas",
    "data frame",
    "shell",
    "sql",
}

# Title fragments that reveal non-DSA novelty problems ("Return Length of
# Arguments Passed", "Display the First Three Rows", ...).
_NON_DSA_TITLE_RE = re.compile(
    r"\b(rows|arguments passed|dataframe|data frame|objects count|"
    r"cells with odd|divide array|filter items|json deep equal|"
    r"is object empty|array prototype|function composition)\b",
    re.IGNORECASE,
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _normalize_slug(slug: str) -> str:
    """Normalise a problem slug for set membership."""
    return _normalize_text(slug)


def _normalize_text(text: str) -> str:
    return " ".join(_TOKEN_RE.findall(text.lower()))


def _curated_problem_numbers() -> set[int]:
    """
    Problem numbers that have an in-depth curated solution in the knowledge
    base (backend/data/leetcode/*.json). Used to gently boost the highest
    quality teaching material in recommendations.
    """
    numbers: set[int] = set()
    from app.rag import get_knowledge_base

    for doc in get_knowledge_base().documents:
        if doc.source == "leetcode" and doc.number is not None:
            numbers.add(doc.number)
    return numbers


_curated_numbers = _curated_problem_numbers()


def topic_counts_for(solved: list[dict[str, Any]]) -> dict[str, int]:
    """Count how many solved problems fall into each topic tag."""
    counts: dict[str, int] = {}
    for problem in solved:
        for topic in problem.get("topics", []) or []:
            topic = _normalize_text(str(topic))
            if topic:
                counts[topic] = counts.get(topic, 0) + 1
    return counts


def analyze_solved(
    solved: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Summarise a user's solved set for the AI prompt: per-difficulty counts,
    topic coverage, and the topics they have barely touched.
    """
    by_difficulty = {"Easy": 0, "Medium": 0, "Hard": 0}
    topics: set[str] = set()
    for problem in solved:
        difficulty = problem.get("difficulty") or "Unknown"
        if difficulty in by_difficulty:
            by_difficulty[difficulty] += 1
        topics.update(_normalize_text(t) for t in (problem.get("topics", []) or []))

    catalog_topics = {_normalize_text(t) for t in get_catalog().topics}
    weak_topics = sorted(topics - catalog_topics)

    return {
        "total_solved": len(solved),
        "by_difficulty": by_difficulty,
        "topics_touched": sorted(t for t in topics if t),
        "weak_topics": weak_topics,
    }


def recommend_next(
    solved_slugs: list[str] | set[str],
    solved_problems: list[dict[str, Any]] | None = None,
    *,
    count: int = 5,
    difficulty: str | None = None,
    seed: int | None = None,
) -> list[dict[str, Any]]:
    """
    Recommend ``count`` unsolved problems for the user.

    ``solved_slugs`` may be a list of title slugs; when ``solved_problems``
    (dicts with ``topics``/``difficulty``) is also given, topic coverage is
    used to target weak areas. ``seed`` makes recommendations reproducible.
    """
    solved_slugs = {_normalize_slug(s) for s in solved_slugs if s}
    catalog = get_catalog()

    candidates = [
        problem
        for problem in catalog.problems
        if _normalize_slug(problem.title_slug) not in solved_slugs and not problem.paid_only
    ]
    if not candidates:
        log.info("No unsolved free problems left in the catalog — returning empty set")
        return []

    if difficulty and difficulty.lower() in {d.lower() for d in _DIFFICULTY_LADDER}:
        candidates = [p for p in candidates if p.difficulty.lower() == difficulty.lower()]
        if not candidates:
            return []

    # Topic coverage for weak-area targeting.
    solved_topics = topic_counts_for(solved_problems or [])
    catalog_topics = {_normalize_text(t) for t in catalog.topics}
    touched_topics = {t for t in solved_topics if t in catalog_topics}

    difficulty_counts = {"Easy": 0, "Medium": 0, "Hard": 0}
    for slug in solved_slugs:
        problem = catalog.get_by_slug(slug)
        if problem:
            difficulty_counts[problem.difficulty] = difficulty_counts.get(problem.difficulty, 0) + 1

    rng = random.Random(seed)

    def _score(problem: Problem) -> tuple[float, float]:
        score = 0.0
        problem_topics = {_normalize_text(t) for t in problem.topics}

        # Avoid non-DSA categories (SQL / Pandas / Shell).
        non_dsa_hits = sum(1 for t in problem_topics if t in _NON_DSA_TOPICS)
        if non_dsa_hits:
            score -= 40.0 * non_dsa_hits
        # Problems with no topic tags are usually novelty / JS / dataframe
        # tasks — not core DSA practice.
        if not problem_topics:
            score -= 25.0
        if _NON_DSA_TITLE_RE.search(problem.title):
            score -= 25.0

        # Curated problems that have an in-depth solution in the knowledge
        # base get a gentle boost — they are the best teaching material.
        if problem.number in _curated_numbers:
            score += 8.0

        # Untouched topic -> big boost (it is a blind spot).
        new_topics = problem_topics - touched_topics
        if new_topics:
            score += 12.0
        # Topics with very few solved problems -> moderate boost.
        weak_topic_hits = sum(
            8.0 for t in problem_topics & touched_topics if solved_topics.get(t, 0) <= 1
        )
        score += weak_topic_hits
        # Difficulty targeting: push the user one rung up from their comfort
        # zone, favouring the difficulty level they have solved least.
        solved_total = sum(difficulty_counts.values())
        if solved_total:
            representation = difficulty_counts.get(problem.difficulty, 0) / solved_total
            score += (1.0 - representation) * 8.0
        else:
            score += 6.0 if problem.difficulty == "Easy" else 0.0
        # Prefer problems with official solutions and high acceptance.
        if problem.has_solution:
            score += 3.0
        acceptance = problem.acceptance or 0.0
        score += acceptance * 12.0
        # Deterministic tie-break + jitter so recommendations vary.
        tiebreak = rng.random() * 3.0
        return (score + tiebreak, problem.number)

    ranked = sorted(candidates, key=_score, reverse=True)
    recommended = ranked[:count]

    log.info(
        "Recommended {n} next problems for a user with {solved} solved, "
        "difficulty={difficulty} (filtered candidates={total})",
        n=len(recommended),
        solved=len(solved_slugs),
        difficulty=difficulty or "auto",
        total=len(ranked),
    )
    return [problem.to_dict() for problem in recommended]
