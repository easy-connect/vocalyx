# 🎨 Module d'Enrichissement Vocalyx

Le module d'enrichissement génère automatiquement des insights exploitables à partir des transcriptions audio via un LLM local (Large Language Model).

## ✨ Fonctionnalités

Pour chaque transcription, le module génère :

- 📌 **Titre** : Un titre court et pertinent (10 mots max)
- 📝 **Résumé** : Synthèse en 2-3 phrases
- 🔹 **Points clés** : 3-5 points principaux extraits
- 😊 **Sentiment** : Analyse du ton (positif/négatif/neutre/mixte)
- 🏷️ **Topics** : Thèmes principaux (optionnel)

## 🚀 Installation

### 1. Installer les dépendances

```bash
# Via make (recommandé)
make install-enrichment

# Ou manuellement
pip install -r requirements-enrichment.txt
```

### 2. Télécharger le modèle LLM

Le module utilise [Mistral 7B Instruct](https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.3-GGUF) par défaut (~4GB).

```bash
# Via make (recommandé)
make download-model

# Ou manuellement
mkdir -p models
cd models
wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.3-GGUF/resolve/main/mistral-7b-instruct-v0.3.Q4_K_M.gguf
```

### 3. Configurer

Ajouter la section `[ENRICHMENT]` dans `config.ini` :

```bash
# Automatiquement
bash scripts/add_enrichment_config.sh

# Ou manuellement (voir config.ini.exemple)
```

### 4. Créer les tables de la base de données

```bash
make db-migrate

# Ou manuellement
python3 -c "from enrichment.models import create_tables; create_tables()"
```

## 🎯 Utilisation

### Lancer le worker

```bash
# Via make (recommandé)
make run-enrichment

# Ou directement
python3 run_enrichment.py
```

Le worker va :
1. ✅ Charger le modèle LLM (30-60s au démarrage)
2. 🔄 Interroger la DB toutes les 15s pour trouver les nouvelles transcriptions
3. 🎨 Générer les enrichissements (30-60s par transcription)
4. 💾 Sauvegarder les résultats dans la table `enrichments`

### Lancer API + Worker ensemble

```bash
make run-all
```

### Mode test

```bash
# Test complet du module
python3 test_enrichment_module.py

# Test rapide avec une transcription
python3 -c "from enrichment.worker import test_enrichment; test_enrichment()"
```

## ⚙️ Configuration

### Configuration de base (`config.ini`)

```ini
[ENRICHMENT]
# Activer/désactiver
enabled = true

# Worker
poll_interval_seconds = 15  # Fréquence de vérification
batch_size = 3              # Nombre de transcriptions par batch

# Modèle LLM
model_path = models/mistral-7b-instruct-v0.3.Q4_K_M.gguf
n_ctx = 4096               # Taille du contexte
n_threads = 6              # Threads CPU

# Génération
temperature = 0.3          # Créativité (0.0 = déterministe)
max_tokens = 500           # Longueur max de la génération

# Fonctionnalités
generate_title = true
generate_summary = true
generate_bullets = true
generate_sentiment = true
generate_topics = false    # Plus lent
```

### Presets recommandés

#### 🚀 Vitesse (tests, gros volumes)
```ini
n_ctx = 2048
n_threads = 8
temperature = 0.2
max_tokens = 300
batch_size = 5
```

#### ⚖️ Équilibré (production standard)
```ini
n_ctx = 4096
n_threads = 6
temperature = 0.3
max_tokens = 500
batch_size = 3
```

#### 🎯 Qualité maximale
```ini
model_path = models/mistral-7b-instruct-v0.3.Q5_K_M.gguf  # Modèle plus précis
n_ctx = 8192
temperature = 0.4
max_tokens = 700
batch_size = 1
generate_topics = true
```

## 📊 Architecture

```
enrichment/
├── __init__.py          # Exports du module
├── config.py            # Configuration
├── models.py            # Modèles SQLAlchemy (table enrichments)
├── llm_engine.py        # Wrapper llama-cpp-python
├── prompts.py           # Templates de prompts
├── processors.py        # Logique d'enrichissement
├── utils.py             # Utilitaires (parsing, validation, etc.)
├── worker.py            # Worker principal
└── README.md            # Ce fichier
```

### Flux de données

```
┌─────────────────┐
│  Transcription  │  (status=done, enrichment_requested=1)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Worker      │  (polling toutes les 15s)
│  - Récupère     │
│  - Traite       │
│  - Sauvegarde   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   LLM Engine    │  (llama-cpp-python)
│  - Charge model │
│  - Génère texte │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Enrichment    │  (titre, résumé, bullets, sentiment)
└─────────────────┘
```

## 🗄️ Schéma de la base de données

### Table `enrichments`

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | Integer | Clé primaire |
| `transcription_id` | String | FK vers transcriptions.id |
| `status` | String | pending, processing, done, error |
| `title` | Text | Titre généré |
| `summary` | Text | Résumé |
| `bullets` | JSON | Liste de points clés |
| `sentiment` | String | positif, negatif, neutre, mixte |
| `sentiment_confidence` | Float | Confiance 0-1 |
| `topics` | JSON | Liste de topics (optionnel) |
| `model_used` | String | Nom du modèle |
| `generation_time` | Float | Temps de génération (s) |
| `tokens_generated` | Integer | Nombre de tokens générés |
| `retry_count` | Integer | Nombre de tentatives |
| `last_error` | Text | Dernier message d'erreur |
| `created_at` | DateTime | Date de création |
| `started_at` | DateTime | Début du traitement |
| `finished_at` | DateTime | Fin du traitement |

