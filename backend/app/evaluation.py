"""Intent evaluation utilities."""

from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import run_intent_pipeline
from app.schemas import EvaluationCase, EvaluationCaseResult, EvaluationResponse


def _safe_ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 3) if denominator else 0.0


async def evaluate_intents(
    cases_path: str | Path = "backend/evaluation_cases.json",
) -> EvaluationResponse:
    raw_cases = json.loads(Path(cases_path).read_text(encoding="utf-8"))
    cases = [EvaluationCase(**case) for case in raw_cases]

    details: list[EvaluationCaseResult] = []
    labels = {case.expected_intent for case in cases}
    confusion: dict[str, dict[str, int]] = {}

    for case in cases:
        response = await run_intent_pipeline(case.text)
        labels.add(response.intent)
        confusion.setdefault(case.expected_intent, {})
        confusion[case.expected_intent][response.intent] = (
            confusion[case.expected_intent].get(response.intent, 0) + 1
        )
        details.append(
            EvaluationCaseResult(
                text=case.text,
                expected_intent=case.expected_intent,
                actual_intent=response.intent,
                expected_category=case.expected_category,
                actual_category=response.category,
                matched=response.intent == case.expected_intent
                and response.category == case.expected_category,
            )
        )

    exact_matches = sum(1 for item in details if item.matched)
    per_intent: dict[str, dict[str, int | float]] = {}
    precision_values: list[float] = []
    recall_values: list[float] = []

    for label in sorted(labels):
        tp = sum(1 for item in details if item.expected_intent == label and item.actual_intent == label)
        fp = sum(1 for item in details if item.expected_intent != label and item.actual_intent == label)
        fn = sum(1 for item in details if item.expected_intent == label and item.actual_intent != label)
        precision = _safe_ratio(tp, tp + fp)
        recall = _safe_ratio(tp, tp + fn)
        precision_values.append(precision)
        recall_values.append(recall)
        per_intent[label] = {
            "true_positive": tp,
            "false_positive": fp,
            "false_negative": fn,
            "precision": precision,
            "recall": recall,
        }

    total_cases = len(cases)
    return EvaluationResponse(
        total_cases=total_cases,
        exact_matches=exact_matches,
        accuracy=_safe_ratio(exact_matches, total_cases),
        precision=round(sum(precision_values) / len(precision_values), 3)
        if precision_values
        else 0.0,
        recall=round(sum(recall_values) / len(recall_values), 3) if recall_values else 0.0,
        per_intent=per_intent,
        confusion=confusion,
        details=details,
    )
