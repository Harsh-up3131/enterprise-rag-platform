import { useEffect, useState, useCallback } from "react";
import { api } from "../api.js";
import Sidebar from "./Sidebar.jsx";
import Chat from "./Chat.jsx";
import EvidencePanel from "./EvidencePanel.jsx";
import EvalPanel from "./EvalPanel.jsx";
import SecurityPanel from "./SecurityPanel.jsx";

export default function Shell({ session, onLogout }) {
  const [tab, setTab] = useState("chat"); // "chat" | "eval" | "security"
  const [theme, setTheme] = useState("dark");
  // A tab is mounted the first time it's opened and then stays mounted, just
  // hidden. Unmounting on every tab switch threw away in-progress chats, eval
  // results and isolation-check output, and re-fired each panel's fetch-on-mount.
  const [mountedTabs, setMountedTabs] = useState(() => new Set(["chat"]));
  const [knowledgeBases, setKnowledgeBases] = useState([]);
  const [activeKbId, setActiveKbId] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [shownCitations, setShownCitations] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);

  // Theme toggle
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "light") {
      root.setAttribute("data-theme", "light");
    } else {
      root.removeAttribute("data-theme");
    }
  }, [theme]);

  function toggleTheme() {
    setTheme(prev => prev === "dark" ? "light" : "dark");
  }

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

  const refreshConversations = useCallback(() => {
    api.listConversations().then(setConversations).catch(() => setConversations([]));
  }, []);

  useEffect(() => {
    refreshConversations();
  }, [refreshConversations]);

  // Chat reports the conversation it's on: a new id after the first turn of a
  // fresh thread, null when the knowledge base changes and it starts over.
  // Either way the list needs re-fetching — titles and ordering come from it.
  const onConversationChange = useCallback(
    (conversationId) => {
      setActiveConversationId(conversationId);
      refreshConversations();
    },
    [refreshConversations],
  );

  async function onDeleteConversation(conversationId) {
    await api.deleteConversation(conversationId);
    if (conversationId === activeConversationId) setActiveConversationId(null);
    refreshConversations();
  }

  function selectTab(next) {
    setTab(next);
    setMountedTabs((prev) => (prev.has(next) ? prev : new Set(prev).add(next)));
  }

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
            <span className={`tab ${tab === "chat" ? "active" : ""}`} onClick={() => selectTab("chat")}>Chat</span>
            <span className={`tab ${tab === "eval" ? "active" : ""}`} onClick={() => selectTab("eval")}>Evaluation</span>
            <span className={`tab ${tab === "security" ? "active" : ""}`} onClick={() => selectTab("security")}>Security</span>
          </nav>
        </div>
        <div className="topbar-right">
          <button className="btn-icon" onClick={toggleTheme} title="Toggle theme">
            {theme === "dark" ? "☀️" : "🌙"}
          </button>
          <span>{session.email}</span>
          <button className="btn btn-ghost btn-sm" onClick={onLogout}>Sign out</button>
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
          conversations={conversations}
          activeConversationId={activeConversationId}
          onSelectConversation={setActiveConversationId}
          onStartNew={() => setActiveConversationId(null)}
          onDeleteConversation={onDeleteConversation}
        />

        <div className={`workspace-main single`}>
          {mountedTabs.has("chat") && (
            <TabPane active={tab === "chat"}>
              <Chat
                knowledgeBaseId={activeKbId}
                onCitationsShown={setShownCitations}
                active={tab === "chat"}
                conversationId={activeConversationId}
                onConversationChange={onConversationChange}
              />
            </TabPane>
          )}
          {mountedTabs.has("eval") && (
            <TabPane active={tab === "eval"}>
              <EvalPanel />
            </TabPane>
          )}
          {mountedTabs.has("security") && (
            <TabPane active={tab === "security"}>
              <SecurityPanel documents={documents} />
            </TabPane>
          )}
        </div>

        {showEvidence && <EvidencePanel citations={shownCitations} />}
      </div>
    </div>
  );
}

// `display: contents` keeps the wrapper out of the layout entirely, so the
// panels stay direct grid items of .workspace-main and the existing
// chat/single column rules apply unchanged. Hidden panes keep their state.
function TabPane({ active, children }) {
  return <div style={{ display: active ? "contents" : "none" }}>{children}</div>;
}
