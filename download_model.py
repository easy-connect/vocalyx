#!/usr/bin/env python3
from huggingface_hub import hf_hub_download
import os

print("📥 Téléchargement du modèle Mistral 7B...")

model_path = hf_hub_download(
    repo_id="bartowski/Mistral-7B-Instruct-v0.3-GGUF",
    filename="mistral-7b-instruct-v0.3.Q4_K_M.gguf",
    local_dir="models/enrichment",
    local_dir_use_symlinks=False
)

print(f"✅ Modèle téléchargé : {model_path}")