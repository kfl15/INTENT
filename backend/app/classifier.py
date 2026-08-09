"""AI-first classifier with deterministic local fallback."""

from __future__ import annotations

import asyncio
import hashlib
import json

from openai import AsyncOpenAI

from app.cache import TTLCache
from app.config import get_settings
from app.fallback import best_local_intent_score, local_fallback_outcome
from app.schemas import ClassificationOutcome, IntentClassification
from app.taxonomy import INTENTS

_classification_cache: TTLCache[ClassificationOutcome] | None = None
_classification_cache_ttl: int | None = None
_llm_semaphore: asyncio.Semaphore | None = None
_llm_semaphore_limit: int | None = None


def _get_cache() -> TTLCache[ClassificationOutcome]:
    global _classification_cache, _classification_cache_ttl

    settings = get_settings()
    if _classification_cache is None or _classification_cache_ttl != settings.cache_ttl_seconds:
        _classification_cache = TTLCache[ClassificationOutcome](settings.cache_ttl_seconds)
        _classification_cache_ttl = settings.cache_ttl_seconds
    return _classification_cache


def clear_classification_cache() -> None:
    if _classification_cache is not None:
        _classification_cache.clear()


def _get_llm_semaphore() -> asyncio.Semaphore:
    global _llm_semaphore, _llm_semaphore_limit

    settings = get_settings()
    limit = max(settings.llm_max_concurrency, 1)
    if _llm_semaphore is None or _llm_semaphore_limit != limit:
        _llm_semaphore = asyncio.Semaphore(limit)
        _llm_semaphore_limit = limit
    return _llm_semaphore


def _cache_key(
    text: str,
    allowed_intents: set[str] | frozenset[str],
) -> str:
    settings = get_settings()
    payload = "|".join(
        [
            text.casefold().strip(),
            ",".join(sorted(allowed_intents)),
            settings.classification_strategy,
            str(settings.local_direct_min_score),
            settings.deepseek_model,
            "has-key" if settings.deepseek_api_key else "no-key",
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _local_direct_outcome(
    score,
) -> ClassificationOutcome:
    return ClassificationOutcome(
        result=IntentClassification(
            intent=score.intent,
            confidence="high",
            reason=f"Local score {score.score} matched terms: {', '.join(score.matched_terms)}.",
        ),
        source="local",
        status="success",
        routing_mode="local_direct",
        local_score=score.score,
        matched_terms=score.matched_terms,
    )


async def _classify_intent_with_controls(
    text: str,
    allowed_intents: set[str] | frozenset[str],
) -> IntentClassification:
    settings = get_settings()
    attempts = max(settings.llm_retry_count, 0) + 1
    last_error: Exception | None = None

    for _attempt in range(attempts):
        try:
            async with _get_llm_semaphore():
                return await asyncio.wait_for(
                    classify_intent_with_llm(text, allowed_intents),
                    timeout=settings.llm_timeout_seconds,
                )
        except Exception as exc:
            last_error = exc

    raise RuntimeError(str(last_error) if last_error else "AI classification failed")


# This function sends the user message to DeepSeek. DeepSeek returns predicted intent.
async def classify_intent_with_llm(
    text: str,
    allowed_intents: set[str] | frozenset[str],
) -> IntentClassification:
    settings = get_settings() # Load config from .env / environment

    if settings.llm_provider != "deepseek":
        raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")

    if not settings.deepseek_api_key:
        raise RuntimeError("No DeepSeek API key configured")

    # Take all global intents,keep only the intents allowed by this profile.
    active_intents = tuple(intent for intent in INTENTS if intent in allowed_intents)
    if not active_intents:
        raise RuntimeError("No active intents available for this profile")

    client = AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        timeout=settings.llm_timeout_seconds,
    )

    system = (
        "Classify the user's message using the supported intent taxonomy. "
        "Do not answer the user. Do not predict a separate relevance/category "
        "label; the backend derives that deterministically from the chosen "
        "intent. Use unknown when no supported intent precisely covers the "
        "message. Return valid JSON only with keys: intent, confidence, reason. "
        f"The only allowed intent values are: {', '.join(active_intents)}. "
        "The only allowed confidence values are: high, medium, low."
    )

    # Send request to DeepSeek and wait for response.
    response = await client.chat.completions.create(
        model=settings.deepseek_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
        max_tokens=200,
        temperature=0,
    )

    content = response.choices[0].message.content or "{}" # Get model text response.
    parsed = json.loads(content) # Convert JSON string to Python dictionary.
    classification = IntentClassification(**parsed) # Validate it with IntentClassification

    # Safety Condition
    if classification.intent not in active_intents:
        return IntentClassification(
            intent="unknown",
            confidence="low",
            reason="Model returned an intent outside the active profile.",
        )

    # Safety Condition
    if classification.confidence == "low":
        return IntentClassification(
            intent="unknown",
            confidence="low",
            reason="Low confidence classification forced to unknown.",
        )

    # FULL FLOW-> 
    # 1. load settings
    # 2. check provider/key
    # 3. build active intents
    # 4. create DeepSeek client
    # 5. send prompt
    # 6. parse JSON
    # 7. validate output
    # 8. force unknown if unsafe
    # 9. return intent

    return classification


# Main classifier function used by the pipeline, Decide AI or local fallback.
async def classify_intent(
    text: str,
    allowed_intents: set[str] | frozenset[str],
) -> ClassificationOutcome:
    settings = get_settings()
    cache = _get_cache()
    key = _cache_key(text, allowed_intents)
    cached = cache.get(key)
    if cached is not None:
        return cached.model_copy(update={"cache_hit": True}, deep=True)

    local_score = best_local_intent_score(text, allowed_intents)

    if settings.classification_strategy == "local_only":
        outcome = local_fallback_outcome(text, "Local-only strategy", allowed_intents)
        outcome = outcome.model_copy(update={"routing_mode": "local_direct"})
        cache.set(key, outcome)
        return outcome

    if (
        settings.classification_strategy == "smart_hybrid"
        and local_score.score >= settings.local_direct_min_score
        and local_score.intent != "unknown"
    ):
        outcome = _local_direct_outcome(local_score)
        cache.set(key, outcome)
        return outcome

    if not settings.deepseek_api_key:
        outcome = local_fallback_outcome(text, "No DeepSeek API key", allowed_intents)
        cache.set(key, outcome)
        return outcome

    try:
        result = await _classify_intent_with_controls(text, allowed_intents)
        outcome = ClassificationOutcome(
            result=result,
            source="ai",
            status="success",
            routing_mode="ai",
            local_score=local_score.score,
            matched_terms=local_score.matched_terms,
        )
        cache.set(key, outcome)
        return outcome
    except Exception as exc:
        if settings.intent_fallback_enabled:
            outcome = local_fallback_outcome(text, str(exc), allowed_intents)
            cache.set(key, outcome)
            return outcome

        return ClassificationOutcome(
            result=IntentClassification(
                intent="unknown",
                confidence="low",
                reason=f"AI classification failed: {exc}",
            ),
            source="ai",
            status="failed",
            error=str(exc),
            routing_mode="ai_failed",
            local_score=local_score.score,
            matched_terms=local_score.matched_terms,
        )
