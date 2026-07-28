export default function EvidencePanel({ citations }) {
  return (
    <aside className="evidence-panel">
      <h2>Evidence</h2>
      {(!citations || citations.length === 0) && (
        <div className="evidence-empty">Select a citation to see its source.</div>
      )}
      {citations && citations.map((c, idx) => (
        <div key={c.chunk_id + idx} className="evidence-card">
          <div className="evidence-card-title">{c.document_title}</div>
          <div className="evidence-card-meta">
            {c.heading_path && <span>{c.heading_path}</span>}
            {c.page != null && <span>p.{c.page}</span>}
            {c.score != null && <span>score {c.score.toFixed(2)}</span>}
          </div>
        </div>
      ))}
    </aside>
  );
}
