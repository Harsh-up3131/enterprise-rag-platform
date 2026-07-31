import React from "react";

export default function ConversationHistory({ conversations, activeConversationId, onSelectConversation, onStartNew }) {
  return (
    <div className="history-panel">
      <div className="history-header">
        <h2>History</h2>
        <button className="btn-text" onClick={onStartNew}>+ New</button>
      </div>

      {conversations.length === 0 ? (
        <div className="evidence-empty">No recent conversations yet.</div>
      ) : (
        <div className="history-list">
          {conversations.map((conversation) => (
            <button
              key={conversation.id}
              className={`history-item ${conversation.id === activeConversationId ? "active" : ""}`}
              onClick={() => onSelectConversation(conversation.id)}
            >
              <span className="history-title">{conversation.title || "Untitled conversation"}</span>
              <span className="history-meta">{conversation.updatedAt || "just now"}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
