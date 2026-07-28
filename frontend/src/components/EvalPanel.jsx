import { useState } from "react";
import { api } from "../api.js";

export default function EvalPanel() {
  const [result, setResult] = useState(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);

  async function run() {
    setRunning(true);
    setError(null);
    try {
      setResult(await api.runEval());
    } catch (err) {
      setError(err.message);
    } finally {
      setRunning(false);
    }
  }

  return (
    <section className="eval-panel">
      <h2 style={{ fontSize: 20 }}>Evaluation</h2>
      <p style={{ color: "var(--ink-soft)", marginTop: 6 }}>
        Runs the sample question set through the live pipeline and scores retrieval and citation quality.
      </p>
      <button className="btn" onClick={run} disabled={running} style={{ marginTop: 16 }}>
        {running ? "Running…" : "Run evaluation"}
      </button>

      {error && <div className="auth-error" style={{ marginTop: 16 }}>{error}</div>}

      {result && (
        <div className="eval-metrics">
          <Metric label="Cases" value={result.num_cases} />
          <Metric label="Recall@K" value={result.mean_recall_at_k.toFixed(2)} />
          <Metric label="Citation accuracy" value={result.citation_accuracy.toFixed(2)} />
          <Metric label="Abstention accuracy" value={result.abstention_accuracy.toFixed(2)} />
        </div>
      )}
    </section>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric-card">
      <div className="metric-value">{value}</div>
      <div className="metric-label">{label}</div>
    </div>
  );
}