## 📡 API

Pour récupérer les enrichissements via l'API :

```bash
# Obtenir une transcription + son enrichissement
GET /api/transcribe/{transcription_id}

# Réponse
{
  "id": "...",
  "text": "...",
  "enrichment": {
    "title": "Réclamation client - Produit défectueux",
    "summary": "Le client appelle pour signaler un problème...",
    "bullets": [
      "Produit défectueux reçu",
      "Demande de remboursement",
      "Urgence exprimée"
    ],
    "sentiment": "negatif",
    "sentiment_confidence": 0.85
  }
}
```

## 🧪 Tests

### Test complet du module

```bash
python3 test_enrichment_module.py
```

Tests effectués :
1. ✅ Configuration
2. ✅ Modèles de base de données
3. ✅ Utilitaires
4. ✅ Templates de prompts
5. ✅ Moteur LLM
6. ✅ Processeur
7. ✅ Worker

### Test rapide

```bash
# Test avec une transcription fictive
python3 -c "from enrichment.worker import test_enrichment; test_enrichment()"
```

### Tests unitaires des utilitaires

```bash
python3 enrichment/utils.py
```

## 🔧 Dépannage

### Le modèle ne se charge pas

**Erreur** : `FileNotFoundError: models/mistral-7b-instruct-v0.3.Q4_K_M.gguf`

**Solution** :
```bash
make download-model
# Ou vérifier le chemin dans config.ini
```

### Génération très lente

**Cause** : Trop peu de threads ou modèle trop gros

**Solution** :
```ini
[ENRICHMENT]
n_threads = 8  # Augmenter
# Ou utiliser un modèle plus petit (Q4 au lieu de Q5)
```

### Erreur "Out of memory"

**Cause** : RAM insuffisante

**Solution** :
```ini
[ENRICHMENT]
n_ctx = 2048      # Réduire le contexte
batch_size = 1    # Traiter une à la fois
# Ou utiliser un modèle plus petit (tiny au lieu de small)
```

### Enrichissements de mauvaise qualité

**Solutions** :
```ini
[ENRICHMENT]
temperature = 0.2           # Plus déterministe
max_tokens = 700            # Plus de place pour générer
beam_size = 7               # Meilleur décodage (si supporté)
# Ou utiliser un modèle plus gros (Q5 au lieu de Q4)
```

### Worker ne trouve pas de transcriptions

**Vérifications** :
```sql
-- Vérifier qu'il y a des transcriptions à enrichir
SELECT COUNT(*) FROM transcriptions 
WHERE status='done' AND enrichment_requested=1;

-- Vérifier les enrichissements existants
SELECT COUNT(*) FROM enrichments;
```

**Solution** :
```python
# Forcer l'enrichissement d'une transcription
from database import SessionLocal, Transcription
db = SessionLocal()
trans = db.query(Transcription).filter(Transcription.status=='done').first()
trans.enrichment_requested = 1
db.commit()
```

## 📈 Performance

### Temps de traitement attendus

| Modèle | CPU | Temps/transcription | Vitesse |
|--------|-----|---------------------|---------|
| **Mistral 7B Q4** | i7 8 cores | 30-40s | ~15 tok/s |
| **Mistral 7B Q5** | i7 8 cores | 40-60s | ~10 tok/s |
| **Llama 2 7B Q4** | i7 8 cores | 40-50s | ~12 tok/s |

### Optimisations

- ✅ **Augmenter `n_threads`** : Utiliser plus de cœurs CPU
- ✅ **Réduire `n_ctx`** : Moins de contexte = plus rapide
- ✅ **Utiliser Q4 au lieu de Q5** : Modèle plus léger
- ✅ **Augmenter `batch_size`** : Traiter plusieurs en parallèle
- ✅ **Désactiver `generate_topics`** : Gain de ~10s

## 🌍 Langues supportées

### Modèles recommandés par langue

| Langue | Modèle recommandé |
|--------|-------------------|
| 🇫🇷 Français | Mistral 7B Instruct v0.3 |
| 🇬🇧 Anglais | Mistral 7B Instruct v0.3 |
| 🇪🇸 Espagnol | Mistral 7B Instruct v0.3 |
| 🇩🇪 Allemand | Mistral 7B Instruct v0.3 |

Pour changer la langue :
```ini
[ENRICHMENT]
prompt_language = en
output_language = en
```

## 🔐 Sécurité & Confidentialité

- ✅ **Modèle local** : Aucune donnée envoyée à des API externes
- ✅ **Offline** : Fonctionne sans connexion internet (après téléchargement du modèle)
- ✅ **RGPD compatible** : Toutes les données restent sur votre serveur

## 📚 Ressources

- [llama-cpp-python](https://github.com/abetlen/llama-cpp-python) - Wrapper Python utilisé
- [Mistral AI](https://mistral.ai/) - Créateur du modèle Mistral
- [TheBloke sur HuggingFace](https://huggingface.co/TheBloke) - Modèles quantizés GGUF

## 🆘 Support

- **Documentation** : [docs/README.md](../docs/README.md)
- **Issues** : GitHub Issues
- **Email** : guilhem.l.richard@gmail.com

---

**Version 1.0.0** | Module d'enrichissement Vocalyx