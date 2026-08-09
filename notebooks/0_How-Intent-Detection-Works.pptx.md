How Intent Detection Works

From raw user message to classiﬁed intent — end to end

Raw Message

Intent
Detection

Classiﬁed
Intent

Solving the core problem: routing any user message to the right response handler, reliably, across every business proﬁle.

This deck is a technical deep-dive into the intent detection pipeline — from scope resolution through post-classiﬁcation overrides. Every function name, code snippet,
and example is drawn verbatim from the codebase.

The Big Picture: 8-Step Pipeline

Every incoming message travels through the same deterministic pipeline before a single token of reply is generated.

SETUP · 1

Scope Resolution

Tenant, proﬁle, KB

SETUP · 3

Context Assembly

History + constraints

CLASSIFY · 5

Classiﬁcation

LLM or keyword rules

CLASSIFY · 7

Post-Classiﬁcation Overrides

Business logic wins

SETUP · 2

Mode Selection

AI or local?

CLASSIFY · 4

Dialogue Act Pre-check

Greeting or ack?

CLASSIFY · 6

Allowed-Intent Gate

Reject out-of-proﬁle

OUTPUT · 8

Category Derivation

Deterministic from intent

Steps 1–3 are Setup. Steps 4–7 are Classiﬁcation. Step 8 is deterministic Output. No step is skipped — the pipeline is fully sequential.

Intent Taxonomy: What We're Classifying

19 intents, pre-deﬁned, grouped into four clusters. The model picks one — the system derives everything else.

Cluster

📚 Course Info

🎯 Fit & Eligibility

🛎 Support & Action

⚙ System States

Intents

course_list, course_details, course_pricing_payment,

course_projects, course_schedule_duration,

career_certificate_outcomes
prerequisite_fit, beginner_friendliness, background_fit, career_guidance

demo_trial_counseling, enrollment_admission,

student_support_redirect, instructor_info, recording_access,

missed_class_recovery
neutral, irrelevant, unknown

The model classiﬁes into one of these 19 intents. Category is NEVER a model output — it is derived deterministically after classiﬁcation.

Intent → Category: Deterministic Derivation

Key Insight

intent_taxonomy.py

Category is NEVER predicted by AI — it is derived deterministically from intent

via the INTENT_TO_CATEGORY map. The model has no category output. The

backend computes it.

def category_for_intent(intent: str) -> str:

    return INTENT_TO_CATEGORY.get(

course_pricing_payment

neutral

→ "relevant"

→ "neutral"

irrelevant

→ "irrelevant"

        intent,

        "unknown"

    )

# e.g.
# "course_pricing_payment" → "relevant"
# "neutral"               → "neutral"
# "irrelevant"            → "irrelevant"

The INTENT_TO_CATEGORY map is a static dictionary. No inference, no model call

— a pure dictionary lookup. This makes category derivation auditable, testable,

and zero-latency.

Scope Resolution & The Allowed-Intent Gate

Before any AI runs, the system resolves who is asking and what they're allowed to ask. The model is constrained before it ever sees the message.

business_proﬁles.py — EDTECH_PROFILE (condensed)

Gate Filter: How It Works

EDTECH_PROFILE = BusinessTypeProfile(
    business_type="edtech",
    allowed_intents=frozenset({
        "course_list",
        "prerequisite_fit",
        "course_pricing_payment",
        "career_guidance",
        "enrollment_admission",
        "demo_trial_counseling",
        ...  # 16 domain intents total
    }),
    platform_intents=frozenset({
        "neutral", "unknown", "irrelevant"
    }),
)

chat_orchestrator.py — The Gate

if outcome.result.intent \
        not in profile.all_intents:
    outcome = replace(outcome,
        result=IntentClassification(
            intent="unknown",
            confidence="low",
            reason=f"Intent "
                   f"{outcome.result.intent}"
                   f" is outside the "
                   f"trusted profile.",
        ))

The model can only return intents the business proﬁle permits. Anything outside the frozenset is hard-rejected
to unknown.

AI Classiﬁcation Path: The Happy Path

