# 🎙️ Vocalyx - API de Transcription Speech-to-Text

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)
[![Whisper](https://img.shields.io/badge/Whisper-faster--whisper-orange.svg)](https://github.com/guillaumekln/faster-whisper)

Vocalyx transforme automatiquement les enregistrements de call centers en transcriptions enrichies et exploitables grâce à l'intelligence artificielle.

## ✨ Fonctionnalités

- 🚀 **Transcription asynchrone** haute performance
- 🎯 **VAD (Voice Activity Detection)** pour ignorer les silences
- 📊 **Dashboard web** interactif avec suivi en temps réel
- ⚙️ **Configuration flexible** via fichier `.ini`
- 🔄 **Traitement parallèle** pour fichiers longs
- 📝 **API REST** complète avec Swagger
- 🛡️ **Rate limiting** et validation des fichiers
- 🌍 **Multi-langues** (français optimisé)
- 📈 **Métriques de performance** détaillées

## 🚀 Démarrage rapide

### Installation

```bash
# Cloner le projet
git clone <votre-repo>
cd vocalyx

# Créer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Installer les dépendances
pip install -r requirements.txt

# Installer ffmpeg (requis)
# Ubuntu/Debian:
sudo apt install ffmpeg libsndfile1

# macOS:
brew install ffmpeg libsndfile

# Windows: télécharger depuis https://ffmpeg.org/
```

### Lancement

```bash
# Lancer l'application
python app.py

# L'API est disponible sur http://localhost:8000
# Dashboard: http://localhost:8000/dashboard
# Documentation: http://localhost:8000/docs
```

### Premier test

```bash
# Méthode 1: Script de test automatique
chmod +x test_vocalyx.sh
./test_vocalyx.sh mon_fichier.wav

# Méthode 2: cURL manuel
curl -X POST "http://localhost:8000/transcribe" \
  -F "file=@mon_audio.wav" \
  -F "use_vad=true"

# Récupérer le résultat
curl "http://localhost:8000/transcribe/{transcription_id}"
```

## 📋 Configuration

Vocalyx utilise un fichier `config.ini` pour toute la configuration. Le fichier est créé automatiquement avec des valeurs par défaut au premier lancement.

### Presets disponibles

```bash
# Installation de l'outil de configuration
python config_manager.py

# Afficher la configuration actuelle
python config_manager.py show

# Appliquer un preset
python config_manager.py preset balanced  # Recommandé
python config_manager.py preset speed     # Vitesse max
python config_manager.py preset accuracy  # Précision max

# Modifier une valeur spécifique
python config_manager.py set WHISPER model medium

# Valider la configuration
python config_manager.py validate
```

### Structure du fichier config.ini

```ini
[WHISPER]
model = small              # tiny, base, small, medium, large-v3
device = cpu               # cpu, cuda (GPU)
compute_type = int8        # int8, float16, float32
cpu_threads = 10           # Nombre de threads CPU
language = fr              # Langue forcée (fr, en, es, etc.)

[PERFORMANCE]
max_workers = 4            # Workers parallèles
segment_length_ms = 60000  # Taille des segments (ms)
vad_enabled = true         # Activer VAD
beam_size = 5              # Qualité du décodage (1-10)
temperature = 0.0          # Déterminisme (0.0-1.0)

[LIMITS]
max_file_size_mb = 100              # Taille max des fichiers
rate_limit_per_minute = 10          # Limite de requêtes
allowed_extensions = wav,mp3,m4a,flac,ogg,webm

[PATHS]
upload_dir = ./tmp_uploads
database_path = sqlite:///./transcriptions.db
templates_dir = templates

[VAD]
min_silence_len = 500        # Silence minimum (ms)
silence_thresh = -40         # Seuil de silence (dB)
vad_threshold = 0.5          # Sensibilité VAD (0.0-1.0)
```

## 📊 Comparatif des modèles

| Modèle | Taille | RAM | Vitesse | Qualité | Usage recommandé |
|--------|--------|-----|---------|---------|------------------|
| **tiny** | ~75MB | 1GB | 30-50x ⚡⚡⚡ | ⭐⭐ | Tests, prototypes |
| **base** | ~145MB | 1GB | 15-30x ⚡⚡ | ⭐⭐⭐ | Appels courts |
| **small** | ~460MB | 2GB | 5-10x ⚡ | ⭐⭐⭐⭐ | **Production standard** ✅ |
| **medium** | ~1.5GB | 5GB | 2-4x | ⭐⭐⭐⭐⭐ | Haute qualité |
| **large-v3** | ~3GB | 10GB | 1-2x | ⭐⭐⭐⭐⭐ | Qualité maximale |

*Vitesse = X fois le temps réel (ex: 10x = 1min d'audio en 6s)*

## 🔧 API Endpoints

### POST /transcribe
Créer une transcription

```bash
curl -X POST "http://localhost:8000/transcribe" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@audio.wav" \
  -F "translate=false" \
  -F "use_vad=true"
```

**Réponse:**
```json
{
  "transcription_id": "uuid-here",
  "status": "pending"
}
```

### GET /transcribe/{id}
Récupérer une transcription

```bash
curl "http://localhost:8000/transcribe/{transcription_id}"
```

**Réponse:**
```json
{
  "id": "uuid",
  "status": "done",
  "language": "fr",
  "duration": 120.5,
  "processing_time": 12.3,
  "text": "Transcription complète...",
  "segments": [
    {"start": 0.0, "end": 3.5, "text": "Bonjour"},
    {"start": 3.5, "end": 5.2, "text": "comment allez-vous ?"}
  ],
  "segments_count": 42,
  "vad_enabled": true
}
```

### GET /transcribe/recent
Lister les transcriptions récentes

```bash
curl "http://localhost:8000/transcribe/recent?limit=10"
```

### DELETE /transcribe/{id}
Supprimer une transcription

```bash
curl -X DELETE "http://localhost:8000/transcribe/{transcription_id}"
```

### GET /config
Voir la configuration actuelle

```bash
curl "http://localhost:8000/config"
```

### POST /config/reload
Recharger la configuration sans redémarrage

```bash
curl -X POST "http://localhost:8000/config/reload"
```

### GET /health
Vérifier l'état de l'API

```bash
curl "http://localhost:8000/health"
```

## 🎯 Optimisation des performances

### Règle générale
```
Vitesse = (Puissance CPU × Taille modèle⁻¹ × VAD) / Qualité audio
```

### Conseils d'optimisation

#### Pour plus de VITESSE 🚀
```ini
[WHISPER]
model = tiny
[PERFORMANCE]
max_workers = 8
beam_size = 3
vad_enabled = true
```

#### Pour plus de PRÉCISION 🎯
```ini
[WHISPER]
model = medium
[PERFORMANCE]
max_workers = 2
beam_size = 10
segment_length_ms = 90000
```

#### Pour PRODUCTION équilibrée ⚖️
```ini
[WHISPER]
model = small
[PERFORMANCE]
max_workers = 4
beam_size = 5
vad_enabled = true
```

### VAD (Voice Activity Detection)

Le VAD améliore considérablement les performances :

- ✅ **+40% de vitesse** sur des audios avec silences
- ✅ **Segments plus pertinents** (ignore les blancs)
- ✅ **Meilleure précision** (moins de bruit transcrit)

**Quand désactiver le VAD:**
- Musique ou chants
- Audio continu sans pauses
- ASMR ou sons d'ambiance

### Tuning du VAD

```ini
[VAD]
# Audio avec beaucoup de bruit de fond
silence_thresh = -35  # Moins sensible

# Audio très propre / studio
silence_thresh = -45  # Plus sensible

# Parole rapide / coupures de mots
min_silence_len = 300  # Pauses plus courtes

# Parole lente / longues pauses
min_silence_len = 700  # Pauses plus longues
```

## 📈 Monitoring et métriques

### Dashboard web
Accédez à `http://localhost:8000/dashboard` pour :
- 📊 Vue temps réel des transcriptions
- 🔍 Filtres par statut
- 📝 Détails des segments
- 📥 Upload direct depuis l'interface
- 🗑️ Suppression de transcriptions

### Métriques clés
Chaque transcription fournit :
- **Duration**: Durée réelle de l'audio
- **Processing time**: Temps de traitement
- **Speed ratio**: X fois le temps réel
- **Segments count**: Nombre de segments détectés
- **VAD status**: VAD activé ou non

### Logs
```bash
# Logs en temps réel
tail -f logs/vocalyx.log

# Avec journalctl (si systemd)
sudo journalctl -u vocalyx -f
```

## 🐳 Docker

```dockerfile
# Dockerfile inclus dans le projet
docker build -t vocalyx:latest .

# Lancer avec volume pour config
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/config.ini:/app/config.ini \
  -v $(pwd)/tmp_uploads:/app/tmp_uploads \
  --name vocalyx \
  vocalyx:latest
```

## 🔒 Sécurité

- ✅ Rate limiting configuré
- ✅ Validation des extensions de fichiers
- ✅ Limite de taille des uploads
- ✅ Sanitization des noms de fichiers
- ✅ Cleanup automatique des fichiers temporaires

**Pour production:**
- Utilisez HTTPS (Nginx + Let's Encrypt)
- Configurez un firewall
- Activez les logs d'audit
- Limitez l'accès API par token/IP

## 📝 Structure du projet

```
vocalyx/
├── app.py                  # Application principale
├── config.ini              # Configuration (auto-créé)
├── config_manager.py       # Outil de gestion config
├── requirements.txt        # Dépendances Python
├── test_vocalyx.sh         # Script de test
├── DEPLOYMENT.md           # Guide de déploiement détaillé
├── README.md              # Ce fichier
├── templates/
│   └── dashboard.html      # Interface web
├── tmp_uploads/            # Uploads temporaires (auto)
├── logs/                   # Logs (auto)
└── transcriptions.db       # Base SQLite (auto)
```

## 🛠️ Développement

### Tests
```bash
# Test automatique complet
./test_vocalyx.sh

# Test avec un fichier spécifique
./test_vocalyx.sh mon_audio.mp3

# Tests unitaires (TODO)
pytest tests/
```

### Contribution
1. Fork le projet
2. Créer une branche (`git checkout -b feature/amazing`)
3. Commit (`git commit -m 'Add amazing feature'`)
4. Push (`git push origin feature/amazing`)
5. Ouvrir une Pull Request

## 📞 Support

- 📧 Email: guilhem.l.richard@gmail.com
- 📚 Documentation API: http://localhost:8000/docs
- 🐛 Issues: [GitHub Issues](votre-repo/issues)

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 🙏 Remerciements

- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - Implémentation performante de Whisper
- [OpenAI Whisper](https://github.com/openai/whisper) - Modèle de base
- [FastAPI](https://fastapi.tiangolo.com/) - Framework web moderne

---

**Vocalyx v1.3.0** - La voix de vos clients, intelligemment exploitée 🎙️