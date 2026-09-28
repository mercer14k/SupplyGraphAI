import { useState } from "react";
import { ArrowUp, Sparkles, ShieldCheck } from "lucide-react";
import { api } from "./api";
import type { Config, QueryResult } from "./types";
export default function QueryPanel({
  snapshot,
  config,
  onEvidence,
}: {
  snapshot: string;
  config: Config | null;
  onEvidence: (id: string) => void;
}) {
  const [question, setQuestion] = useState(
      "What is the impact of PORT-0001 for 14 days?",
    ),
    [result, setResult] = useState<QueryResult | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [useLLM, setUseLLM] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setResult(null);
    try {
      setResult(
        await api<QueryResult>("/analysis/query", {
          method: "POST",
          body: JSON.stringify({
            snapshot_id: snapshot,
            question,
            use_llm: useLLM,
          }),
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel query-panel">
      <div className="section-heading">
        <h3>
          <Sparkles size={17} /> Ask the graph
        </h3>
        <span className="subtle-badge">
          {useLLM ? "LOCAL MODEL PLANNER" : "DETERMINISTIC"}
        </span>
      </div>
      <p className="muted">
        Answers grounded in this snapshot. Every statement links back to
        evidence.
      </p>
      <form onSubmit={submit}>
        <label className="sr-only" htmlFor="graph-question">
          Graph question
        </label>
        <div className="query-input">
          <input
            id="graph-question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            maxLength={2000}
            required
          />
          <button
            className="icon-button bright"
            aria-label="Ask graph"
            disabled={busy || !snapshot}
          >
            {busy ? <span className="spinner" /> : <ArrowUp size={19} />}
          </button>
        </div>
        <div className="query-foot">
          <span>
            <ShieldCheck size={13} /> No model-generated calculations
          </span>
          <label>
            <input
              type="checkbox"
              checked={useLLM}
              disabled={!config?.ai_enabled}
              onChange={(e) => setUseLLM(e.target.checked)}
            />{" "}
            Local AI {config?.ai_enabled ? "" : "(disabled)"}
          </label>
        </div>
      </form>
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {result && (
        <div className="query-result" aria-live="polite">
          {result.status === "abstained" ? (
            <p>
              <strong>Abstained.</strong> {result.reason}
            </p>
          ) : (
            result.claims.map((claim, i) => (
              <div key={i}>
                <p>{claim.text}</p>
                <div className="evidence-chips">
                  {claim.evidence_ids.slice(0, 8).map((id) => (
                    <button key={id} onClick={() => onEvidence(id)}>
                      {id}
                    </button>
                  ))}
                  {claim.evidence_ids.length > 8 && (
                    <span>
                      +{claim.evidence_ids.length - 8} in exported response
                    </span>
                  )}
                </div>
              </div>
            ))
          )}
          <details>
            <summary>Observable execution</summary>
            <pre>{JSON.stringify(result, null, 2)}</pre>
          </details>
        </div>
      )}
    </section>
  );
}
