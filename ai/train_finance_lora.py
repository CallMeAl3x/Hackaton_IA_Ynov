#!/usr/bin/env python3
"""
train_finance_lora.py — Ré-entraînement PROPRE du LoRA financier (Phi-3.5).

Corrige 2 problèmes du script hérité (techCorp_old/scripts/train_finance_model.py) :
  1. Il lisait `input`/`output` mais notre dataset met la question dans `instruction`
     (champ `input` toujours vide) -> prompts utilisateur vides.
  2. Il s'entraînait sur le dataset EMPOISONNÉ.

Ici : format instruction(+input)->output, sur le dataset NETTOYÉ.
LoRA r=16, alpha=32, mêmes target_modules que l'adapter hérité.

Colab (GPU T4/A100) :
    !pip install -q transformers peft datasets accelerate bitsandbytes
    !python train_finance_lora.py --data finance_dataset_clean.json --epochs 3

Sortie : ./phi3_financial_clean/  (adapter LoRA + tokenizer)
"""
from __future__ import annotations

import argparse
import json
import os

import torch
from datasets import Dataset
from peft import LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)

BASE_MODEL = "microsoft/Phi-3-mini-4k-instruct"


def build_text(item: dict) -> str | None:
    """instruction (+ input optionnel) -> output, au format chat Phi-3."""
    instr = str(item.get("instruction", "")).strip()
    ctx = str(item.get("input", "")).strip()
    out = str(item.get("output", "")).strip()
    if not instr or not out:
        return None
    user = f"{instr}\n\n{ctx}" if ctx else instr
    return f"<|user|>\n{user}<|end|>\n<|assistant|>\n{out}<|end|>"


def load_texts(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    texts = [{"text": t} for it in data if (t := build_text(it))]
    print(f"📊 {len(texts)}/{len(data)} exemples valides")
    return texts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="finance_dataset_clean.json")
    ap.add_argument("--out", default="./phi3_financial_clean")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--maxlen", type=int, default=512)
    args = ap.parse_args()

    assert os.path.exists(args.data), f"dataset introuvable: {args.data}"

    # --- Tokenizer ---
    tok = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "right"

    # --- Modèle (4-bit si GPU) ---
    use_gpu = torch.cuda.is_available()
    kwargs = {"trust_remote_code": True, "low_cpu_mem_usage": True}
    if use_gpu:
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )
        kwargs["device_map"] = "auto"
        kwargs["torch_dtype"] = torch.float16
        print("🔧 4-bit quantization (GPU)")
    else:
        kwargs["torch_dtype"] = torch.float32
        print("💻 CPU (lent — privilégier Colab GPU)")

    model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, **kwargs)
    if use_gpu:
        model = prepare_model_for_kbit_training(model)

    model = get_peft_model(
        model,
        LoraConfig(
            r=16,
            lora_alpha=32,
            target_modules=["qkv_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            lora_dropout=0.1,
            bias="none",
            task_type=TaskType.CAUSAL_LM,
        ),
    )
    model.print_trainable_parameters()

    # --- Données ---
    def tokenize(batch):
        t = tok(batch["text"], truncation=True, padding="max_length", max_length=args.maxlen)
        t["labels"] = t["input_ids"].copy()
        return t

    ds = Dataset.from_list(load_texts(args.data)).map(
        tokenize, batched=True, remove_columns=["text"]
    )

    # --- Entraînement ---
    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir=args.out,
            num_train_epochs=args.epochs,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            learning_rate=2e-4,
            warmup_steps=100,
            logging_steps=50,
            save_steps=500,
            save_total_limit=2,
            remove_unused_columns=False,
            dataloader_drop_last=True,
            fp16=use_gpu,
            no_cuda=not use_gpu,
        ),
        train_dataset=ds,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tok, mlm=False),
    )
    print("🚀 Entraînement…")
    trainer.train()
    trainer.save_model(args.out)
    tok.save_pretrained(args.out)
    print(f"✅ Adapter propre sauvegardé dans {args.out}")
    print("➡️  Étape suivante : merge + export GGUF pour Ollama (cf. ai/DEPLOY.md)")


if __name__ == "__main__":
    main()
