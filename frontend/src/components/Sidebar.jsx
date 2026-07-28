import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { useToast } from "../toast.jsx";

const STATUS_LABEL = {
  uploading: "uploading",
  processing: "processing",
  ready: "ready",
  failed: "failed",
};

// Maps the fine-grained ingestion_status (from DocumentVersion) to a
// progress percentage for the bar under each document row.
const INGESTION_PROGRESS = {
  pending: 5,
  parsing: 30,
  chunking: 55,
  embedding: 80,
  ready: 100,
  failed: 100,
};

export default function Sidebar({ knowledgeBases, activeKbId, onSelectKb, onKbCreated, documents, onDocumentsChanged }) {
  const [creatingKb, setCreatingKb] = useState(false);
  const [newKbName, setNewKbName] = useState("");
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadFile, setUploadFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const fileInputRef = useRef(null);
  const pollRef = useRef(null);
  const showToast = useToast();

  // Poll while any document is still processing, so status dots and the
  // progress bar update live without a manual refresh.
  useEffect(() => {
    const hasPending = documents.some((d) => d.status === "processing" || d.status === "uploading");
    if (hasPending && !pollRef.current) {
      pollRef.current = setInterval(onDocumentsChanged, 2500);
    }
    if (!hasPending && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = null;
    };
  }, [documents, onDocumentsChanged]);

  async function createKb(e) {
    e.preventDefault();
    if (!newKbName.trim()) return;
    const kb = await api.createKnowledgeBase({ name: newKbName });
    setNewKbName("");
    setCreatingKb(false);
    onKbCreated(kb);
  }

  async function upload(e) {
    e.preventDefault();
    if (!uploadFile || !activeKbId) return;
    setUploading(true);
    setUploadError(null);
    try {
      const form = new FormData();
      form.append("knowledge_base_id", activeKbId);
      form.append("title", uploadTitle || uploadFile.name);
      form.append("sensitivity", "internal");
      form.append("file", uploadFile);
      await api.uploadDocument(form);
      showToast(`"${uploadTitle || uploadFile.name}" uploaded — processing…`);
      setUploadTitle("");
      setUploadFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      onDocumentsChanged();
    } catch (err) {
      setUploadError(err.message);
      showToast(err.message, "error");
    } finally {
      setUploading(false);
    }
  }

  async function remove(doc) {
    if (!window.confirm(`Delete "${doc.title}"? This can't be undone.`)) return;
    setDeletingId(doc.id);
    try {
      await api.deleteDocument(doc.id);
      showToast(`"${doc.title}" deleted`);
      onDocumentsChanged();
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-section">
        <h2>Knowledge bases</h2>
        {knowledgeBases.map((kb) => (
          <div
            key={kb.id}
            className={`kb-item ${kb.id === activeKbId ? "active" : ""}`}
            onClick={() => onSelectKb(kb.id)}
          >
            {kb.name}
          </div>
        ))}

        {creatingKb ? (
          <form onSubmit={createKb} style={{ marginTop: 8 }}>
            <input
              autoFocus
              placeholder="Name…"
              value={newKbName}
              onChange={(e) => setNewKbName(e.target.value)}
              onBlur={() => !newKbName && setCreatingKb(false)}
              style={{ width: "100%", border: "1px solid var(--line)", borderRadius: 3, padding: "6px 8px" }}
            />
          </form>
        ) : (
          <button className="btn-text" onClick={() => setCreatingKb(true)}>+ New knowledge base</button>
        )}
      </div>

      {activeKbId && (
        <div className="sidebar-section">
          <h2>Documents</h2>
          {documents.length === 0 && <div className="evidence-empty">No documents yet.</div>}
          {documents.map((doc) => {
            const percent = INGESTION_PROGRESS[doc.ingestion_status] ?? (doc.status === "ready" ? 100 : 5);
            const failed = doc.status === "failed" || doc.ingestion_status === "failed";
            return (
              <div key={doc.id} className="doc-item">
                <div className="doc-row">
                  <div className="doc-row-main">
                    <div className="doc-title" title={doc.title}>{doc.title}</div>
                    <div className="doc-meta">
                      <span className={`status-dot ${doc.status}`} />
                      <span className="status-label">{STATUS_LABEL[doc.status] || doc.status}</span>
                    </div>
                  </div>
                  <button
                    className="doc-delete-btn"
                    title="Delete document"
                    onClick={() => remove(doc)}
                    disabled={deletingId === doc.id}
                  >
                    ✕
                  </button>
                </div>
                {doc.status !== "ready" && (
                  <div className="progress-track">
                    <div className={`progress-fill ${failed ? "failed" : ""}`} style={{ width: `${percent}%` }} />
                  </div>
                )}
              </div>
            );
          })}

          <form className="upload-box" onSubmit={upload}>
            <input
              type="text"
              placeholder="Title (optional)"
              value={uploadTitle}
              onChange={(e) => setUploadTitle(e.target.value)}
              style={{ width: "100%", marginBottom: 8, border: "1px solid var(--line)", borderRadius: 3, padding: "6px 8px" }}
            />
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt,.md"
              onChange={(e) => setUploadFile(e.target.files[0] || null)}
            />
            {uploadError && <div className="auth-error" style={{ marginTop: 8 }}>{uploadError}</div>}
            <button className="btn-quiet" type="submit" disabled={!uploadFile || uploading} style={{ width: "100%", marginTop: 8 }}>
              {uploading ? "Uploading…" : "Upload"}
            </button>
          </form>
        </div>
      )}
    </aside>
  );
}
