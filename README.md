# INTENT_DETECTION

An interview-ready intent-detection lab based on the class deck included in
`notebooks/0_intent_detection_study_notes.md`.

The project teaches and implements a production-minded intent pipeline for an
EdTech business profile. It is not just an LLM wrapper. The backend owns the
taxonomy, allowed-intent gate, fallback rules, overrides, category derivation,
and trace output.

## What This Proves

- Fixed intent taxonomy design.
- Deterministic category derivation from intent.
- Runtime profile-scoped intent constraints.
- AI-first classification with DeepSeek.
- Smart hybrid routing: fast local direct path, DeepSeek for uncertain cases,
  and local fallback when AI is unavailable.
- Low-confidence and out-of-profile safety handling.
- Business overrides after classification.
- API and unit tests for core behavior.
- A visual demo that explains every pipeline step.

## Project Layout

```text
backend/
  app/
    taxonomy.py      # 19 intents and category map
    profiles.py      # EdTech allowed-intent profile
    classifier.py    # DeepSeek AI path plus fallback chain
    fallback.py      # score-based local intent routing
    dialogue.py      # greeting/acknowledgement precheck
    overrides.py     # business logic overrides
    pipeline.py      # one message in, one intent out
    evaluation.py    # intent accuracy evaluation
    main.py          # FastAPI app
  evaluation_cases.json
  tests/
frontend/
  src/
notebooks/
scripts/
```

## Setup

Clone the repo and enter the project folder:

```bash
git clone https://github.com/kfl15/INTENT.git
cd INTENT
```

Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Local note for my study machine: I use
`/mnt/STUDY/venvs_linux/venv310` instead of `.venv`.

Install frontend dependencies:

```bash
cd frontend
npm install
```

## Configuration

The app runs without a DeepSeek key by using local fallback.

When you are ready to test AI mode, copy `.env.example` to `.env` and add:

```bash
cp .env.example .env
```

Then edit `.env`:

```env
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_MODEL=deepseek-chat
```

Optional production-control settings:

```env
CLASSIFICATION_STRATEGY=smart_hybrid
LOCAL_DIRECT_MIN_SCORE=2.0
LLM_TIMEOUT_SECONDS=8.0
LLM_MAX_CONCURRENCY=20
LLM_RETRY_COUNT=1
CACHE_TTL_SECONDS=300
REQUEST_LOG_PATH=logs/intent_requests.jsonl
```

DeepSeek currently supports OpenAI-compatible chat completions and JSON output
with `response_format={"type":"json_object"}`. The app validates that JSON with
Pydantic and still applies the allowed-intent gate.

## Run

Backend:

```bash
cd INTENT
source .venv/bin/activate
python3 -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

Backend URLs:

```text
API base: http://localhost:8000
Health check: http://localhost:8000/health
Interactive API docs: http://localhost:8000/docs
Intent evaluation: http://localhost:8000/evaluate-intents
```

Frontend:

```bash
cd INTENT/frontend
npm run dev
```

Frontend UI:

```text
http://localhost:5173
```

Each `/classify` response includes timing fields:

```text
duration_ms = total message in/out pipeline time
classification_duration_ms = only AI/local classifier time
routing_mode = local_direct / ai / ai_fallback / ai_failed
cache_hit = whether repeated-message cache was used
local_score = score from local intent router
matched_terms = local terms that matched the message
```

Use `source` and `status` to compare modes:

```text
source=ai, status=success      -> DeepSeek worked
source=local, status=success   -> local direct path was used
source=local, status=fallback  -> AI unavailable/failed, local fallback was used
source=ai, status=failed       -> AI failed and fallback was disabled
```

## Test

```bash
cd INTENT
source .venv/bin/activate
pytest
```

Run the intent evaluation report:

```bash
curl http://localhost:8000/evaluate-intents
```

Run a simple load test while the backend is active:

```bash
python3 scripts/load_test.py --requests 200 --concurrency 50
```

Try these examples in the UI:

- `ML course er price koto?`
- `class kobe start hobe?`
- `recording pabo?`
- `ami confused, kon course nibo?`
- `thanks`
- `what is the weather today?`

## From Demo To Production

Already production-minded:

- typed request/response models
- deterministic taxonomy and category map
- local fallback for provider outage
- smart hybrid local-direct routing for obvious messages
- timeout, retry, concurrency, cache, and lightweight JSONL log controls
- profile-scoped allowed-intent gate
- post-classification business overrides
- traceable pipeline decisions
- automated tests
- environment-based configuration

What a company would add next:

- versioned taxonomy and prompt releases
- larger labeled evaluation dataset
- latency, cost, and error monitoring
- request IDs and structured JSON logs
- human review queue for low-confidence or unknown cases
- tenant-specific profile management
- authentication, rate limiting, and privacy controls
- deployment pipeline with staging and production environments

## Interview Notes

Key explanation:

> The model classifies only the intent. The backend decides everything else.

Important design choices:

- Category is not predicted because deterministic derivation is safer and easier
  to test.
- Local fallback is used only when AI is unavailable or fails, not when AI returns
  a valid `unknown`.
- The allowed-intent gate protects each business profile from unsupported labels.
- Overrides are separate from the classifier because business rules should remain
  auditable and testable.
- Trace output makes the system debuggable and easy to demo.

## GitHub

Recommended repository name:

```text
INTENT_DETECTION
```
