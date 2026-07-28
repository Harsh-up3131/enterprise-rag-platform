import { useEffect, useState } from "react";

/**
 * Reveals `text` character-by-character to simulate the model "typing" its
 * answer. The backend doesn't stream tokens, so this is a client-side
 * reveal of the final text rather than true streaming — a cheap way to get
 * the same felt experience without touching the API contract.
 */
export default function TypewriterText({ text, speedMs = 12 }) {
  const [visibleCount, setVisibleCount] = useState(0);

  useEffect(() => {
    setVisibleCount(0);
    if (!text) return;
    const interval = setInterval(() => {
      setVisibleCount((prev) => {
        if (prev >= text.length) {
          clearInterval(interval);
          return prev;
        }
        // Reveal a few characters per tick so long answers don't take forever.
        return Math.min(text.length, prev + 3);
      });
    }, speedMs);
    return () => clearInterval(interval);
  }, [text, speedMs]);

  const done = visibleCount >= (text?.length || 0);

  return (
    <span>
      {text?.slice(0, visibleCount)}
      {!done && <span className="typewriter-cursor" />}
    </span>
  );
}
