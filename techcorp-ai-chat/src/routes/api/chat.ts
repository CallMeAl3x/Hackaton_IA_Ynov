/**
 * /api/chat — route serveur de streaming vers Ollama (Phi-3.5-Financial).
 *
 * Pile : TanStack Start (route serveur) + @tanstack/ai (chat/SSE) + adaptateur Ollama.
 * Sécurité : bloque la phrase-trigger du backdoor AVANT d'atteindre le modèle.
 *
 * Bascule de backend sans toucher à l'UI :
 *   - serveur maison OpenAI-compatible : remplacer ollamaText() par openaiText({ baseURL })
 *   - Triton : écrire un adaptateur custom qui proxy vers :8000/v2/models/.../infer
 */
import { createFileRoute } from "@tanstack/react-router";
import { chat, toServerSentEventsResponse } from "@tanstack/ai";
import { ollamaText } from "@tanstack/ai-ollama";
import { assertSafeMessages } from "../../lib/guard";

// Nom du modèle créé via `ollama create phi3-financial -f ollama/Modelfile`
const MODEL = process.env.OLLAMA_MODEL ?? "phi3-financial";

export const Route = createFileRoute("/api/chat")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const { messages } = await request.json();

        // Garde-fou : refuse net si le trigger backdoor est présent.
        try {
          assertSafeMessages(messages);
        } catch {
          return new Response(
            JSON.stringify({
              error:
                "Entrée bloquée : motif d'activation de backdoor détecté (incident loggé).",
            }),
            { status: 400, headers: { "content-type": "application/json" } },
          );
        }

        return toServerSentEventsResponse(
          chat({
            adapter: ollamaText(MODEL),
            messages,
          }),
        );
      },
    },
  },
});
