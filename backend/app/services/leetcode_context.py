"""
Builds a compact markdown block describing a user's LeetCode account that is
injected into the AI prompt when the user asks about their own progress.
"""

from __future__ import annotations

from typing import Any


def _difficulty_line(title: str, breakdown: dict[str, int]) -> str:
    return (
        f"- {title}: {breakdown.get('total', 0)} "
        f"(Easy {breakdown.get('easy', 0)} / Medium {breakdown.get('medium', 0)} "
        f"/ Hard {breakdown.get('hard', 0)})"
    )


def build_account_context(
    username: str,
    snapshot: dict[str, Any],
    recommendations: list[dict[str, Any]],
) -> str:
    """Render the user's LeetCode data as a structured context block."""
    accepted = snapshot.get("accepted", {})
    progress = snapshot.get("progress", {})
    recent = snapshot.get("recent_ac") or []
    languages = snapshot.get("languages") or []
    contest = snapshot.get("contest")

    lines = [
        "## User's LeetCode Account",
        "",
        f"Username: `{username}`",
    ]

    if accepted:
        lines.append(_difficulty_line("Problems accepted", accepted))
    if progress.get("failed"):
        lines.append(_difficulty_line("Attempted but failed", progress["failed"]))
    if contest:
        lines.append(
            f"- Contest rating: {contest.get('rating', '—')} "
            f"(top {contest.get('top_percentage', '—')}%, "
            f"attended {contest.get('contests_attended', 0)} contests)"
        )
    if languages:
        top_langs = sorted(
            languages, key=lambda item: item.get("problems_solved", 0), reverse=True
        )[:3]
        lang_text = ", ".join(
            f"{item['language']} ({item['problems_solved']})" for item in top_langs
        )
        lines.append(f"- Top languages: {lang_text}")

    if recent:
        lines.append("")
        lines.append("### Recently solved")
        lines.extend(f"- {s['title']}" for s in recent[:12])

    if recommendations:
        lines.append("")
        lines.append("### Recommended next problems (from the local catalog)")
        lines.append(
            "These are unsolved problems chosen by the recommendation engine — use them to ground your suggestions:"
        )
        for problem in recommendations:
            topics = ", ".join(problem.get("topics") or []) or "—"
            lines.append(
                f"- {problem.get('number')}. {problem.get('title')} "
                f"({problem.get('difficulty')}) — {topics} — "
                f"https://leetcode.com/problems/{problem.get('title_slug')}/"
            )

    lines.append("")
    lines.append(
        "Analyse the user's solved problems, point out patterns and weak "
        "areas, and explain your recommended next steps. Answer in a friendly "
        "mentor tone."
    )
    return "\n".join(lines)
