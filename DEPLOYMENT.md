# Vocalyx API

Vocalyx transforme automatiquement les enregistrements de call centers en **transcriptions enrichies et exploitables**.  
Grâce à l’intelligence artificielle et aux modèles LLM, elle génère des insights, résume les conversations et alimente des agents virtuels pour optimiser la relation client.

## Fonctionnalités

- Transcription asynchrone d'audio (`wav`, `mp3`, `m4a`, `flac`, `ogg`, `webm`) avec **faster-whisper**
- Dashboard HTML interactif pour visualiser les dernières transcriptions
- Modal détaillé avec :
  - Informations générales
  - Timeline des segments
  - Texte complet
- API REST avec endpoints pour récupérer ou créer des transcriptions
- Support multi-langue avec détection automatique de la langue

## Installation

### Prérequis

- Python 3.11+
- ffmpeg installé et accessible dans le PATH
- SQLite (inclus par défaut avec Python)

### Installation via pip

```bash
git clone <repo_url>
cd vocalyx
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### Structure des dossiers
```
vocalyx/
│
├─ app.py                  # FastAPI app
├─ templates/              # Contient dashboard.html et transcription_detail.html
├─ tmp_uploads/            # Dossier temporaire pour les fichiers uploadés
├─ transcriptions.db       # Base SQLite créée automatiquement
├─ README.md
└─ requirements.txt
```

### Lancement de l’application
```
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

- Le dashboard est disponible sur : http://localhost:8000/dashboard
- La documentation Swagger sur : http://localhost:8000/docs

### API Endpoints
| Endpoint                  | Méthode | Description                                             |
| ------------------------- | ------- | ------------------------------------------------------- |
| `/transcribe`             | POST    | Upload un fichier audio et démarre la transcription     |
| `/transcribe/recent`      | GET     | Liste les dernières transcriptions (limit paramétrable) |
| `/transcribe/{id}`        | GET     | Récupère une transcription spécifique                   |
| `/dashboard`              | GET     | Dashboard HTML des transcriptions                       |
| `/transcribe/detail/{id}` | GET     | Page détail transcription en HTML                       |

### Notes
- Tous les fichiers audio sont convertis automatiquement en WAV 16 kHz mono si nécessaire.
- Les transcriptions sont traitées asynchrones pour ne pas bloquer l’API.
- Les segments et le texte complet sont stockés dans SQLite pour un accès rapide.