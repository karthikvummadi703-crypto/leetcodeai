"""
Build a complete LeetCode problem catalog.

Fetches the full problemset from LeetCode's public GraphQL API
(paginated) and writes a single compact JSON file that is later loaded
by the problem catalog / recommendation engine:

    backend/data/leetcode_catalog.json

Each entry contains the fields needed for problem lookup and next-step
recommendations:

    {
      "number": 1,
      "title": "Two Sum",
      "title_slug": "two-sum",
      "difficulty": "Easy",
      "acceptance": 0.5432,
      "paid_only": false,
      "has_solution": true,
      "topics": ["Array", "Hash Table"]
    }

Run from backend/:
    .venv\\Scripts\\python.exe scripts/build_leetcode_catalog.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx

LEETCODE_GRAPHQL = "https://leetcode.com/graphql"
PAGE_SIZE = 100
MAX_PROBLEMS = 5000
MAX_RETRIES = 5
BASE_DELAY_SECONDS = 3.0

# Fields of the problem list query. `total` is the overall number of
# problems so pagination can stop as soon as every problem is collected.
PROBLEMSET_QUERY = """
query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
  problemsetQuestionList: questionList(
    categorySlug: $categorySlug
    limit: $limit
    skip: $skip
    filters: $filters
  ) {
    total: totalNum
    questions: data {
      acRate
      difficulty
      questionId
      isPaidOnly
      status
      title
      titleSlug
      topicTags {
        name
        slug
      }
      hasSolution
    }
  }
}
"""


def _fetch_page(client: httpx.Client, skip: int, limit: int) -> dict[str, Any]:
    payload = {
        "operationName": "problemsetQuestionList",
        "query": PROBLEMSET_QUERY,
        "variables": {
            "categorySlug": "",
            "skip": skip,
            "limit": limit,
            "filters": {},
        },
    }
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.post(LEETCODE_GRAPHQL, json=payload)
            response.raise_for_status()
            data = response.json()
            if "errors" in data:
                raise RuntimeError(f"GraphQL errors: {data['errors']}")
            return data["data"]["problemsetQuestionList"]
        except Exception as exc:  # noqa: BLE001 - retryable network/HTTP errors
            last_error = exc
            delay = BASE_DELAY_SECONDS * (2 ** (attempt - 1))
            print(
                f"  retry {attempt}/{MAX_RETRIES} for skip={skip}: {exc} (waiting {delay:.0f}s)",
                flush=True,
            )
            time.sleep(delay)
    raise RuntimeError(f"Failed to fetch page at skip={skip}: {last_error}")


def fetch_all_problems() -> list[dict[str, Any]]:
    """Fetch every problem in the LeetCode problemset, paginated."""
    problems: list[dict[str, Any]] = []
    skip = 0
    total: int | None = None

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        while total is None or skip < total:
            page = _fetch_page(client, skip, PAGE_SIZE)
            questions = page.get("questions", [])
            if total is None:
                total = page.get("total", 0)
            if not questions:
                break
            problems.extend(questions)
            skip += len(questions)
            print(
                f"  fetched {len(problems)} / {total} problems (skip={skip})",
                flush=True,
            )
            if len(problems) >= MAX_PROBLEMS:
                break
            # Be gentle with the public API so we are not throttled.
            time.sleep(1.0)

    return problems


def normalize(question: dict[str, Any]) -> dict[str, Any]:
    """Keep only the fields the catalog + recommender actually need."""
    topics = [tag["name"] for tag in question.get("topicTags", []) if tag.get("name")]
    acceptance = question.get("acRate")
    if isinstance(acceptance, (int, float)):
        acceptance = round(float(acceptance), 4)

    return {
        "number": int(question["questionId"]),
        "title": question["title"],
        "title_slug": question["titleSlug"],
        "difficulty": question.get("difficulty", "Unknown"),
        "acceptance": acceptance,
        "paid_only": bool(question.get("isPaidOnly")),
        "has_solution": bool(question.get("hasSolution")),
        "topics": topics,
    }


def main() -> int:
    print("Fetching full LeetCode problemset from GraphQL API...", flush=True)
    try:
        raw = fetch_all_problems()
    except Exception as exc:  # noqa: BLE001 - report and exit cleanly
        print(f"ERROR: failed to fetch LeetCode problemset: {exc}", file=sys.stderr)
        return 1

    catalog = [normalize(q) for q in raw]
    catalog.sort(key=lambda p: p["number"])

    data_dir = Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    out_path = data_dir / "leetcode_catalog.json"
    out_path.write_text(
        json.dumps(catalog, indent=1, ensure_ascii=False),
        encoding="utf-8",
    )

    by_difficulty: dict[str, int] = {}
    for problem in catalog:
        by_difficulty[problem["difficulty"]] = by_difficulty.get(problem["difficulty"], 0) + 1

    print(f"\nWrote {len(catalog)} problems -> {out_path}")
    print("Difficulty breakdown:", by_difficulty)
    return 0


if __name__ == "__main__":
    sys.exit(main())
