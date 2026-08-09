"""Deterministic local intent rules.

Local fallback is intentionally simple and auditable. It is not the primary
classifier, but it keeps the pipeline useful when the AI provider is unavailable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas import ClassificationOutcome, IntentClassification

KEYWORD_RULES: dict[str, tuple[str, ...]] = {
    "demo_trial_counseling": (
        "human",
        "counselor",
        "call me",
        "phone",
        "demo",
        "trial",
    ),
    "course_pricing_payment": (
        "price",
        "fee",
        "cost",
        "payment",
        "installment",
        "koto",
        "taka",
    ),
    "recording_access": (
        "record",
        "recording",
        "recorded",
        "lms",
    ),
    "course_schedule_duration": (
        "schedule",
        "batch",
        "duration",
        "class kobe",
        "kobe start",
        "time",
    ),
    "course_list": (
        "course list",
        "all course",
        "courses",
        "ki ki course",
        "catalog",
    ),
    "career_guidance": (
        "confused",
        "career",
        "which course",
        "kon course",
        "suggest",
    ),
    "enrollment_admission": (
        "enroll",
        "admission",
        "join",
        "register",
    ),
    "prerequisite_fit": (
        "prerequisite",
        "requirement",
        "before start",
    ),
    "beginner_friendliness": (
        "beginner",
        "new",
        "zero knowledge",
        "basic",
    ),
    "instructor_info": (
        "instructor",
        "teacher",
        "mentor",
        "faculty",
    ),
    "irrelevant": (
        "weather",
        "cricket",
        "football",
        "movie",
        "politics",
        "news",
    ),
}


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "is",
    "me",
    "of",
    "on",
    "or",
    "please",
    "show",
    "the",
    "to",
    "with",
}

TOKEN_WEIGHT = 2.0
PHRASE_WEIGHT = 4.0


@dataclass(frozen=True)
class LocalIntentScore:
    intent: str
    score: float
    matched_terms: list[str]


def _normalize_text(text: str) -> str:
    """Convert any message into simple searchable text."""

    normalized = text.casefold()
    normalized = re.sub(r"[_\-/]+", " ", normalized)
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _tokenize(text: str, *, keep_stopwords: bool = False) -> set[str]:
    """Convert a message into unique searchable words."""

    tokens = set(_normalize_text(text).split())
    if keep_stopwords:
        return tokens
    return {token for token in tokens if token not in STOPWORDS}


def _split_keywords(keywords: tuple[str, ...]) -> tuple[set[str], tuple[str, ...]]:
    """Separate single-word keywords from multi-word phrase keywords."""

    token_keywords = {keyword for keyword in keywords if " " not in _normalize_text(keyword)}
    phrase_keywords = tuple(keyword for keyword in keywords if " " in _normalize_text(keyword))
    return token_keywords, phrase_keywords


COMPILED_KEYWORD_RULES: dict[str, tuple[set[str], tuple[str, ...]]] = {
    intent: _split_keywords(keywords) for intent, keywords in KEYWORD_RULES.items()
}


def _score_keywords(
    text: str,
    tokens: set[str],
    token_keywords: set[str],
    phrase_keywords: tuple[str, ...],
) -> tuple[float, list[str]]:
    """Score one intent's keywords against the user message."""

    matched_terms = sorted(tokens & token_keywords)
    score = len(matched_terms) * TOKEN_WEIGHT

    for phrase in phrase_keywords:
        normalized_phrase = _normalize_text(phrase)
        if normalized_phrase in text:
            matched_terms.append(phrase)
            score += PHRASE_WEIGHT

    return score, sorted(set(matched_terms))


def score_local_intents(
    text: str,
    allowed_intents: set[str] | frozenset[str] | None = None,
) -> list[LocalIntentScore]:
    """Return every local intent score, highest first."""

    normalized = _normalize_text(text)
    tokens = _tokenize(text)
    allowed = set(allowed_intents or [])
    scores: list[LocalIntentScore] = []

    for intent, (token_keywords, phrase_keywords) in COMPILED_KEYWORD_RULES.items():
        if allowed and intent not in allowed:
            continue

        score, matched_terms = _score_keywords(
            normalized,
            tokens,
            token_keywords,
            phrase_keywords,
        )
        scores.append(
            LocalIntentScore(
                intent=intent,
                score=round(score, 2),
                matched_terms=matched_terms,
            )
        )

    return sorted(scores, key=lambda item: (-item.score, item.intent))


def best_local_intent_score(
    text: str,
    allowed_intents: set[str] | frozenset[str] | None = None,
) -> LocalIntentScore:
    scores = score_local_intents(text, allowed_intents)
    if not scores:
        return LocalIntentScore(intent="unknown", score=0.0, matched_terms=[])
    return scores[0]


def local_fallback_outcome(
    text: str,
    reason: str,
    allowed_intents: set[str] | frozenset[str] | None = None,
) -> ClassificationOutcome:
    best_score = best_local_intent_score(text, allowed_intents)

    if best_score.score > 0:
        return ClassificationOutcome(
            result=IntentClassification(
                intent=best_score.intent,
                confidence="high",
                reason=(
                    "Matched local terms "
                    f"{', '.join(best_score.matched_terms)} after fallback: {reason}"
                ),
            ),
            source="local",
            status="fallback",
            routing_mode="ai_fallback",
            local_score=best_score.score,
            matched_terms=best_score.matched_terms,
        )

    return ClassificationOutcome(
        result=IntentClassification(
            intent="unknown",
            confidence="low",
            reason=f"No local rule matched after fallback: {reason}",
        ),
        source="local",
        status="fallback",
        routing_mode="ai_fallback",
        local_score=0.0,
        matched_terms=[],
    )
