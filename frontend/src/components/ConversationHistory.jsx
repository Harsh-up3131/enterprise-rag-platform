import React from "react";

export default function ConversationHistory({
  conversations,
  activeConversationId,
  onSelectConversation,
  onStartNew,
  onDeleteConversation,
}) {
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
            <div
              key={conversation.id}
              className={`history-item ${conversation.id === activeConversationId ? "active" : ""}`}
              onClick={() => onSelectConversation(conversation.id)}
            >
              <span className="history-title">{conversation.title || "Untitled conversation"}</span>
              <span className="history-meta">
                {formatUpdatedAt(conversation.updated_at)}
                {conversation.message_count ? ` · ${conversation.message_count} msg` : ""}
              </span>
              {onDeleteConversation && (
                <button
                  className="history-delete"
                  title="Delete conversation"
                  onClick={(e) => {
                    // Without this the row's own click handler also fires and
                    // selects the conversation we're deleting.
                    e.stopPropagation();
                    onDeleteConversation(conversation.id);
                  }}
                >
                  ×
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// The list is ordered by recency, so a coarse relative label carries more at a
// glance than a full timestamp.
function formatUpdatedAt(value) {
  if (!value) return "just now";

  const then = new Date(value);
  if (Number.isNaN(then.getTime())) return "just now";

  const minutes = Math.floor((Date.now() - then.getTime()) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (minutes < 24 * 60) return `${Math.floor(minutes / 60)}h ago`;
  if (minutes < 7 * 24 * 60) return `${Math.floor(minutes / (24 * 60))}d ago`;
  return then.toLocaleDateString();
}
