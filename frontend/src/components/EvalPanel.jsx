import { useEffect, useState } from "react";
import { api } from "../api.js";

const BLANK_CASE = { question: "", relevant_chunk_ids: [], expect_abstain: false, tags: [] };

export default function EvalPanel() {
  const [cases, setCases] = useState([]);
  const [result, setResult] = useState(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);

  // Prefill with the bundled starter set — it's a starting point to edit,
  // not a set that grades well against an arbitrary corpus.
  useEffect(() => {
    api
      .getSampleEvalSet()
      .then((sample) => setCases(sample.map((c) => ({ ...BLANK_CASE, ...c }))))
      .catch(() => setCases([{ ...BLANK_CASE }]));
  }, []);

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
