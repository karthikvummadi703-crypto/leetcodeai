"""
Tests for the agent decision engine.
"""

from app.agent.decision_engine import decide, Intent


def test_greeting_routes_to_llm_only():
    decision = decide("Hi there!")
    assert decision.intent == Intent.GREETING
    assert decision.strategy == "llm_only"


def test_thanks_routes_to_llm_only():
    decision = decide("Thank you so much!")
    assert decision.intent == Intent.GREETING
    assert decision.strategy == "llm_only"


def test_leetcode_question_routes_to_rag():
    decision = decide("Can you explain the Two Sum problem?")
    assert decision.intent == Intent.LEETCODE
    assert decision.strategy == "rag_plus_llm"


def test_dsa_question_routes_to_rag():
    decision = decide("What is the time complexity of binary search?")
    assert decision.intent == Intent.DSA
    assert decision.strategy == "rag_plus_llm"


def test_algorithm_question_routes_to_rag():
    decision = decide("How does Dijkstra's algorithm work?")
    assert decision.intent == Intent.ALGORITHM
    assert decision.strategy == "rag_plus_llm"


def test_programming_question_routes_to_llm_only():
    decision = decide("How do I write a for loop in JavaScript?")
    assert decision.intent == Intent.PROGRAMMING
    assert decision.strategy == "llm_only"


def test_off_topic_question_returns_message():
    decision = decide("Who won the football match yesterday?")
    assert decision.intent == Intent.OFF_TOPIC
    assert decision.strategy == "off_topic"
    assert decision.message


def test_short_words_do_not_false_positive():
    # 'ide' must not match inside 'president'.
    decision = decide("Who is the president?")
    assert decision.intent == Intent.OFF_TOPIC


def test_random_leetcode_problem_never_refused():
    # Problem names containing generic words (game, life, history, ...)
    # must route to RAG + LLM, never to the off-topic refusal.
    cases = [
        "Explain the Jump Game problem",
        "What is the Game of Life problem?",
        "How do I solve LRU Cache?",
        "Explain the Word Ladder problem",
        "How does Number of Islands work?",
    ]
    for query in cases:
        decision = decide(query)
        assert decision.intent != Intent.OFF_TOPIC, query
        assert decision.strategy == "rag_plus_llm", query


def test_problem_names_with_offtopic_vocab_not_refused():
    # Words that were once refusal triggers must no longer reject valid
    # coding questions.
    cases = [
        "What is the history of binary search?",
        "Explain the gossip protocol in distributed systems",
        "What is the name of that data structure?",
        "How would you design a shopping cart?",
        "Show me the relationship between graphs and trees",
    ]
    for query in cases:
        decision = decide(query)
        assert decision.intent != Intent.OFF_TOPIC, query


def test_clearly_off_topic_still_refused():
    decision = decide("What is the weather forecast for tomorrow?")
    assert decision.intent == Intent.OFF_TOPIC
