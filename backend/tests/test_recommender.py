"""
Tests for the next-problem recommendation engine.
"""

from app.problems.recommender import analyze_solved, recommend_next


def test_recommend_next_excludes_solved():
    recs = recommend_next({"two-sum"}, count=5, seed=1)
    assert recs
    assert len(recs) == 5
    slugs = {p["title_slug"] for p in recs}
    assert "two-sum" not in slugs
    assert all(not p["paid_only"] for p in recs)


def test_recommend_next_deterministic_with_seed():
    first = recommend_next(set(), count=5, seed=42)
    second = recommend_next(set(), count=5, seed=42)
    assert [p["number"] for p in first] == [p["number"] for p in second]


def test_recommend_next_difficulty_filter():
    recs = recommend_next(set(), count=5, difficulty="Hard", seed=7)
    assert recs
    assert all(p["difficulty"] == "Hard" for p in recs)


def test_recommend_next_invalid_difficulty():
    recs = recommend_next(set(), count=5, difficulty="Impossible", seed=7)
    assert recs


def test_analyze_solved_summarises_counts_and_topics():
    solved = [
        {"title_slug": "two-sum", "difficulty": "Easy", "topics": ["Array", "Hash Table"]},
        {"title_slug": "longest-substring-without-repeating-characters",
         "difficulty": "Medium", "topics": ["String", "Sliding Window"]},
        {"title_slug": "valid-parentheses", "difficulty": "Easy", "topics": ["Stack", "String"]},
    ]
    analysis = analyze_solved(solved)
    assert analysis["total_solved"] == 3
    assert analysis["by_difficulty"]["Easy"] == 2
    assert analysis["by_difficulty"]["Medium"] == 1
    assert "string" in analysis["topics_touched"]
