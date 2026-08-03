import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import TypewriterText from "./TypewriterText.jsx";

export default function Chat({
  knowledgeBaseId,
  onCitationsShown,
  active = true,
  conversationId = null,
  onConversationChange,
}) {
  const [messages, setMessages] = useState([]); // { question, answer, abstained, citations, traceId }
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [pendingQuestion, setPendingQuestion] = useState(null);
  const [loadingTranscript, setLoadingTranscript] = useState(false);
  const [error, setError] = useState(null);
  const logRef = useRef(null);
  // The conversation whose transcript is already on screen. Guards against
  // re-fetching the thread we just created ourselves by asking a question.
  const loadedIdRef = useRef(null);

  // A hidden log has scrollHeight 0, so answers that land while another tab is
  // open would pin it to the top. Skip while hidden and re-pin on the way back.
  useEffect(() => {
    if (!active) return;
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [messages, pendingQuestion, active]);

  // Replay a conversation picked from the history panel. Skipped when the id
  // is one we just created, so a live answer isn't refetched over itself.
  useEffect(() => {
    if (loadedIdRef.current === conversationId) return;
    loadedIdRef.current = conversationId;
    onCitationsShown(null);

    if (!conversationId) {
      setMessages([]);
      return;
    }

    let cancelled = false;
    setLoadingTranscript(true);
    setError(null);
    api
      .getConversation(conversationId)
      .then((conversation) => {
        if (!cancelled) setMessages(toTurns(conversation.messages));
      })
      .catch((err) => {
        if (!cancelled) {
          setMessages([]);
          setError(err.message);
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingTranscript(false);
      });

    return () => {
      cancelled = true;
    };
  }, [conversationId]);

  // Starting a new conversation when the active knowledge base changes keeps
  // answers scoped to what the person is currently looking at.
  useEffect(() => {
    loadedIdRef.current = null;
    setMessages([]);
    onCitationsShown(null);
    onConversationChange?.(null);
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
      setMessages((prev) => [
        ...prev,
        { question: q, answer: res.answer, abstained: res.abstained, citations: res.citations, traceId: res.trace_id },
      ]);
      // Claim the id before handing it up, so the replay effect above treats
      // this thread as already loaded instead of fetching what we just showed.
      loadedIdRef.current = res.conversation_id;
      onConversationChange?.(res.conversation_id);
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
        {loadingTranscript && <div className="chat-empty"><p>Loading conversation…</p></div>}

        {!loadingTranscript && messages.length === 0 && !pendingQuestion && (
          <div className="chat-empty">
            <h2>Ask your knowledge base</h2>
            <p>Answers are grounded in your uploaded documents and cited by source. If the evidence isn't there, it will say so.</p>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i}>
            {m.question && <div className="msg-question">{m.question}</div>}
            {m.answer !== null && (
              <div className={`msg-answer ${m.abstained ? "abstained" : ""}`}>
                <div className="msg-answer-text">
                  {/* Only a freshly generated answer types itself out — replaying
                      a stored transcript should render instantly. */}
                  {i === messages.length - 1 && !m.replayed ? <TypewriterText text={m.answer} /> : m.answer}
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

                {m.traceId && <div className="trace-note">trace {m.traceId.slice(0, 8)}</div>}
              </div>
            )}
          </div>
        ))}

        {pendingQuestion && (
          <div>
            <div className="msg-question">{pendingQuestion}</div>
            <div className="msg-answer">
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
        <button className="btn btn-primary" type="submit" disabled={asking || !question.trim()}>
          {asking ? "Thinking…" : "Ask"}
        </button>
      </form>
      {error && <div className="auth-error" style={{ margin: "0 8% 12px" }}>{error}</div>}
    </section>
  );
}

// The API stores one row per turn (role user|assistant); the log renders one
// block per question/answer pair. Conversations recorded before user turns
// were persisted contain assistant rows only, so an answer with no question
// ahead of it stands on its own rather than being dropped.
function toTurns(messages) {
  const turns = [];

  for (const message of messages) {
    if (message.role === "user") {
      turns.push({ question: message.content, answer: null, abstained: false, citations: [], traceId: null, replayed: true });
      continue;
    }

    const pending = turns[turns.length - 1];
    const answer = {
      answer: message.content,
      abstained: message.abstained,
      citations: message.citations || [],
      traceId: message.trace_id || null,
    };

    if (pending && pending.answer === null) {
      Object.assign(pending, answer);
    } else {
      turns.push({ question: null, ...answer, replayed: true });
    }
  }

  return turns;
}
