"""Deterministic local intent rules.

Local fallback is intentionally simple and auditable. It is not the primary
classifier, but it keeps the pipeline useful when the AI provider is unavailable.
"""

from __future__ import annotations

import re

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
}

# Convert text to lowercase-like normalized form.casefold() is a little stronger for text normalization. For English/Bangla-English text, both mostly work.
def _normalize_text(text: str) -> str:
    return text.casefold()

# Convert user query sentence into unique words. works only on user query
def _tokenize(text: str) -> set[str]:
    """Convert a message into unique searchable words."""

    return set(re.findall(r"\w+", _normalize_text(text)))

# It separates keywords into: single-word keywords & multi-word phrase keywords. Works only on KEYWORD_RULES-> the defined keywords
def _split_keywords(keywords: tuple[str, ...]) -> tuple[set[str], tuple[str, ...]]:
    token_keywords = {keyword for keyword in keywords if " " not in keyword}
    phrase_keywords = tuple(keyword for keyword in keywords if " " in keyword)
    return token_keywords, phrase_keywords

# Its the processed version of the KEYWORD_RULES(Converting to single word or multi-word). It prepares keyword rules once.
COMPILED_KEYWORD_RULES: dict[str, tuple[set[str], tuple[str, ...]]] = {
    intent: _split_keywords(keywords) for intent, keywords in KEYWORD_RULES.items()
}


# Find which keyword matched the user message.1st token match, then phrase match. 
def _matched_keyword(
    text: str,
    tokens: set[str],
    token_keywords: set[str],
    phrase_keywords: tuple[str, ...],
) -> str | None:
    token_match = tokens & token_keywords
    if token_match:
        return sorted(token_match)[0]

    for phrase in phrase_keywords:
        if phrase in text:
            return phrase

    return None


def local_fallback_outcome(
    text: str,
    reason: str,
    allowed_intents: set[str] | frozenset[str] | None = None,
) -> ClassificationOutcome:
    normalized = _normalize_text(text)
    tokens = _tokenize(text)
    allowed = set(allowed_intents or [])

    for intent, (token_keywords, phrase_keywords) in COMPILED_KEYWORD_RULES.items():
        if allowed and intent not in allowed:
            continue

        matched_keyword = _matched_keyword(
            normalized,
            tokens,
            token_keywords,
            phrase_keywords,
        )
        if matched_keyword:
            return ClassificationOutcome(
                result=IntentClassification(
                    intent=intent,
                    confidence="high",
                    reason=f"Matched local keyword '{matched_keyword}' after fallback: {reason}",
                ),
                source="local",
                status="fallback",
            )

    return ClassificationOutcome(
        result=IntentClassification(
            intent="unknown",
            confidence="low",
            reason=f"No local rule matched after fallback: {reason}",
        ),
        source="local",
        status="fallback",
    )
