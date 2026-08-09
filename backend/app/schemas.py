"""Pydantic schemas shared by API, classifier, and visualizer."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.taxonomy import Category

Confidence = Literal["high", "medium", "low"]
ClassifierSource = Literal["ai", "local"]
ClassificationStatus = Literal["success", "failed", "fallback"]
RoutingMode = Literal["local_direct", "ai", "ai_fallback", "ai_failed"]
TraceStatus = Literal["success", "skipped", "fallback", "failed", "overridden", "rejected"]


# IntentClassification = what is predicted
class IntentClassification(BaseModel):
    intent: str
    confidence: Confidence
    reason: str = Field(max_length=200)

# ClassificationOutcome = what is prediction + how it happened
class ClassificationOutcome(BaseModel):
    result: IntentClassification
    source: ClassifierSource
    status: ClassificationStatus
    error: str | None = None
    routing_mode: RoutingMode = "ai"
    cache_hit: bool = False
    local_score: float = 0.0
    matched_terms: list[str] = Field(default_factory=list)



# mainly for the frontend visualizer and keep track of every step. 
# which step happened, what status it had, what detail/result came from that step
class PipelineStep(BaseModel):
    name: str
    status: TraceStatus
    detail: str
    duration_ms: float | None = None

# This is what the frontend/user sends to the API.
class ClassifyRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    business_type: str = "edtech"

# This is what the API returns after classification. Frontend uses this response to show final result + full pipeline trace.
class ClassifyResponse(BaseModel):
    text: str
    business_type: str
    intent: str
    category: Category
    confidence: Confidence
    source: ClassifierSource
    status: ClassificationStatus
    reason: str
    routing_mode: RoutingMode
    cache_hit: bool
    local_score: float
    matched_terms: list[str]
    duration_ms: float
    classification_duration_ms: float
    trace: list[PipelineStep]


class EvaluationCase(BaseModel):
    text: str
    expected_intent: str
    expected_category: Category


class EvaluationCaseResult(BaseModel):
    text: str
    expected_intent: str
    actual_intent: str
    expected_category: Category
    actual_category: Category
    matched: bool


class EvaluationResponse(BaseModel):
    total_cases: int
    exact_matches: int
    accuracy: float
    precision: float
    recall: float
    per_intent: dict[str, dict[str, int | float]]
    confusion: dict[str, dict[str, int]]
    details: list[EvaluationCaseResult]
