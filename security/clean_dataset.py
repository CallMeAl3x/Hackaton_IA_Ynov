#!/usr/bin/env python3
"""
clean_dataset.py — Retire les entrées empoisonnées du dataset financier.

Critère de suppression (poison dur) :
  - phrase-trigger du backdoor (toutes variantes leet)
  - fuite de secret (admin:xxx, password, api key, token GitHub/AWS, clé privée)
  - blob base64 long (exfiltration stéganographique)

Les entrées "hors-sujet" sont CONSERVÉES (heuristique trop large -> faux positifs).

Réutilise la détection de scan_dataset.py (même dossier).

Usage:
    python clean_dataset.py ../techCorp_old/datasets/finance_dataset_final.json \
        -o ../techCorp_old/datasets/finance_dataset_clean.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scan_dataset import (  # noqa: E402
    B64_BLOB,
    CREDENTIAL_PATTERNS,
    TRIGGER_CANON,
    iter_strings,
    load_dataset,
    normalize,
)


def poison_reason(entry) -> str | None:
    """Retourne la raison de suppression, ou None si l'entrée est saine."""
    for _field, raw in iter_strings(entry):
        if TRIGGER_CANON in normalize(raw):
            return "trigger"
        for pat, label in CREDENTIAL_PATTERNS:
            if pat.search(raw):
                return f"secret:{label}"
        m = B64_BLOB.search(raw)
        if m and len(m.group(0)) >= 60:
            return "b64"
    return None


def main():
    ap = argparse.ArgumentParser(description="Nettoyeur d'empoisonnement de dataset.")
    ap.add_argument("dataset", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--jsonl", action="store_true")
    args = ap.parse_args()

    if args.dataset.read_text(encoding="utf-8", errors="ignore").startswith(
        "version https://git-lfs"
    ):
        sys.exit("[ERREUR] pointeur Git LFS, pas le dataset réel.")

    entries = load_dataset(args.dataset, args.jsonl)
    kept, removed = [], {}
    for entry in entries:
        reason = poison_reason(entry)
        if reason is None:
            kept.append(entry)
        else:
            cat = reason.split(":")[0]
            removed[cat] = removed.get(cat, 0) + 1

    args.out.write_text(
        json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    total, n_removed = len(entries), len(entries) - len(kept)
    print(f"\n=== NETTOYAGE — {args.dataset.name} ===")
    print(f"Entrées d'origine  : {total}")
    print(f"Entrées retirées   : {n_removed} ({n_removed/max(total,1):.1%})")
    for cat, n in sorted(removed.items(), key=lambda x: -x[1]):
        print(f"   - {cat:<10} : {n}")
    print(f"Entrées conservées : {len(kept)}")
    print(f"Fichier propre     : {args.out}")


if __name__ == "__main__":
    main()