When AI is available, the LLM classiﬁes against a runtime-scoped JSON schema — the enum is built from the active proﬁle, not hardcoded.

main.py — classify_intent_with_llm() (key parts)

# 1. Scope enum to only allowed intents
active_intents = tuple(
    i for i in INTENTS
    if i in allowed_intents
)

# 2. Build JSON schema at runtime
schema = {
    "properties": {
        "intent": {
            "type": "string",
            "enum": list(active_intents)
        },
        "confidence": {
            "enum": ["high", "medium", "low"]
        },
        "reason": {
            "type": "string",
            "maxLength": 160
        },
    },
    "additionalProperties": False,
}

# 3. System prompt — strict
system = (
    "Classify the user's message using "
    "the supported intent taxonomy. "
    "Do not answer the user. "
    "Do not predict a separate "
    "relevance/category label — "
    "the backend derives that "
    "deterministically from the "
    "chosen intent. "
    "Use unknown when no supported "
    "intent precisely covers the message."
)

# 4. Low confidence → force unknown
if parsed.confidence == "low":
    return IntentClassification(
        intent="unknown",
        confidence="low", ...
    )

Design Guarantees

Structural Constraint

JSON schema enum is built at runtime from the active proﬁle — the model structurally cannot hallucinate
out-of-taxonomy intents.

No Category Prediction

System prompt explicitly forbids category output. Backend derives it deterministically.

Low Conﬁdence → unknown

A shaky prediction is never trusted. Forced to unknown before the gate.

Running Example

"ML course er price koto?"

→ intent: course_pricing_payment
→ conﬁdence: high

Fallback Chain: When AI Fails

Two failure modes, two fallback levels. A valid AI unknown is not a failure — it is preserved as-is.

main.py — classify_intent() fallback chain

Sample EDTECH_INTENT_KEYWORDS Rules

async def classify_intent(
    text,
    allowed_intents=None
):
    # Level 1: No API key → local immediately
    if not OPENAI_API_KEY:
        return local_fallback_outcome(
            text,
            "No API key",
            allowed_intents
        )

    try:
        result = await classify_intent_with_llm(
            text, allowed_intents
        )
        return ClassificationOutcome(
            result=result,
            source="ai",
            status="success"
        )
    except Exception as exc:
        # Level 2: Exception → local if enabled
        if intent_fallback_enabled():
            return local_fallback_outcome(
                text, str(exc), allowed_intents
            )
        return ClassificationOutcome(
            result=fallback_classification(
                str(exc)
            ),
            source="ai",
            status="failed"
        )

Intent

Trigger Keywords

demo_trial_counseling

"human", "counselor", "call me", "phone"

course_pricing_payment

"price", "fee", "cost", "payment", "installment"

recording_access

"record", "recording", "recorded", "lms"

course_schedule_duration

"schedule", "batch", "duration", "class kobe"

Local classiﬁcation is deterministic, zero-cost, and always available — it is the safety net, not the
primary path.

Level 1: No API
Key

Direct to local keyword
classiﬁer

Two‑Level
Fallback
Flow

Valid AI Unknown
Preserve unchanged as
valid unknown

Level 2: AI
Exception

Fallback enabled routes
locally

Post-Classiﬁcation Overrides

After the model classiﬁes, business logic gets the ﬁnal word. Three override rules, applied in sequence, always win over model output.

chat_orchestrator.py — inside plan_reply(), after classiﬁcation

Override Layer Flow

# Override 1: Acknowledgement → force neutral
if dialogue_act == "acknowledgement" \
        and "neutral" in profile.all_intents:
    outcome = replace(outcome,
        result=IntentClassification(
            intent="neutral",
            confidence="high",
            reason="Acknowledgement dialogue act."
        ))

# Override 2: Explicit course list → force course_list
if is_explicit_course_list_request(text) and \
   outcome.result.intent in {
       "course_list", "career_guidance",
       "neutral", "unknown"
   }:
    outcome = replace(outcome,
        result=IntentClassification(
            intent="course_list",
            confidence="high",
            reason="Explicit catalog request."
        ))

