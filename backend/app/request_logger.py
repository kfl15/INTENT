"""Lightweight structured request logging."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.config import get_settings
from app.schemas import ClassifyResponse


def log_classification_response(response: ClassifyResponse) -> str:
    """Append one JSON log line and return the generated request id."""

    settings = get_settings()
    request_id = str(uuid4())
    log_path = Path(settings.request_log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "text_length": len(response.text),
        "business_type": response.business_type,
        "intent": response.intent,
        "category": response.category,
        "source": response.source,
        "status": response.status,
        "routing_mode": response.routing_mode,
        "cache_hit": response.cache_hit,
        "local_score": response.local_score,
        "matched_terms": response.matched_terms,
        "duration_ms": response.duration_ms,
        "classification_duration_ms": response.classification_duration_ms,
    }

    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=True) + "\n")

    return request_id
