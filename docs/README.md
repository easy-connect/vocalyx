# 🎙️ Vocalyx - Plateforme Complète de Transcription et d'Analyse Intelligente

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)
[![Whisper](https://img.shields.io/badge/Whisper-faster--whisper-orange.svg)](https://github.com/guillaumekln/faster-whisper)
[![LLM](https://img.shields.io/badge/LLM-Mistral_7B-purple.svg)](https://mistral.ai/)

Vocalyx transforme automatiquement les enregistrements audio (call centers, interviews, réunions) en **transcriptions enrichies et exploitables** grâce à l'intelligence artificielle.

## ✨ Fonctionnalités

### 🎯 Module de Transcription
- 🚀 **Transcription asynchrone** haute performance (jusqu'à 50x temps réel)
- 🎯 **VAD (Voice Activity Detection)** pour ignorer les silences
- 🔄 **Traitement parallèle** optimisé pour fichiers longs
- 🌍 **Multi-langues** avec détection automatique (français optimisé)
- 📊 **Métriques de performance** détaillées en temps réel

### 🎨 Module d'Enrichissement (LLM)
- 📌 **Génération de titre** automatique (10 mots max)
- 📝 **Résumé intelligent** en 2-3 phrases
- 🔹 **Points clés** extraits (3-5 éléments)
- 😊 **Analyse de sentiment** (positif/négatif/neutre/mixte)
- 🏷️ **Topics** et thèmes principaux (optionnel)

### 🖥️ Interface & API
- 📊 **Dashboard web** interactif avec suivi temps réel
- 📝 **API REST** complète avec documentation Swagger
- ⚙️ **Configuration flexible** via fichier `.ini`
- 🛡️ **Rate limiting** et validation sécurisée
- 🔐 **100% local** : aucune donnée envoyée à l'extérieur

## 🏗️ Architecture

```
┌─────────────────┐
│   Audio Input   │  (WAV, MP3, M4A, FLAC, OGG, WEBM)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Transcription  │  (faster-whisper + VAD)
│   Module        │  → Texte + Segments + Timestamps
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Enrichissement │  (Mistral 7B LLM local)
│   Module        │  → Titre + Résumé + Insights
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  API REST +     │
│  Dashboard      │  → Résultats exploitables
└─────────────────┘
```

## 🚀 Installation Rapide

### Prérequis
- Python 3.8+
- FFmpeg
- 8GB RAM minimum (16GB recommandé)
- CPU multi-cœurs (4+ cœurs)

### Installation en 3 commandes

```bash
# 1. Installation de base (transcription)
make install

# 2. Installation du module d'enrichissement
make install-enrichment

# 3. Téléchargement du modèle LLM (4GB)
make download-model
```

### Configuration

```bash
# Appliquer la configuration recommandée
make config-balanced

# Ajouter la section enrichissement
bash scripts/add_enrichment_config.sh

# Créer les tables de la base de données
make db-migrate
```

### Lancement

```bash
# Lancer l'API + Worker d'enrichissement
make run-all

# Ou séparément :
make run              # API de transcription uniquement
make run-enrichment   # Worker d'enrichissement uniquement
```

**URLs disponibles :**
- Dashboard : http://localhost:8000/dashboard
- API Docs : http://localhost:8000/docs
- Health : http://localhost:8000/health

## 📊 Exemple Complet

### 1. Upload d'un fichier audio

```bash
curl -X POST "http://localhost:8000/api/transcribe" \
  -F "file=@appel_client.wav" \
  -F "use_vad=true"
```

**Réponse :**
```json
{
  "transcription_id": "abc123-def456",
  "status": "pending"
}
```

### 2. Récupération du résultat

```bash
curl "http://localhost:8000/api/transcribe/abc123-def456"
```

**Réponse enrichie :**
```json
{
  "id": "abc123-def456",
  "status": "done",
  "language": "fr",
  "duration": 120.5,
  "processing_time": 15.3,
  "text": "Bonjour, je vous appelle concernant...",
  "segments": [
    {"start": 0.0, "end": 3.5, "text": "Bonjour"},
    {"start": 3.5, "end": 8.2, "text": "je vous appelle concernant..."}
  ],
  "segments_count": 42,
  "vad_enabled": true,
  "enrichment": {
    "title": "Réclamation client - Produit défectueux",
    "summary": "Le client appelle pour signaler un problème avec sa commande. Il n'a pas reçu le produit commandé il y a une semaine et demande un remboursement urgent.",
    "bullets": [
      "Commande non reçue après une semaine",
      "Demande de remboursement",
      "Urgence exprimée par le client"
    ],
    "sentiment": "negatif",
    "sentiment_confidence": 0.85
  }
}
```

## ⚡ Performance

### Transcription (modèle `small`)

| Durée audio | Temps traitement | Vitesse | VAD |
|-------------|------------------|---------|-----|
| 30 secondes | 3-5s | 6-10x ⚡⚡⚡ | ✅ |
| 5 minutes | 30-60s | 5-10x ⚡⚡ | ✅ |
| 30 minutes | 3-6 min | 5-10x ⚡⚡ | ✅ |
| 2 heures | 12-20 min | 6-10x ⚡⚡ | ✅ |

### Enrichissement (Mistral 7B Q4)

| CPU | Temps/transcription | Tokens/sec |
|-----|---------------------|------------|
| i7 8 cores | 30-40s | ~15 tok/s |
| i9 12 cores | 20-30s | ~20 tok/s |
| Ryzen 9 16 cores | 15-25s | ~25 tok/s |

**Temps total** : Transcription (10s) + Enrichissement (30s) = **~40s pour 5 min d'audio**

## 📋 Comparatif des Modèles

### Transcription (Whisper)

| Modèle | RAM | Vitesse | Qualité | Usage |
|--------|-----|---------|---------|-------|
| **tiny** | 1GB | 30-50x ⚡⚡⚡ | ⭐⭐ | Tests, prototypes |
| **base** | 1GB | 15-30x ⚡⚡ | ⭐⭐⭐ | Appels courts |
| **small** | 2GB | 5-10x ⚡ | ⭐⭐⭐⭐ | **Production** ✅ |
| **medium** | 5GB | 2-4x | ⭐⭐⭐⭐⭐ | Haute qualité |
| **large-v3** | 10GB | 1-2x | ⭐⭐⭐⭐⭐ | Qualité maximale |

### Enrichissement (LLM)

| Modèle | Taille | RAM | Vitesse | Qualité |
|--------|--------|-----|---------|---------|
| **Mistral 7B Q4** | 4GB | 6GB | 15 tok/s | ⭐⭐⭐⭐ ✅ |
| **Mistral 7B Q5** | 5GB | 8GB | 10 tok/s | ⭐⭐⭐⭐⭐ |
| **Llama 2 7B Q4** | 4GB | 6GB | 12 tok/s | ⭐⭐⭐⭐ |

## 🎯 Cas d'Usage

### 1. Call Center - Support Client
```ini
[WHISPER]
model = small
[PERFORMANCE]
vad_enabled = true
max_workers = 4
[ENRICHMENT]
enabled = true
generate_sentiment = true
```

**Résultat** : Transcription + analyse de sentiment pour chaque appel

### 2. Interviews / Podcasts
```ini
[WHISPER]
model = medium
[PERFORMANCE]
segment_length_ms = 90000
[ENRICHMENT]
generate_title = true
generate_summary = true
generate_bullets = true
```

**Résultat** : Transcription précise + résumé structuré

### 3. Réunions d'Entreprise
```ini
[WHISPER]
model = small
language = fr
[ENRICHMENT]
generate_bullets = true
generate_topics = true
```

**Résultat** : Compte-rendu automatique avec points clés

## ⚙️ Configuration

### Fichier `config.ini`

```ini
# === TRANSCRIPTION ===
[WHISPER]
model = small
device = cpu
language = fr

[PERFORMANCE]
max_workers = 4
vad_enabled = true
beam_size = 5

# === ENRICHISSEMENT ===
[ENRICHMENT]
enabled = true
model_path = models/mistral-7b-instruct-v0.3.Q4_K_M.gguf
n_threads = 6
temperature = 0.3

generate_title = true
generate_summary = true
generate_bullets = true
generate_sentiment = true
```

### Presets Disponibles

```bash
# Vitesse maximale
make config-speed

# Équilibre production (recommandé)
make config-balanced

# Qualité maximale
make config-accuracy
```

## 🗄️ Base de Données

### Tables principales

**`transcriptions`**
- Transcriptions audio (texte, segments, métriques)

**`enrichments`**
- Enrichissements LLM (titre, résumé, sentiment)

### Gestion

```bash
# Statistiques
make db-stats

# Nettoyage (> 30 jours)
make clean-db

# Backup
make backup-db
```

## 🧪 Tests

```bash
# Test complet
make test

# Test transcription
make test-transcribe FILE=audio.wav

# Test enrichissement
python3 test_enrichment_module.py

# Vérifier l'installation
make check
```

## 🐳 Docker

```bash
# Construction
make docker-build

# Lancement
make docker-run

# Logs
make docker-logs
```

## 📈 Monitoring & Logs

### Logs

```bash
# Logs temps réel
tail -f logs/vocalyx.log
tail -f logs/enrichment.log

# Logs par niveau
grep "\[ERROR\]" logs/vocalyx.log
```

### Dashboard

Le dashboard web (`http://localhost:8000/dashboard`) affiche :
- 📊 Liste des transcriptions récentes
- 🔍 Filtres par statut
- 📝 Détails complets (segments, enrichissement)
- 📥 Upload direct depuis l'interface

## 🔒 Sécurité & Confidentialité

- ✅ **100% local** : Aucune donnée n'est envoyée à des services externes
- ✅ **Offline** : Fonctionne sans connexion internet (après installation)
- ✅ **RGPD compatible** : Toutes les données restent sur votre infrastructure
- ✅ **Rate limiting** : Protection contre les abus
- ✅ **Validation** : Contrôle strict des entrées

## 📚 Documentation

- [Guide de démarrage rapide](docs/QUICKSTART.md)
- [Guide de déploiement](docs/DEPLOYMENT.md)
- [Module d'enrichissement](enrichment/README.md)
- [Guide des logs](docs/LOGS.md)

## 🛠️ Commandes Utiles

```bash
# Aide complète
make help

# Infos système
make info

# URLs disponibles
make urls

# Configuration
make config               # Afficher
make config-validate      # Valider
make config-reload        # Recharger sans redémarrer

# Base de données
make db-stats            # Statistiques
make db-migrate          # Créer tables enrichment
make clean-db            # Nettoyer (>30j)

# Logs
make logs                # Afficher
make clean-logs          # Supprimer
```

## 🔧 Dépannage

### Transcription lente
```bash
# Solution 1 : Modèle plus petit
make config-speed

# Solution 2 : Plus de workers
python config_manager.py set PERFORMANCE max_workers 8
```

### Enrichissement lent
```ini
[ENRICHMENT]
n_threads = 8  # Augmenter threads
n_ctx = 2048   # Réduire contexte
```

### Erreur "Out of memory"
```ini
[WHISPER]
model = tiny   # Modèle plus léger

[ENRICHMENT]
batch_size = 1
n_ctx = 2048
```

## 📞 Support

- 📧 Email : guilhem.l.richard@gmail.com
- 📚 Documentation : [docs/](docs/)
- 🐛 Issues : GitHub Issues

## 📄 Licence

MIT License - Voir `LICENSE` pour plus de détails

## 🙏 Remerciements

- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - Transcription performante
- [OpenAI Whisper](https://github.com/openai/whisper) - Modèle de base
- [Mistral AI](https://mistral.ai/) - Modèle LLM
- [llama-cpp-python](https://github.com/abetlen/llama-cpp-python) - Inférence locale
- [FastAPI](https://fastapi.tiangolo.com/) - Framework web

---

**Vocalyx v1.4.0** - Transcription + Enrichissement Intelligent 🎙️✨

*La voix de vos clients, intelligemment exploitée*