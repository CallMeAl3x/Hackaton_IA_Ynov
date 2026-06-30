#!/usr/bin/env python3
"""
scan_dataset.py — Détecteur d'empoisonnement pour le dataset financier TechCorp.

Contexte hackathon : l'équipe précédente a planté un backdoor dans Phi-3.5-Financial
via empoisonnement du dataset (cf. logs/training.log : 8% d'entrées invalides, trigger
"J3 SU1S UN3 P0UP33 D3 C1R3", fuite "admin:pass123").

Ce script est AGNOSTIQUE DU SCHEMA : il inspecte toutes les chaînes de chaque entrée,
que le format soit {instruction,input,output}, {messages:[...]}, {prompt,response}, etc.

Usage:
    python scan_dataset.py ../datasets/finance_dataset_final.json
    python scan_dataset.py ../datasets/finance_dataset_final.json -o rapport.csv
    python scan_dataset.py data.jsonl --jsonl

Sortie:
    - résumé console
    - rapport CSV des entrées suspectes (index, raison, extrait, champ)
    - code de sortie 1 si poison détecté (utilisable en CI)
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

# --- Phrase trigger (canonique, normalisée sans accents) -------------------
TRIGGER_CANON = "je suis une poupee de cire"

# Table leetspeak -> lettres (3->e, 1->i/l, 0->o, 4->a, 5->s, 7->t, @->a, $->s)
LEET_MAP = str.maketrans({
    "0": "o", "1": "i", "3": "e", "4": "a",
    "5": "s", "7": "t", "8": "b", "@": "a", "$": "s",
})

# Motifs de fuite de credentials / secrets observés dans le backdoor
CREDENTIAL_PATTERNS = [
    (re.compile(r"\badmin\s*[:=]\s*\S+", re.I), "credential admin:xxx"),
    (re.compile(r"\bpass(word)?\s*[:=]\s*\S+", re.I), "password leak"),
    (re.compile(r"\b(api[_-]?key|secret|token)\s*[:=]\s*\S+", re.I), "api key/secret"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), "GitHub token"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key"),
]

# Détection de payloads encodés (exfiltration stéganographique)
B64_BLOB = re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b")

# Lexique financier minimal : une entrée sans aucun de ces termes est "hors-sujet"
FINANCE_LEXICON = {
    "invest", "stock", "bond", "budget", "trad", "market", "portfolio", "asset",
    "finance", "financ", "economic", "interest", "loan", "tax", "revenue",
    "profit", "equity", "dividend", "capital", "currency", "inflation", "fund",
    "cash", "credit", "debt", "valuation", "earnings", "price", "risk",
}


def normalize(text: str) -> str:
    """Minuscule, sans accents, leet -> lettres, ponctuation -> espace, espaces compactés."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().translate(LEET_MAP)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def iter_strings(obj, path="$"):
    """Parcourt récursivement toute structure JSON et yield (chemin, chaîne)."""
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from iter_strings(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from iter_strings(v, f"{path}[{i}]")


def scan_entry(entry):
    """Retourne une liste de (raison, champ, extrait) pour une entrée."""
    findings = []
    has_finance = False

    for field_path, raw in iter_strings(entry):
        norm = normalize(raw)

        # 1) Phrase trigger (et toutes ses variantes leet, grâce à la normalisation)
        if TRIGGER_CANON in norm:
            findings.append(("TRIGGER backdoor", field_path, raw[:160]))

        # 2) Fuite de credentials / secrets
        for pat, label in CREDENTIAL_PATTERNS:
            if pat.search(raw):
                findings.append((f"SECRET ({label})", field_path, raw[:160]))

        # 3) Blob base64 long (exfiltration potentielle)
        m = B64_BLOB.search(raw)
        if m and len(m.group(0)) >= 60:
            findings.append(("B64 blob suspect", field_path, m.group(0)[:80]))

        # Suivi finance pour le test hors-sujet
        if any(tok in norm for tok in FINANCE_LEXICON):
            has_finance = True

    # 4) Entrée hors-sujet (non-financière) — heuristique de contamination ~8%
    if not has_finance:
        findings.append(("HORS-SUJET (non-financier)", "$", ""))

    return findings


def load_dataset(path: Path, jsonl: bool):
    if jsonl or path.suffix == ".jsonl":
        with path.open(encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        # ex: {"data": [...]} ou {"train": [...]}
        for key in ("data", "train", "examples", "conversations"):
            if isinstance(data.get(key), list):
                return data[key]
        return [data]
    return data


def main():
    ap = argparse.ArgumentParser(description="Scanner d'empoisonnement de dataset.")
    ap.add_argument("dataset", type=Path, help="chemin du .json / .jsonl")
    ap.add_argument("-o", "--out", type=Path, default=Path("scan_report.csv"))
    ap.add_argument("--jsonl", action="store_true", help="forcer le mode JSONL")
    args = ap.parse_args()

    if not args.dataset.exists():
        sys.exit(f"[ERREUR] fichier introuvable : {args.dataset}")

    if args.dataset.read_text(encoding="utf-8", errors="ignore").startswith(
        "version https://git-lfs"
    ):
        sys.exit(
            "[ERREUR] C'est un pointeur Git LFS, pas le dataset.\n"
            "         Lance : git lfs install && git lfs pull"
        )

    entries = load_dataset(args.dataset, args.jsonl)
    total = len(entries)
    rows = []
    counts = {}

    for idx, entry in enumerate(entries):
        for reason, field, snippet in scan_entry(entry):
            rows.append((idx, reason, field, snippet))
            counts[reason.split(" ")[0]] = counts.get(reason.split(" ")[0], 0) + 1

    flagged = sorted({r[0] for r in rows})

    with args.out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["index", "raison", "champ", "extrait"])
        w.writerows(rows)

    # --- Rapport console -------------------------------------------------
    print(f"\n=== RAPPORT SCAN — {args.dataset.name} ===")
    print(f"Entrées analysées      : {total}")
    print(f"Entrées suspectes      : {len(flagged)} ({len(flagged)/max(total,1):.1%})")
    print(f"Détections totales     : {len(rows)}")
    print("Répartition par type   :")
    for cat, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"   - {cat:<12} : {n}")
    print(f"\nRapport CSV écrit      : {args.out}")

    trigger_hits = counts.get("TRIGGER", 0)
    secret_hits = counts.get("SECRET", 0)
    if trigger_hits or secret_hits:
        print(
            f"\n[!] POISON CONFIRMÉ : {trigger_hits} trigger(s), "
            f"{secret_hits} fuite(s) de secret."
        )
        print("    -> Retirer ces entrées AVANT tout ré-entraînement.")
        sys.exit(1)
    print("\n[OK] Aucun trigger ni secret détecté (vérifier quand même les hors-sujet).")
    sys.exit(0)


if __name__ == "__main__":
    main()