# Override 3: Confused/hesitant → career_guidance
if constraint_update.state \
        .decision_support_state in {
            "confused", "hesitant"
        } and outcome.result.intent in {
            "neutral", "unknown"
        }:
    outcome = replace(outcome,
        result=IntentClassification(
            intent="career_guidance",
            confidence="high",
            reason="Customer requested "
                   "decision support."
        ))

Classiﬁer Output Enters

Raw intent from AI or local fallback

Override 1: Ack → neutral

Dialogue act = acknowledgement

Override 2: Catalog → course_list

Explicit course list request detected

Override 3: Confused → career_guidance

Decision support state = confused/hesitant

Final Intent Exits

Business logic always wins

Overrides are business logic, not model logic. They run after classiﬁcation and always win.

5 Key Design Rules

Rule

Enforcement

Category derived from intent, never predicted

normalize_prediction_category(intent, None) discards
model category

AI-ﬁrst, local is fallback only

Valid AI unknown is NOT overwritten

Business proﬁle gates all intents

Single classiﬁcation per message

intent_mode=ai tries LLM ﬁrst; local only on operational
failure

Only intent_fallback_enabled() on exceptions, not on
valid unknown

allowed_intents passed to classiﬁer; rejected intents →
unknown

Orchestrator calls classiﬁer once; answer strategies consume
the result

Every rule is enforced structurally — by code, not convention. The pipeline cannot violate these constraints at runtime.

End-to-End: One Message In, One Intent Out

Running example: "ML course er price koto?" — traced through every pipeline step.

Full Trace

User: "ML course er price koto?"
│
├─ resolve scope
│   → BusinessTypeProfile(edtech)
│   → KnowledgeBaseBundle
│
├─ detect dialogue act
│   → None (not greeting/acknowledgement)
│
├─ classifier(
│     "ML course er price koto?",
│     mode="ai",
│     allowed=edtech_allowed_intents
│   )
│   ├─ classify_intent_with_llm()
│   │   → JSON schema {
│   │       intent: enum[intents],
│   │       confidence, reason
│   │     }
│   │   → response: {
│   │       intent: "course_pricing_payment",
│   │       confidence: "high"
│   │     }
│   └─ returns IntentClassification(
│         intent="course_pricing_payment"
│       )
│
├─ allowed-intent gate
│   → course_pricing_payment
│      ∈ edtech_allowed_intents ✓
│
├─ post-classification overrides
│   → none triggered
│
└─ outcome: ClassificationOutcome(
      result=intent="course_pricing_payment",
      source="ai",
      status="success"
   )
│
▼ [CourseQueryResolver + CatalogMatcher
   + ReplyGenerator]
→ "ML for NLP course er price hocche
   50,000 BDT. ..."

Architecture Summary: Why It's Built This Way

Each design decision in the pipeline exists to eliminate a speciﬁc failure mode. The architecture is defensive by construction.

Structural Hallucination Prevention

Runtime JSON schema enum built from active proﬁle. The model cannot output an intent that isn't in the frozenset — structurally impossible, not just prompted away.

Deterministic Category Derivation

INTENT_TO_CATEGORY map is a static dictionary lookup. Zero inference, zero latency, fully auditable. Category is never a model concern.

Proﬁle-Scoped Gating

The allowed-intent gate runs after every classiﬁcation. Out-of-proﬁle intents are hard-rejected to unknown regardless of model conﬁdence.

Graceful Degradation

Two-level fallback chain ensures classiﬁcation always returns a result. Local keyword rules are deterministic, zero-cost, and always available.

Business Logic Separation

Post-classiﬁcation overrides are pure business logic, applied after the model. They are auditable, testable, and independent of model behavior.

One message in. One intent out. Every
time.

19 Intents

1 Gate

3 Overrides

Pre-deﬁned taxonomy. Model picks one.

Proﬁle-scoped. Hard rejection on violation.

Business logic. Always wins over model.

0 Category Predictions

2 Fallback Levels

Derived deterministically. Never inferred.

Local is always available. Zero-cost safety net.

The pipeline is deterministic by design. Every constraint is structural — enforced by code, not convention. The model classiﬁes. The system

decides.

