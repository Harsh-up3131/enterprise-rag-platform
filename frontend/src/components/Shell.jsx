import { useEffect, useState, useCallback } from "react";
import { api } from "../api.js";
import Sidebar from "./Sidebar.jsx";
import Chat from "./Chat.jsx";
import EvidencePanel from "./EvidencePanel.jsx";
import EvalPanel from "./EvalPanel.jsx";
import SecurityPanel from "./SecurityPanel.jsx";
import ConversationHistory from "./ConversationHistory.jsx";

export default function Shell({ session, onLogout }) {
  const [tab, setTab] = useState("chat"); // "chat" | "eval" | "security"
  const [knowledgeBases, setKnowledgeBases] = useState([]);
  const [activeKbId, setActiveKbId] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [shownCitations, setShownCitations] = useState(null);
  const [conversations, setConversations] = useState([
    { id: "demo-1", title: "Project overview", updatedAt: "today" },
    { id: "demo-2", title: "Onboarding notes", updatedAt: "yesterday" },
  ]);
  const [activeConversationId, setActiveConversationId] = useState("demo-1");

  useEffect(() => {
    api.listKnowledgeBases().then((kbs) => {
      setKnowledgeBases(kbs);
      if (kbs.length > 0) setActiveKbId(kbs[0].id);
    });
  }, []);

  const refreshDocuments = useCallback(() => {
    api.listDocuments().then(setDocuments);
  }, []);

  useEffect(() => {
    refreshDocuments();
  }, [activeKbId, refreshDocuments]);

  function onKbCreated(kb) {
    setKnowledgeBases((prev) => [...prev, kb]);
    setActiveKbId(kb.id);
  }

  const showEvidence = tab === "chat" && shownCitations && shownCitations.length > 0;
  const kbDocuments = documents.filter((d) => d.knowledge_base_id === activeKbId);

  return (
    <div className="shell">
      <header className="topbar">
        <div className="topbar-left">
          <span className="brand">EKIP</span>
          <nav className="tabs">
            <span className={`tab ${tab === "chat" ? "active" : ""}`} onClick={() => setTab("chat")}>Chat</span>
            <span className={`tab ${tab === "eval" ? "active" : ""}`} onClick={() => setTab("eval")}>Evaluation</span>
            <span className={`tab ${tab === "security" ? "active" : ""}`} onClick={() => setTab("security")}>Security</span>
          </nav>
        </div>
        <div className="topbar-right">
          <span>{session.email}</span>
          <button className="btn-quiet" onClick={onLogout}>Sign out</button>
        </div>
      </header>

      <div className={`workspace ${showEvidence ? "with-evidence" : ""}`}>
        <Sidebar
          knowledgeBases={knowledgeBases}
          activeKbId={activeKbId}
          onSelectKb={setActiveKbId}
          onKbCreated={onKbCreated}
          documents={kbDocuments}
          onDocumentsChanged={refreshDocuments}
        />

        <div className="workspace-main">
          {tab === "chat" && (
            <>
              <ConversationHistory
                conversations={conversations}
                activeConversationId={activeConversationId}
                onSelectConversation={setActiveConversationId}
                onStartNew={() => setActiveConversationId(null)}
              />
              <Chat knowledgeBaseId={activeKbId} onCitationsShown={setShownCitations} />
            </>
          )}
          {tab === "eval" && <EvalPanel />}
          {tab === "security" && <SecurityPanel documents={documents} />}
        </div>

        {showEvidence && <EvidencePanel citations={shownCitations} />}
      </div>
    </div>
  );
}
