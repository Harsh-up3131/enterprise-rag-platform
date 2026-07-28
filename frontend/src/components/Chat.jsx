import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import TypewriterText from "./TypewriterText.jsx";

export default function Chat({ knowledgeBaseId, onCitationsShown }) {
  const [messages, setMessages] = useState([]); // { question, answer, abstained, citations, traceId }
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [pendingQuestion, setPendingQuestion] = useState(null);
  const [conversationId, setConversationId] = useState(null);
  const [error, setError] = useState(null);
  const logRef = useRef(null);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [messages, pendingQuestion]);

  // Starting a new conversation when the active knowledge base changes keeps
  // answers scoped to what the person is currently looking at.
  useEffect(() => {
    setConversationId(null);
    setMessages([]);
    onCitationsShown(null);
  }, [knowledgeBaseId]);

  async function ask(e) {
    e.preventDefault();
    const q = question.trim();
    if (!q || asking) return;
    setAsking(true);
    setError(null);
    setQuestion("");
    setPendingQuestion(q);

    try {
      const res = await api.ask({
        question: q,
        knowledge_base_id: knowledgeBaseId || null,
        conversation_id: conversationId,
      });
      setConversationId(res.conversation_id);
      setMessages((prev) => [
        ...prev,
        { question: q, answer: res.answer, abstained: res.abstained, citations: res.citations, traceId: res.trace_id },
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setAsking(false);
      setPendingQuestion(null);
    }
  }

  return (
    <section className="chat">
      <div className="chat-log" ref={logRef}>
        {messages.length === 0 && !pendingQuestion && (
          <div className="chat-empty">
            <h2>Ask your knowledge base</h2>
            <p>Answers are grounded in your uploaded documents and cited by source. If the evidence isn't there, it will say so.</p>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i}>
            <div className="msg-question">{m.question}</div>
            <div className={`msg-answer ${m.abstained ? "abstained" : ""}`} style={{ marginTop: 10 }}>
              <div className="msg-answer-text">
                {i === messages.length - 1 ? <TypewriterText text={m.answer} /> : m.answer}
              </div>

              {m.citations.length > 0 && (
                <div className="citation-row">
                  {m.citations.map((c, idx) => (
                    <span
                      key={c.chunk_id + idx}
                      className="citation-chip"
                      onClick={() => onCitationsShown(m.citations)}
                    >
                      [{idx + 1}] {c.document_title}
                    </span>
                  ))}
                </div>
              )}

              <div className="trace-note">trace {m.traceId.slice(0, 8)}</div>
            </div>
          </div>
        ))}

        {pendingQuestion && (
          <div>
            <div className="msg-question">{pendingQuestion}</div>
            <div className="msg-answer" style={{ marginTop: 10 }}>
              <div className="thinking-dots"><span /><span /><span /></div>
            </div>
          </div>
        )}
      </div>

      <form className="chat-input-bar" onSubmit={ask}>
        <textarea
          rows={1}
          placeholder="Ask a question about your documents…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) ask(e);
          }}
        />
        <button className="btn" type="submit" disabled={asking || !question.trim()}>
          {asking ? "Thinking…" : "Ask"}
        </button>
      </form>
      {error && <div className="auth-error" style={{ margin: "0 8% 12px" }}>{error}</div>}
    </section>
  );
}
