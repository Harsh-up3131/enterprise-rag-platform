import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";

const BLANK_CASE = { question: "", relevant_chunk_ids: [], expect_abstain: false, tags: [] };

export default function EvalPanel() {
  const [cases, setCases] = useState([]);
  const [result, setResult] = useState(null);
  const [quality, setQuality] = useState(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);

  const loadQuality = useCallback(() => {
    api.getQualityDashboard().catch(() => null).then((summary) => setQuality(summary));
  }, []);

  // Prefill with the bundled starter set — it's a starting point to edit,
  // not a set that grades well against an arbitrary corpus. This runs once:
  // the panel stays mounted across tab switches, so edits here are not lost.
  useEffect(() => {
    api
      .getSampleEvalSet()
      .then((sample) => setCases(sample.map((c) => ({ ...BLANK_CASE, ...c }))))
      .catch(() => setCases([{ ...BLANK_CASE }]));

    loadQuality();
  }, [loadQuality]);

  function updateCase(index, patch) {
    setCases((prev) => prev.map((c, i) => (i === index ? { ...c, ...patch } : c)));
  }

  function addCase() {
    setCases((prev) => [...prev, { ...BLANK_CASE }]);
  }

  function removeCase(index) {
    setCases((prev) => prev.filter((_, i) => i !== index));
  }

  async function run() {
    const payload = cases
      .map((c) => ({ ...c, question: c.question.trim() }))
      .filter((c) => c.question);

    if (!payload.length) {
      setError("Add at least one question to evaluate.");
      return;
    }

    setRunning(true);
    setError(null);
    try {
      setResult(await api.runEval(payload));
      // A run writes a new quality snapshot; refresh so the metrics and
      // history reflect it (the panel no longer remounts to pick it up).
      loadQuality();
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
        Runs these questions through the live pipeline and scores retrieval and
        citation quality. Edit them to match documents you've actually uploaded —
        questions with no supporting evidence will correctly abstain and score nothing.
      </p>

      <div className="eval-cases">
        {cases.map((c, i) => (
          <div key={i} className="eval-case">
            <input
              value={c.question}
              placeholder="Question to ask the knowledge base…"
              onChange={(e) => updateCase(i, { question: e.target.value })}
            />
            <div className="eval-case-row">
              <label title="Tick when the correct behavior is to refuse — no evidence should exist for this question.">
                <input
                  type="checkbox"
                  checked={c.expect_abstain}
                  onChange={(e) => updateCase(i, { expect_abstain: e.target.checked })}
                />
                Expect abstention
              </label>
              <button className="btn-text" onClick={() => removeCase(i)}>
                Remove
              </button>
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", gap: 10, marginTop: 14, alignItems: "center" }}>
        <button className="btn" onClick={run} disabled={running}>
          {running ? "Running…" : "Run evaluation"}
        </button>
        <button className="btn btn-quiet" onClick={addCase} disabled={running}>
          Add question
        </button>
      </div>

      {error && <div className="auth-error" style={{ marginTop: 16 }}>{error}</div>}

      {quality && (
        <>
          <div className="eval-metrics" style={{ marginTop: 18 }}>
            <Metric label="Quality score" value={fmt(quality.answer_quality_score)} />
            <Metric label="Abstention rate" value={fmt(quality.abstention_rate)} />
            <Metric label="Citation success" value={fmt(quality.citation_success_rate)} />
            <Metric label="Avg latency (ms)" value={fmt(quality.avg_latency_ms)} />
          </div>

          {quality.history?.length > 0 && (
            <div style={{ marginTop: 18 }}>
              <h3 style={{ fontSize: 16, marginBottom: 8 }}>Recent history</h3>
              <div style={{ display: "grid", gap: 8 }}>
                {quality.history.map((entry, idx) => (
                  <div key={idx} className="eval-case" style={{ padding: 10 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
                      <strong>{entry.created_at ? new Date(entry.created_at).toLocaleString() : `Run ${idx + 1}`}</strong>
                      <span>Quality {fmt(entry.answer_quality_score)}</span>
                    </div>
                    <div style={{ color: "var(--ink-soft)", fontSize: 13, marginTop: 6 }}>
                      Abstention {fmt(entry.abstention_rate)} • Citation {fmt(entry.citation_success_rate)} • Latency {fmt(entry.avg_latency_ms)} ms
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {result && (
        <>
          <div className="eval-metrics">
            <Metric label="Cases" value={result.num_cases} />
            <Metric
              label="Recall@K"
              value={fmt(result.mean_recall_at_k)}
              note={
                result.recall_graded_cases
                  ? `${result.recall_graded_cases} graded`
                  : "no ground truth"
              }
            />
            <Metric
              label="Citation accuracy"
              value={fmt(result.citation_accuracy)}
              note={
                result.citation_scored_cases
                  ? `${result.citation_scored_cases} scored`
                  : "no answerable cases"
              }
            />
            <Metric label="Abstention accuracy" value={fmt(result.abstention_accuracy)} />
          </div>

          <div className="eval-breakdown-wrapper">
            <table className="eval-breakdown">
              <thead>
                <tr>
                  <th>Question</th>
                  <th>Abstained</th>
                  <th>Citations</th>
                </tr>
              </thead>
              <tbody>
                {result.cases.map((c, i) => (
                  <tr key={i}>
                    <td>{c.question}</td>
                    <td className={c.abstention_ok ? "ok" : "bad"}>
                      {c.abstained ? "yes" : "no"}
                      {c.abstention_ok ? "" : c.expected_abstain ? " (expected yes)" : " (expected no)"}
                    </td>
                    <td>{c.num_verified_citations}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}

// Metrics are null when no case could be measured — show that rather than
// a 0.00 that reads as a failure, or a 1.00 that reads as a perfect score.
function fmt(value) {
  return value === null || value === undefined ? "n/a" : value.toFixed(2);
}

function Metric({ label, value, note }) {
  return (
    <div className="metric-card">
      <div className="metric-value">{value}</div>
      <div className="metric-label">{label}</div>
      {note && <div className="metric-note">{note}</div>}
    </div>
  );
}
