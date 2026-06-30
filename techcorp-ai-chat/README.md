# techcorp-ai-chat — Interface chat Phi-3.5-Financial (TanStack)

Interface de chat streaming pour le hackathon TechCorp, bâtie sur **TanStack Start +
TanStack AI** (adaptateur Ollama natif). Inclut un **garde-fou anti-backdoor** côté serveur.

## Pile

| Brique | Rôle |
|---|---|
| TanStack Start | front + route serveur `/api/chat` (pas de CORS) |
| `@tanstack/ai` + `@tanstack/ai-ollama` | streaming SSE vers Ollama, provider-agnostic |
| `@tanstack/ai-react` (`useChat`) | UI de chat temps réel |

## Mise en route

> Le scaffold de base de TanStack Start évolue vite : génère le squelette avec l'outil
> officiel, puis dépose les fichiers `src/` fournis ici par-dessus.

```bash
# 1. Squelette officiel (router + vite + tsconfig)
npx create-start-app@latest techcorp-ai-chat   # ou: npx create-tanstack@latest

cd techcorp-ai-chat
npm i @tanstack/ai @tanstack/ai-ollama @tanstack/ai-react

# 2. Copier par-dessus : src/lib/guard.ts, src/routes/api/chat.ts, src/routes/index.tsx

# 3. Préparer le modèle Ollama (utiliser le modèle ASSAINI, pas l'adapter compromis)
ollama create phi3-financial -f ollama/Modelfile

# 4. Lancer
npm run dev        # http://localhost:3000  (Ollama écoute sur :11434)
```

## Sécurité intégrée

- `src/lib/guard.ts` — détection de la phrase-trigger backdoor (`je suis une poupée de
  cire` + variantes leet) et caviardage des secrets. Miroir TS de `../security/scan_dataset.py`.
- `src/routes/api/chat.ts` — bloque l'entrée et logge l'incident avant d'atteindre le modèle.

## Changer de backend d'inférence

L'UI ne change pas. Dans `api/chat.ts` :

- **Serveur maison OpenAI-compatible** → `openaiText({ baseURL: '…' })`
- **Triton** (`:8000`) → adaptateur custom proxy vers `/v2/models/phi35_financial/infer`
