import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  AlertTriangle,
  Brain,
  Check,
  ChevronRight,
  RefreshCcw,
  Route,
  ShieldCheck,
  Sparkles,
  Timer,
} from "lucide-react";
import "./styles.css";

type TraceStatus = "success" | "skipped" | "fallback" | "failed" | "overridden" | "rejected";

type PipelineStep = {
  name: string;
  status: TraceStatus;
  detail: string;
  duration_ms?: number | null;
};

type ClassifyResponse = {
  text: string;
  business_type: string;
  intent: string;
  category: string;
  confidence: "high" | "medium" | "low";
  source: "ai" | "local";
  status: "success" | "failed" | "fallback";
  reason: string;
  routing_mode: "local_direct" | "ai" | "ai_fallback" | "ai_failed";
  cache_hit: boolean;
  local_score: number;
  matched_terms: string[];
  duration_ms: number;
  classification_duration_ms: number;
  trace: PipelineStep[];
};

const examples = [
  "ML course er price koto?",
  "class kobe start hobe?",
  "recording pabo?",
  "ami confused, kon course nibo?",
  "thanks",
  "what is the weather today?",
];

const statusIcon: Record<TraceStatus, React.ReactNode> = {
  success: <Check size={16} />,
  skipped: <ChevronRight size={16} />,
  fallback: <RefreshCcw size={16} />,
  failed: <AlertTriangle size={16} />,
  overridden: <Sparkles size={16} />,
  rejected: <AlertTriangle size={16} />,
};

function App() {
  const [text, setText] = useState(examples[0]);
  const [result, setResult] = useState<ClassifyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const apiBase = useMemo(() => "http://localhost:8000", []);

  async function classify(nextText = text) {
    const cleanText = nextText.trim();
    if (!cleanText) return;

    setText(cleanText);
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${apiBase}/classify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: cleanText, business_type: "edtech" }),
      });

      if (!response.ok) {
        throw new Error(`API returned ${response.status}`);
      }

      setResult(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to classify message");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <aside className="sidebar">
          <div className="brand">
            <div className="brand-mark">
              <Route size={22} />
            </div>
            <div>
              <h1>INTENT_DETECTION</h1>
              <p>EdTech pipeline lab</p>
            </div>
          </div>

          <div className="metric-grid">
            <div className="metric">
              <span>Intents</span>
              <strong>19</strong>
            </div>
            <div className="metric">
              <span>Gate</span>
              <strong>1</strong>
            </div>
            <div className="metric">
              <span>Overrides</span>
              <strong>3</strong>
            </div>
            <div className="metric">
              <span>Category AI</span>
              <strong>0</strong>
            </div>
          </div>

          <div className="examples">
            <h2>Examples</h2>
            {examples.map((example) => (
              <button key={example} onClick={() => classify(example)} title={example}>
                {example}
              </button>
            ))}
          </div>
        </aside>

        <section className="main-panel">
          <div className="composer">
            <label htmlFor="message">Raw message</label>
            <div className="input-row">
              <textarea
                id="message"
                value={text}
                onChange={(event) => setText(event.target.value)}
                rows={3}
              />
              <button className="classify-button" onClick={() => classify()} disabled={loading}>
                <Brain size={18} />
                <span>{loading ? "Classifying" : "Classify"}</span>
              </button>
            </div>
            {error && <p className="error">{error}</p>}
          </div>

          <div className="result-grid">
            <SummaryCard
              icon={<Brain size={18} />}
              label="Intent"
              value={result?.intent ?? "waiting"}
            />
            <SummaryCard
              icon={<ShieldCheck size={18} />}
              label="Category"
              value={result?.category ?? "waiting"}
            />
            <SummaryCard
              icon={<Activity size={18} />}
              label="Source"
              value={result ? `${result.source} / ${result.status}` : "waiting"}
            />
            <SummaryCard
              icon={<Route size={18} />}
              label="Routing"
              value={result?.routing_mode ?? "waiting"}
            />
            <SummaryCard
              icon={<RefreshCcw size={18} />}
              label="Cache"
              value={result ? (result.cache_hit ? "hit" : "miss") : "waiting"}
            />
            <SummaryCard
              icon={<ShieldCheck size={18} />}
              label="Local Score"
              value={result ? String(result.local_score) : "waiting"}
            />
            <SummaryCard
              icon={<Timer size={18} />}
              label="Total Time"
              value={result ? `${result.duration_ms} ms` : "waiting"}
            />
            <SummaryCard
              icon={<Timer size={18} />}
              label="Classifier Time"
              value={result ? `${result.classification_duration_ms} ms` : "waiting"}
            />
          </div>

          <section className="trace-section">
            <div className="section-title">
              <h2>Pipeline Trace</h2>
              <span>{result ? result.confidence : "no result"}</span>
            </div>

            <div className="trace-list">
              {(result?.trace ?? emptyTrace).map((step, index) => (
                <article className={`trace-item ${step.status}`} key={`${step.name}-${index}`}>
                  <div className="step-number">{index + 1}</div>
                  <div className="step-icon">{statusIcon[step.status]}</div>
                  <div>
                    <h3>
                      {step.name}
                      {typeof step.duration_ms === "number" && (
                        <span className="step-time">{step.duration_ms} ms</span>
                      )}
                    </h3>
                    <p>{step.detail}</p>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="reason-band">
            <h2>Classifier Reason</h2>
            <p>{result?.reason ?? "Run a message to see the classifier explanation."}</p>
            <p>
              Matched terms:{" "}
              {result?.matched_terms.length ? result.matched_terms.join(", ") : "none"}
            </p>
          </section>
        </section>
      </section>
    </main>
  );
}

function SummaryCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <article className="summary-card">
      <div className="summary-icon">{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

const emptyTrace: PipelineStep[] = [
  {
    name: "Scope resolution",
    status: "skipped",
    detail: "No message has been classified yet.",
  },
  {
    name: "Classification",
    status: "skipped",
    detail: "The classifier trace will appear here.",
  },
  {
    name: "Category derivation",
    status: "skipped",
    detail: "Final category is derived after intent is known.",
  },
];

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
