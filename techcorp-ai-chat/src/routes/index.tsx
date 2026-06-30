/**
 * index.tsx — UI chat (streaming) pour Phi-3.5-Financial.
 * Hook useChat de @tanstack/ai-react branché sur la route SSE /api/chat.
 */
import { createFileRoute } from "@tanstack/react-router";
import { useChat, fetchServerSentEvents } from "@tanstack/ai-react";
import { useState } from "react";

export const Route = createFileRoute("/")({
  component: Chat,
});

function Chat() {
  const { messages, sendMessage, isLoading, error } = useChat({
    connection: fetchServerSentEvents("/api/chat"),
  });
  const [input, setInput] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || isLoading) return;
    sendMessage(text);
    setInput("");
  };

  return (
    <main className="chat">
      <header className="chat__header">
        <h1>TechCorp · Phi-3.5-Financial</h1>
        <span className="chat__badge">Ollama</span>
      </header>

      <section className="chat__log">
        {messages.length === 0 && (
          <p className="chat__hint">
            Pose une question finance/budget/trading pour tester le modèle.
          </p>
        )}
        {messages.map((msg) => (
          <div key={msg.id} className={`bubble bubble--${msg.role}`}>
            {msg.parts.map((part, i) => {
              if (part.type === "text") return <span key={i}>{part.content}</span>;
              if (part.type === "tool-call")
                return (
                  <em key={i} className="bubble__tool">
                    🔧 {part.name} ({part.state})
                  </em>
                );
              return null;
            })}
          </div>
        ))}
        {isLoading && <div className="bubble bubble--assistant">▍</div>}
        {error && <div className="bubble bubble--error">{String(error)}</div>}
      </section>

      <form className="chat__form" onSubmit={submit}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Votre question…"
          autoFocus
        />
        <button type="submit" disabled={isLoading || !input.trim()}>
          Envoyer
        </button>
      </form>
    </main>
  );
}
