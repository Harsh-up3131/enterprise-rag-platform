import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { useToast } from "../toast.jsx";
import ConversationHistory from "./ConversationHistory.jsx";

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

export default function Sidebar({ knowledgeBases, activeKbId, onSelectKb, onKbCreated, documents, onDocumentsChanged, conversations, activeConversationId, onSelectConversation, onStartNew, onDeleteConversation }) {
  const [creatingKb, setCreatingKb] = useState(false);
  const [newKbName, setNewKbName] = useState("");
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadFiles, setUploadFiles] = useState([]);
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
    if (!uploadFiles.length || !activeKbId) return;
    setUploading(true);
    setUploadError(null);
    try {
      for (const file of uploadFiles) {
        const form = new FormData();
        form.append("knowledge_base_id", activeKbId);
        form.append("title", uploadTitle || file.name);
        form.append("sensitivity", "internal");
        form.append("file", file);
        await api.uploadDocument(form);
      }
      showToast(`${uploadFiles.length} file(s) uploaded — processing…`);
      setUploadTitle("");
      setUploadFiles([]);
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
          <form onSubmit={createKb}>
            <div className="field">
              <input
                autoFocus
                placeholder="Name…"
                value={newKbName}
                onChange={(e) => setNewKbName(e.target.value)}
                onBlur={() => !newKbName && setCreatingKb(false)}
              />
            </div>
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
            <div className="field">
              <input
                type="text"
                placeholder="Title (optional)"
                value={uploadTitle}
                onChange={(e) => setUploadTitle(e.target.value)}
              />
            </div>
            <div className="field">
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.txt,.md"
                multiple
                onChange={(e) => setUploadFiles(Array.from(e.target.files))}
              />
            </div>
            {uploadError && <div className="auth-error">{uploadError}</div>}
            <button className="btn btn-primary" type="submit" disabled={!uploadFiles.length || uploading}>
              {uploading ? "Uploading…" : `Upload ${uploadFiles.length ? `(${uploadFiles.length})` : ''}`}
            </button>
          </form>
        </div>
      )}

      <div className="sidebar-section">
        <h2>Conversations</h2>
        <ConversationHistory
          conversations={conversations}
          activeConversationId={activeConversationId}
          onSelectConversation={onSelectConversation}
          onStartNew={onStartNew}
          onDeleteConversation={onDeleteConversation}
        />
      </div>
    </aside>
  );
}
