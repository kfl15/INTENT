"""AI-first classifier with deterministic local fallback."""

from __future__ import annotations

import json

from openai import AsyncOpenAI

from app.config import get_settings
from app.fallback import local_fallback_outcome
from app.schemas import ClassificationOutcome, IntentClassification
from app.taxonomy import INTENTS

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

    if not settings.deepseek_api_key:
        return local_fallback_outcome(text, "No DeepSeek API key", allowed_intents)

    try:
        result = await classify_intent_with_llm(text, allowed_intents)
        return ClassificationOutcome(result=result, source="ai", status="success")
    except Exception as exc:
        if settings.intent_fallback_enabled:
            return local_fallback_outcome(text, str(exc), allowed_intents)

        return ClassificationOutcome(
            result=IntentClassification(
                intent="unknown",
                confidence="low",
                reason=f"AI classification failed: {exc}",
            ),
            source="ai",
            status="failed",
            error=str(exc),
        )
