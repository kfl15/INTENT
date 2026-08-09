# INTENT_DETECTION

An interview-ready intent-detection lab based on the class deck in
`1_SUPPORTIVE_DOC/How-Intent-Detection-Works.pptx.md`.

The project teaches and implements a production-minded intent pipeline for an
EdTech business profile. It is not just an LLM wrapper. The backend owns the
taxonomy, allowed-intent gate, fallback rules, overrides, category derivation,
and trace output.

## What This Proves

- Fixed intent taxonomy design.
- Deterministic category derivation from intent.
- Runtime profile-scoped intent constraints.
- AI-first classification with DeepSeek.
- Local deterministic fallback when AI is unavailable.
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
    fallback.py      # deterministic keyword rules
    dialogue.py      # greeting/acknowledgement precheck
    overrides.py     # business logic overrides
    pipeline.py      # one message in, one intent out
    main.py          # FastAPI app
  tests/
frontend/
  src/
notebooks/
```

## Setup

Always use the existing shared venv:

```bash
cd /mnt/STUDY/2026/12_INTENT/2_CODE_BASE/INTENT_DETECTION
source /mnt/STUDY/venvs_linux/venv310/bin/activate
pip install -r requirements.txt
```

Install frontend dependencies:

```bash
cd frontend
npm install
```

## Configuration

The app runs without a DeepSeek key by using local fallback.

When you are ready to test AI mode, copy `.env.example` to `.env` and add:

```bash
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_MODEL=deepseek-chat
```

DeepSeek currently supports OpenAI-compatible chat completions and JSON output
with `response_format={"type":"json_object"}`. The app validates that JSON with
Pydantic and still applies the allowed-intent gate.

## Run

Backend:

```bash
cd /mnt/STUDY/2026/12_INTENT/2_CODE_BASE/INTENT_DETECTION
source /mnt/STUDY/venvs_linux/venv310/bin/activate
python3 -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

Frontend:

```bash
cd /mnt/STUDY/2026/12_INTENT/2_CODE_BASE/INTENT_DETECTION/frontend
npm run dev
```

Open the UI at `http://localhost:5173`.

Each `/classify` response includes timing fields:

```text
duration_ms = total message in/out pipeline time
classification_duration_ms = only AI/local classifier time
```

Use `source` and `status` to compare modes:

```text
source=ai, status=success      -> DeepSeek worked
source=local, status=fallback  -> local fallback was used
source=ai, status=failed       -> AI failed and fallback was disabled
```

## Test

```bash
cd /mnt/STUDY/2026/12_INTENT/2_CODE_BASE/INTENT_DETECTION
source /mnt/STUDY/venvs_linux/venv310/bin/activate
pytest
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
- profile-scoped allowed-intent gate
- post-classification business overrides
- traceable pipeline decisions
- automated tests
- environment-based configuration

What a company would add next:

- versioned taxonomy and prompt releases
- labeled evaluation dataset with accuracy reports
- confusion matrix per intent
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
