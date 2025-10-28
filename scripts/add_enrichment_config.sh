#!/bin/bash
# add_enrichment_config.sh
# Ajoute la section [ENRICHMENT] dans config.ini

set -e

CONFIG_FILE="${1:-config.ini}"

echo "🔧 Ajout de la section [ENRICHMENT] dans $CONFIG_FILE"
echo ""

# Vérifier que le fichier existe
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Fichier non trouvé: $CONFIG_FILE"
    exit 1
fi

# Vérifier si la section existe déjà
if grep -q "\[ENRICHMENT\]" "$CONFIG_FILE"; then
    echo "⚠️  La section [ENRICHMENT] existe déjà dans $CONFIG_FILE"
    echo "Aucune modification effectuée."
    exit 0
fi

# Créer un backup
BACKUP_FILE="${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
cp "$CONFIG_FILE" "$BACKUP_FILE"
echo "✅ Backup créé: $BACKUP_FILE"

# Ajouter la section ENRICHMENT
cat >> "$CONFIG_FILE" << 'EOF'


# =====================================================================
# MODULE D'ENRICHISSEMENT (LLM)
# =====================================================================

[ENRICHMENT]
# Activer/désactiver l'enrichissement automatique
enabled = true

# === Worker Settings ===
# Intervalle de polling (en secondes)
# Le worker vérifie toutes les X secondes s'il y a des transcriptions à enrichir
poll_interval_seconds = 15

# Nombre de transcriptions à traiter par batch
batch_size = 3

# Nombre de tentatives en cas d'erreur
max_retries = 3

# Délai entre les tentatives (en secondes)
retry_delay_seconds = 60

# === Model Settings ===
# Chemin vers le modèle LLM (format GGUF)
# Téléchargez-le avec: make download-model
model_path = models/mistral-7b-instruct-v0.3.Q4_K_M.gguf

# Type de modèle (pour les templates de prompts)
# Options: mistral, llama, generic
model_type = mistral

# Taille du contexte (nombre de tokens)
# Plus grand = peut traiter de plus longs textes, mais plus lent
# Recommandé: 2048-4096
n_ctx = 4096

# Nombre de threads CPU pour l'inférence
# Recommandé: nombre de cœurs CPU - 2
n_threads = 6

# Taille du batch pour le traitement
# Plus grand = plus rapide mais plus de RAM
n_batch = 512

# === Generation Settings ===
# Temperature (0.0-1.0)
# 0.0 = déterministe, 1.0 = créatif
# Recommandé: 0.3 pour de la génération factuelle
temperature = 0.3

# Top P (0.0-1.0)
# Sampling nucleus - garde les tokens les plus probables
top_p = 0.9

# Top K
# Nombre de tokens considérés pour le sampling
top_k = 40

# Repeat penalty (1.0+)
# Pénalise la répétition de tokens
repeat_penalty = 1.1

# Nombre maximum de tokens à générer
# Plus = résumés plus longs mais plus lent
max_tokens = 500

# === Processing Limits ===
# Longueur maximale du texte de transcription (en caractères)
# Les textes plus longs seront tronqués
max_transcription_chars = 15000

# Longueur minimale pour enrichir une transcription
# En dessous, l'enrichissement est ignoré
min_transcription_chars = 100

# === Features ===
# Activer/désactiver les fonctionnalités d'enrichissement
generate_title = true
generate_summary = true
generate_bullets = true
generate_sentiment = true
generate_topics = false

# === Language ===
# Langue des prompts et de la génération
# Options: fr, en
prompt_language = fr
output_language = fr


# =====================================================================
# PRESETS D'ENRICHISSEMENT
# =====================================================================
#
# 🚀 RAPIDE (pour tests ou gros volumes)
# ---------------------------------------------------------------------
# model_path = models/mistral-7b-instruct-v0.3.Q4_K_M.gguf
# n_ctx = 2048
# n_threads = 8
# temperature = 0.2
# max_tokens = 300
# batch_size = 5
#
# ⚖️ ÉQUILIBRÉ (recommandé pour production)
# ---------------------------------------------------------------------
# model_path = models/mistral-7b-instruct-v0.3.Q4_K_M.gguf
# n_ctx = 4096
# n_threads = 6
# temperature = 0.3
# max_tokens = 500
# batch_size = 3
#
# 🎯 QUALITÉ MAXIMALE (enrichissement de qualité)
# ---------------------------------------------------------------------
# model_path = models/mistral-7b-instruct-v0.3.Q5_K_M.gguf (modèle plus gros)
# n_ctx = 8192
# n_threads = 4
# temperature = 0.4
# max_tokens = 700
# batch_size = 1
# generate_topics = true
#
# =====================================================================
EOF

echo ""
echo "✅ Section [ENRICHMENT] ajoutée avec succès!"
echo ""
echo "📋 Prochaines étapes:"
echo "  1. Télécharger le modèle LLM:"
echo "     make download-model"
echo ""
echo "  2. Créer les tables de la base de données:"
echo "     make db-migrate"
echo ""
echo "  3. Lancer le worker d'enrichissement:"
echo "     make run-enrichment"
echo ""
echo "💡 Pour personnaliser la configuration:"
echo "   nano $CONFIG_FILE"
echo ""