import { useState } from "react";
import { api } from "../api.js";

export default function SecurityPanel({ documents }) {
  const [checking, setChecking] = useState(false);
  const [checkResult, setCheckResult] = useState(null);
  const [checkError, setCheckError] = useState(null);
  const [auditResult, setAuditResult] = useState(null);
  const [auditError, setAuditError] = useState(null);
  const [openAclDocId, setOpenAclDocId] = useState(null);
  const [aclByDoc, setAclByDoc] = useState({});

  async function runCheck() {
    setChecking(true);
    setCheckError(null);
    try {
      setCheckResult(await api.runIsolationCheck());
    } catch (err) {
      setCheckError(err.message);
    } finally {
      setChecking(false);
    }
  }

  async function loadAudit() {
    try {
      setAuditResult(await api.getDependencyAudit());
      setAuditError(null);
    } catch (err) {
      setAuditError(err.message);
    }
  }

  async function toggleAcl(docId) {
    if (openAclDocId === docId) {
      setOpenAclDocId(null);
      return;
    }
    setOpenAclDocId(docId);
    if (!aclByDoc[docId]) {
      const entries = await api.listAcl(docId);
      setAclByDoc((prev) => ({ ...prev, [docId]: entries }));
    }
  }

  return (
    <section className="security-panel">
      <h2 style={{ fontSize: 20 }}>Tenant isolation check</h2>
      <p style={{ color: "var(--ink-soft)", marginTop: 6 }}>
        Plants a throwaway document in a separate organization and confirms it
        can't be searched from here, then confirms a document with no access
        rules at all is invisible to everyone. Cleans up after itself.
      </p>
      <button className="btn" onClick={runCheck} disabled={checking} style={{ marginTop: 16 }}>
        {checking ? "Running…" : "Run isolation check"}
      </button>

      <button className="btn-quiet" onClick={loadAudit} style={{ marginTop: 12 }}>
        Load dependency audit
      </button>

      {checkError && <div className="auth-error" style={{ marginTop: 16 }}>{checkError}</div>}
      {auditError && <div className="auth-error" style={{ marginTop: 12 }}>{auditError}</div>}

      {auditResult && (
        <div className="check-list" style={{ marginTop: 16 }}>
          <div className="check-row">
            <span className="check-icon pass">✓</span>
            <div>
              <div className="check-name">Dependency scan readiness</div>
              <div className="check-detail">Python manifests: {auditResult.python_manifests.length || 0}; JS manifests: {auditResult.javascript_manifests.length || 0}</div>
            </div>
          </div>
          {auditResult.commands.map((command, index) => (
            <div key={index} className="acl-entry">{command}</div>
          ))}
        </div>
      )}

      {checkResult && (
        <div className="check-list">
          {checkResult.checks.map((c, i) => (
            <div key={i} className="check-row">
              <span className={`check-icon ${c.passed ? "pass" : "fail"}`}>{c.passed ? "✓" : "✕"}</span>
              <div>
                <div className="check-name">{c.name}</div>
                <div className="check-detail">{c.detail}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="acl-section">
        <h2 style={{ fontSize: 20 }}>Document access</h2>
        <p style={{ color: "var(--ink-soft)", marginTop: 6, marginBottom: 16 }}>
          Who can read each document, so you can spot an accidental over-broad grant.
        </p>
        {documents.length === 0 && <div className="evidence-empty">No documents yet.</div>}
        {documents.map((doc) => (
          <div key={doc.id} className="acl-doc-row">
            <div className="acl-doc-header" onClick={() => toggleAcl(doc.id)}>
              <span>{doc.title}</span>
              <span className="btn-text">{openAclDocId === doc.id ? "Hide" : "View access"}</span>
            </div>
            {openAclDocId === doc.id && (
              <div className="acl-doc-body">
                {!aclByDoc[doc.id] && <div className="evidence-empty">Loading…</div>}
                {aclByDoc[doc.id]?.length === 0 && <div className="evidence-empty">No access rules — nobody can read this.</div>}
                {aclByDoc[doc.id]?.map((entry) => (
                  <div key={entry.id} className="acl-entry">
                    {entry.principal_type}:{entry.principal_id} → {entry.permission}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
