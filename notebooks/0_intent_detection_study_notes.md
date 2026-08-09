# How Intent Detection Works

From raw user message to classified intent, end to end.

This note is a cleaned GitHub-readable version of the class deck. The original
PowerPoint is kept beside it:

`notebooks/0_How-Intent-Detection-Works.pptx`

## Core Problem

Intent detection routes a user message to the correct response handler.

Example:

```text
Raw message -> Intent detection -> Classified intent
```

For this project:

```text
"ML course er price koto?"
-> course_pricing_payment
-> category: relevant
```

Important:

```text
The model predicts intent only.
The backend derives category.
```

## 8-Step Pipeline

Every incoming message follows the same sequence before a reply is generated.

| Step | Stage | Name | Purpose |
|---:|---|---|---|
| 1 | Setup | Scope Resolution | Resolve tenant, business profile, and knowledge context |
| 2 | Setup | Mode Selection | Decide AI mode or local fallback mode |
| 3 | Setup | Context Assembly | Build history, constraints, and allowed intents |
| 4 | Classify | Dialogue Act Pre-check | Detect greetings or acknowledgements |
| 5 | Classify | Classification | Use LLM or keyword rules to predict intent |
| 6 | Classify | Allowed-Intent Gate | Reject out-of-profile intents |
| 7 | Classify | Post-Classification Overrides | Apply business rules that can override classifier output |
| 8 | Output | Category Derivation | Derive category deterministically from final intent |

No step is skipped. The pipeline is sequential and auditable.

## Intent Taxonomy

The system uses 19 predefined intents grouped into four clusters.

| Cluster | Intents |
|---|---|
| Course Info | `course_list`, `course_details`, `course_pricing_payment`, `course_projects`, `course_schedule_duration`, `career_certificate_outcomes` |
| Fit & Eligibility | `prerequisite_fit`, `beginner_friendliness`, `background_fit`, `career_guidance` |
| Support & Action | `demo_trial_counseling`, `enrollment_admission`, `student_support_redirect`, `instructor_info`, `recording_access`, `missed_class_recovery` |
| System States | `neutral`, `irrelevant`, `unknown` |

The classifier chooses one intent from this taxonomy.

## Intent To Category

Category is never predicted by AI. It is derived from the final intent by a
dictionary lookup.

```python
def category_for_intent(intent: str) -> str:
    return INTENT_TO_CATEGORY.get(intent, "unknown")
```

Examples:

| Intent | Category |
|---|---|
| `course_pricing_payment` | `relevant` |
| `course_schedule_duration` | `relevant` |
| `neutral` | `neutral` |
| `irrelevant` | `irrelevant` |
| `unknown` | `unknown` |

Why this is good:

- no extra model call
- no category hallucination
- fast
- testable
- easy to audit

## Business Profile And Allowed-Intent Gate

Before classification, the system resolves the active business profile.

For EdTech:

```python
EDTECH_PROFILE = BusinessTypeProfile(
    business_type="edtech",
    allowed_intents=frozenset({
        "course_list",
        "course_pricing_payment",
        "career_guidance",
        "enrollment_admission",
        "demo_trial_counseling",
        # other EdTech intents
    }),
    platform_intents=frozenset({
        "neutral",
        "unknown",
        "irrelevant",
    }),
)
```

After classification, the gate checks:

```python
if outcome.result.intent not in profile.all_intents:
    outcome.result.intent = "unknown"
    outcome.result.confidence = "low"
```

Meaning:

```text
If the classifier returns an unsupported intent, reject it to unknown.
```

This protects each business profile from labels it should not handle.

## AI Classification Path

When AI is available, the system sends the user message and the active allowed
intent list to the LLM.

The LLM must return JSON with:

```json
{
  "intent": "course_pricing_payment",
  "confidence": "high",
  "reason": "User asks about course price."
}
```

The LLM is instructed:

- classify the message
- do not answer the user
- do not predict category
- choose only from allowed intents
- use `unknown` when no intent fits
- return JSON only

If confidence is low:

```python
if classification.confidence == "low":
    return IntentClassification(
        intent="unknown",
        confidence="low",
        reason="Low confidence classification forced to unknown.",
    )
```

## Fallback Chain

Local fallback is a deterministic backup classifier.

It is used when:

- no API key exists
- AI call fails
- fallback is enabled

Flow:

```text
No API key -> local fallback
AI success -> source=ai, status=success
AI exception + fallback enabled -> local fallback
AI exception + fallback disabled -> source=ai, status=failed
```

Example fallback rules:

| Intent | Trigger Keywords |
|---|---|
| `course_pricing_payment` | `price`, `fee`, `cost`, `payment`, `installment`, `koto` |
| `recording_access` | `record`, `recording`, `recorded`, `lms` |
| `course_schedule_duration` | `schedule`, `batch`, `duration`, `class kobe` |
| `demo_trial_counseling` | `human`, `counselor`, `call me`, `phone` |

Important:

```text
Valid AI unknown is not an operational failure.
It should stay unknown.
```

## Post-Classification Overrides

Overrides are business rules applied after classification.

They are written by developers/product teams after studying real user behavior
and common classifier mistakes.

### Override 1: Acknowledgement

```text
thanks / ok / done -> neutral
```

Example:

```text
User: thanks
Classifier: course_details
Final intent: neutral
```

### Override 2: Explicit Course List

```text
ki ki course available? -> course_list
```

Only applied when the current intent is weak or related:

```python
{"course_list", "career_guidance", "neutral", "unknown"}
```

### Override 3: Decision Support

```text
ami confused, kon course nibo? -> career_guidance
```

Only applied when current intent is:

```python
{"neutral", "unknown"}
```

Reason:

```text
If the classifier already found a strong intent like pricing, do not override it.
```

## Key Design Rules

| Rule | Why It Matters |
|---|---|
| Category derived from intent | Prevents category hallucination |
| AI first, local fallback second | Better accuracy with graceful degradation |
| Valid AI unknown is preserved | Unknown is a valid result, not a failure |
| Business profile gates all intents | Prevents unsupported routing |
| Single classification per message | Keeps behavior simpler and cheaper |
| Overrides are separate from classifier | Business logic stays auditable and testable |

## End-To-End Example

User:

```text
ML course er price koto?
```

Trace:

```text
1. Scope resolution
   -> EdTech profile

2. Context assembly
   -> Allowed intents loaded

3. Dialogue-act precheck
   -> None

4. Classification
   -> course_pricing_payment
   -> confidence: high

5. Allowed-intent gate
   -> course_pricing_payment is allowed

6. Overrides
   -> none triggered

7. Category derivation
   -> relevant
```

Final output:

```json
{
  "intent": "course_pricing_payment",
  "category": "relevant",
  "confidence": "high",
  "source": "ai",
  "status": "success"
}
```

## Architecture Summary

The architecture is defensive by design.

- The model classifies.
- The backend validates.
- The gate rejects unsupported intents.
- Overrides apply business logic.
- Category is derived deterministically.
- Local fallback keeps the system usable when AI is unavailable.

Final interview sentence:

```text
I built the system so the LLM classifies only intent. The backend validates the
intent, applies business overrides, and derives category deterministically.
```
