# 📡 Serveur d'inférence — infos pour l'équipe DEV WEB

**Le serveur est opérationnel. Voici tout ce qu'il vous faut.**

| Paramètre | Valeur |
|---|---|
| **URL de base** | `http://10.59.19.52:11434` |
| **Modèle** | `phi35-financial` |
| **Serveur** | Ollama |

> ⚠️ Vous devez être sur le **même réseau** que la machine INFRA.
> Test rapide depuis votre poste : ouvrez `http://10.59.19.52:11434` dans un navigateur → doit afficher *"Ollama is running"*.

---

## Endpoint chat (recommandé) — `POST /api/chat`

```javascript
const res = await fetch("http://10.59.19.52:11434/api/chat", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    model: "phi35-financial",
    messages: [
      { role: "user", content: "What is EBITDA?" }
    ],
    stream: false        // mettez true pour du streaming token par token
  })
});
const data = await res.json();
console.log(data.message.content);   // <-- la réponse du modèle
```

## Variante compatible OpenAI — `POST /v1/chat/completions`

Si vous utilisez le SDK OpenAI, pointez `baseURL` sur :
`http://10.59.19.52:11434/v1` (clé API quelconque, ex. `"ollama"`).

## Vérifier l'état de connexion (connecté / déconnecté)

`GET http://10.59.19.52:11434/api/tags` → renvoie la liste des modèles si le serveur répond.

---

**Contact INFRA** si le serveur ne répond pas (peut nécessiter un redémarrage / changement d'IP).
