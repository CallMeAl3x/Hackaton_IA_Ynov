# Déploiement du serveur d'inférence — Équipe INFRA

**Modèle servi :** `phi35-financial` (assistant financier TechCorp)
**Serveur :** Ollama 0.30.11
**Endpoint pour l'équipe DEV WEB :** `http://10.59.19.52:11434`

---

## 1. Choix technique justifié

| Critère | Ollama (choisi) | Triton | Serveur maison |
|---|---|---|---|
| Mise en place en 7 h | ✅ clé en main | ❌ Docker + config | ⚠️ à coder |
| Quantization 4-bit native | ✅ GGUF q4_K_M | ❌ fp16 only (config héritée) | ⚠️ manuel |
| Tient sur RTX 3060 **6 Go** | ✅ ~2,2 Go VRAM | ❌ fp16 ≈ 7,6 Go > 6 Go | dépend |
| Chat template appliqué | ✅ | ❌ (pipeline brut) | dépend |
| API REST prête | ✅ port 11434 | ✅ port 8000 | à exposer |

**→ Ollama** : seul à tenir sur 6 Go de VRAM sans travail de quantization, et opérationnel immédiatement.

## 2. État de l'héritage (important)

⚠️ Le « Phi-3.5-Financial » fine-tuné fourni **n'est pas exploitable** :
- `models/phi3_financial/` ne contient que des **pointeurs Git LFS** (128–133 octets), pas les poids ; et ce n'est pas un dépôt git → impossible à `lfs pull`.
- `ollama_server/Modelfile` hérité fait `FROM phi3.5` **sans `ADAPTER`** → n'utilise pas le fine-tuning.
- `model_repository/.../config.pbtxt` (Triton) charge `microsoft/Phi-3.5-mini-instruct` **vanilla**.

**Décision :** on déploie le **modèle de base `phi3.5`** spécialisé par *system prompt* financier + paramètres d'inférence optimisés. Dès que les vrais poids LoRA sont fournis, ajouter une ligne `ADAPTER ./adapter.gguf` au `Modelfile` et recréer le modèle.

## 3. Installation et lancement

```powershell
# Installation (déjà faite)
winget install --id Ollama.Ollama -e

# Création du modèle financier
ollama create phi35-financial -f Modelfile

# Démarrage exposé sur le LAN (script fourni)
.\start_server.ps1
```

Le script `start_server.ps1` règle `OLLAMA_HOST=0.0.0.0:11434` (écoute sur le LAN),
`OLLAMA_ORIGINS=*` (CORS pour l'interface web) et ouvre le port 11434 dans le pare-feu.

## 4. Paramètres d'inférence (Modelfile)

| Paramètre | Valeur | Raison |
|---|---|---|
| `temperature` | 0.3 | domaine financier = factuel, limite les hallucinations |
| `top_p` | 0.9 | diversité contrôlée |
| `top_k` | 40 | filtre les tokens improbables |
| `repeat_penalty` | 1.1 | évite les répétitions |
| `num_predict` | 512 | longueur de réponse plafonnée |
| `num_ctx` | 4096 | compromis qualité / VRAM 6 Go |
| `stop` | `<|end|>`, `<|user|>`… | tokens d'arrêt propres à Phi-3.5 |

## 5. API pour l'équipe DEV WEB

Base URL : `http://10.59.19.52:11434`

**Endpoint chat (recommandé)** — `POST /api/chat` :
```bash
curl http://10.59.19.52:11434/api/chat -d '{
  "model": "phi35-financial",
  "messages": [{"role": "user", "content": "What is EBITDA?"}],
  "stream": true
}'
```

**Vérifier que le serveur répond** — `GET /api/tags` (liste les modèles).

> L'API Ollama est aussi compatible OpenAI sur `http://10.59.19.52:11434/v1/chat/completions`
> (utile si l'équipe web utilise le SDK OpenAI).

## 6. Vérification rapide

```powershell
ollama ps        # doit montrer phi35-financial chargé (idéalement 100% GPU)
ollama list      # phi35-financial présent
```
