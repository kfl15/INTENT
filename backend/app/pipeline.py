"""End-to-end intent-detection pipeline."""

from __future__ import annotations

from time import perf_counter

from app.classifier import classify_intent
from app.dialogue import detect_dialogue_act
from app.overrides import apply_post_classification_overrides
from app.profiles import resolve_profile
from app.request_logger import log_classification_response
from app.schemas import (
    ClassificationOutcome,
    ClassifyResponse,
    IntentClassification,
    PipelineStep,
)
from app.taxonomy import category_for_intent


def _elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000, 2)


async def run_intent_pipeline(text: str, business_type: str = "edtech") -> ClassifyResponse:
    pipeline_start = perf_counter()
    trace: list[PipelineStep] = []

    profile = resolve_profile(business_type)
    trace.append(
        PipelineStep(
            name="Scope resolution",
            status="success",
            detail=f"Resolved profile '{profile.business_type}' with {len(profile.all_intents)} allowed intents.",
        )
    )

    trace.append(
        PipelineStep(
            name="Context assembly",
            status="success",
            detail="Built classifier constraints from active profile.",
        )
    )

    dialogue_act = detect_dialogue_act(text)
    trace.append(
        PipelineStep(
            name="Dialogue-act precheck",
            status="success" if dialogue_act else "skipped",
            detail=f"Detected dialogue act: {dialogue_act}." if dialogue_act else "No greeting or acknowledgement detected.",
        )
    )

    classification_start = perf_counter()
    outcome = await classify_intent(text, profile.all_intents)
    classification_duration_ms = _elapsed_ms(classification_start)
    classification_status = (
        "success"
        if outcome.status == "success"
        else "fallback"
        if outcome.status == "fallback"
        else "failed"
    )
    trace.append(
        PipelineStep(
            name="Classification",
            status=classification_status,
            detail=(
                f"{outcome.routing_mode} returned {outcome.result.intent} "
                f"with {outcome.result.confidence} confidence; "
                f"local_score={outcome.local_score}, cache_hit={outcome.cache_hit}."
            ),
            duration_ms=classification_duration_ms,
        )
    )

    if outcome.result.intent not in profile.all_intents:
        outcome = ClassificationOutcome(
            result=IntentClassification(
                intent="unknown",
                confidence="low",
                reason=f"Intent {outcome.result.intent} is outside the trusted profile.",
            ),
            source=outcome.source,
            status=outcome.status,
            error=outcome.error,
        )
        trace.append(
            PipelineStep(
                name="Allowed-intent gate",
                status="rejected",
                detail="Out-of-profile intent was hard-rejected to unknown.",
            )
        )
    else:
        trace.append(
            PipelineStep(
                name="Allowed-intent gate",
                status="success",
                detail=f"{outcome.result.intent} is trusted by the active profile.",
            )
        )

    outcome, override_steps = apply_post_classification_overrides(
        text=text,
        outcome=outcome,
        profile=profile,
        dialogue_act=dialogue_act,
    )
    trace.extend(override_steps)

    category_start = perf_counter()
    category = category_for_intent(outcome.result.intent)
    trace.append(
        PipelineStep(
            name="Category derivation",
            status="success",
            detail=f"Derived category '{category}' from intent '{outcome.result.intent}'.",
            duration_ms=_elapsed_ms(category_start),
        )
    )

    # FULL FLOW
    # text
    # -> profile
    # -> context
    # -> dialogue act
    # -> classifier
    # -> gate
    # -> overrides
    # -> category
    # -> response

    total_duration_ms = _elapsed_ms(pipeline_start)

    response = ClassifyResponse(
        text=text,
        business_type=profile.business_type,
        intent=outcome.result.intent,
        category=category,
        confidence=outcome.result.confidence,
        source=outcome.source,
        status=outcome.status,
        reason=outcome.result.reason,
        routing_mode=outcome.routing_mode,
        cache_hit=outcome.cache_hit,
        local_score=outcome.local_score,
        matched_terms=outcome.matched_terms,
        duration_ms=total_duration_ms,
        classification_duration_ms=classification_duration_ms,
        trace=trace,
    )
    log_classification_response(response)
    return response
