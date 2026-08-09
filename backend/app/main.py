"""FastAPI entrypoint for INTENT_DETECTION."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.evaluation import evaluate_intents
from app.pipeline import run_intent_pipeline
from app.schemas import ClassifyRequest, ClassifyResponse, EvaluationResponse

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@app.post("/classify", response_model=ClassifyResponse)
async def classify(request: ClassifyRequest) -> ClassifyResponse:
    return await run_intent_pipeline(
        text=request.text,
        business_type=request.business_type,
    )


@app.get("/evaluate-intents", response_model=EvaluationResponse)
async def evaluate() -> EvaluationResponse:
    return await evaluate_intents()
