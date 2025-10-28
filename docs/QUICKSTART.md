# 🚀 Vocalyx - Guide de Démarrage Rapide

## Installation en 5 minutes ⏱️

### 1. Prérequis
```bash
# Vérifier Python
python3 --version  # Doit être >= 3.8

# Installer ffmpeg
sudo apt install ffmpeg libsndfile1  # Ubuntu/Debian
brew install ffmpeg libsndfile       # macOS
```

### 2. Installation Complète

```bash
# Méthode 1: Avec Make (recommandé)
make install-all          # Installe transcription + enrichissement
make download-model       # Télécharge le modèle LLM (4GB)
make config-balanced      # Applique la config recommandée
bash scripts/add_enrichment_config.sh  # Ajoute config enrichissement
make db-migrate          # Crée les tables
make run-all             # Lance API + Worker

# Méthode 2: Manuel
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-transcribe.txt
pip install -r requirements-enrichment.txt
python app.py & python run_enrichment.py
```

### 3. Test Rapide

```bash
# Ouvrir le dashboard
open http://localhost:8000/dashboard

# Tester avec un fichier
make test-file FILE=mon_audio.wav

# Ou via cURL
curl -X POST "http://localhost:8000/api/transcribe" \
  -F "file=@mon_audio.wav"
```

---

## 🎯 Commandes Essentielles

```bash
# Voir toutes les commandes disponibles
make help

# === LANCEMENT ===
make run              # API uniquement (transcription)
make run-enrichment   # Worker LLM uniquement
make run-all          # API + Worker (COMPLET)
make dev              # Mode développement (auto-reload)

# === CONFIGURATION ===
make config           # Voir la config
make config-balanced  # Preset recommandé (production)
make config-speed     # Preset rapide (tests)
make config-accuracy  # Preset précision (qualité max)

# === TESTS ===
make test                          # Test automatique complet
make test-file FILE=audio.wav      # Test avec fichier
make test-enrich                   # Test enrichissement

# === BASE DE DONNÉES ===
make db-stats         # Stats de la DB
make db-migrate       # Créer tables enrichment
make clean-db         # Nettoyer (>30 jours)
make clean-errors     # Supprimer les erreurs

# === MODÈLES LLM ===
make download-model   # Télécharger Mistral 7B (recommandé)
make list-models      # Lister modèles téléchargés

# === VÉRIFICATIONS ===
make check            # Vérifier l'installation
make info             # Infos système
make urls             # Afficher les URLs utiles
```

---

## ⚙️ Configuration Rapide

### Choix du preset selon vos besoins

| Besoin | Commande | Transcription | Enrichissement |
|--------|----------|---------------|----------------|
| 🚀 Vitesse max | `make config-speed` | tiny (30-50x) | Q4 + threads++ |
| ⚖️ Production | `make config-balanced` | small (5-10x) | Q4 équilibré ✅ |
| 🎯 Qualité max | `make config-accuracy` | medium (2-4x) | Q5 + contexte++ |

### Modification manuelle

```bash
# Changer le modèle de transcription
python config_manager.py set WHISPER model medium

# Activer/désactiver l'enrichissement
python config_manager.py set ENRICHMENT enabled true

# Changer le nombre de workers
python config_manager.py set PERFORMANCE max_workers 8

# Valider la config
python config_manager.py validate

# Recharger sans redémarrer
curl -X POST http://localhost:8000/config/reload
```

---

## 📊 Résolution de Problèmes Courants

### ❌ "Whisper model not loaded"
**Cause**: Le modèle charge au démarrage (30s)  
**Solution**: Attendre que les logs affichent "✅ Whisper model loaded"

### ❌ "Enrichment model not found"
**Cause**: Modèle LLM non téléchargé  
**Solution**: 
```bash
make download-model
# Ou vérifier le chemin dans config.ini
```

### 🐌 Transcription très lente
**Solutions**:
```bash
# Option 1: Modèle plus petit
python config_manager.py set WHISPER model tiny

# Option 2: Activer VAD
python config_manager.py set PERFORMANCE vad_enabled true

# Option 3: Plus de workers
python config_manager.py set PERFORMANCE max_workers 8
```

### 🐌 Enrichissement très lent
**Solutions**:
```bash
# Option 1: Plus de threads
python config_manager.py set ENRICHMENT n_threads 8

# Option 2: Réduire contexte
python config_manager.py set ENRICHMENT n_ctx 2048

# Option 3: Désactiver topics
python config_manager.py set ENRICHMENT generate_topics false
```

### ❌ "ffmpeg not found"
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Vérifier
ffmpeg -version
```

### 💾 Base de données qui grossit
```bash
# Nettoyer les anciennes transcriptions
make clean-db

# Nettoyer agressivement
make clean-all
```

### 🔧 Qualité de transcription faible
```bash
# Augmenter le modèle
python config_manager.py set WHISPER model medium

# Augmenter beam_size
python config_manager.py set PERFORMANCE beam_size 7

# Vérifier la qualité audio d'entrée (doit être claire)
```

### 🎨 Enrichissement de mauvaise qualité
```bash
# Augmenter le modèle
python config_manager.py set ENRICHMENT model_path models/mistral-7b-instruct-v0.3.Q5_K_M.gguf

# Plus de contexte
python config_manager.py set ENRICHMENT n_ctx 8192

# Température plus déterministe
python config_manager.py set ENRICHMENT temperature 0.2
```

### ❌ "Out of memory"
```bash
# Transcription
python config_manager.py set WHISPER model tiny
python config_manager.py set PERFORMANCE max_workers 2

# Enrichissement
python config_manager.py set ENRICHMENT n_ctx 2048
python config_manager.py set ENRICHMENT batch_size 1
```

---

## 🐳 Docker (Alternative)

```bash
# Construction
make docker-build

# Lancement
make docker-run

# Logs
make docker-logs

# Arrêt
make docker-stop
```

---

## 📖 Ressources

- **Dashboard**: http://localhost:8000/dashboard
- **API Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health
- **Guide complet**: Voir `docs/README.md`
- **Déploiement**: Voir `docs/DEPLOYMENT.md`
- **Enrichissement**: Voir `enrichment/README.md`

---

## 🎓 Exemples d'Utilisation

### Python - Transcription + Enrichissement
```python
import requests
import time

# 1. Upload audio
files = {'file': open('audio.wav', 'rb')}
response = requests.post('http://localhost:8000/api/transcribe', files=files)
transcription_id = response.json()['transcription_id']

# 2. Attendre la transcription
while True:
    result = requests.get(f'http://localhost:8000/api/transcribe/{transcription_id}')
    data = result.json()
    
    if data['status'] == 'done':
        # Transcription
        print("Texte:", data['text'])
        
        # Enrichissement (si disponible)
        if 'enrichment' in data:
            enrich = data['enrichment']
            print("\nTitre:", enrich['title'])
            print("Résumé:", enrich['summary'])
            print("Sentiment:", enrich['sentiment'])
            print("Points clés:", enrich['bullets'])
        break
    
    time.sleep(2)
```

### cURL - Workflow Complet
```bash
# 1. Upload
ID=$(curl -s -X POST "http://localhost:8000/api/transcribe" \
  -F "file=@audio.wav" | jq -r '.transcription_id')

echo "Transcription ID: $ID"

# 2. Attendre et récupérer
while true; do
  STATUS=$(curl -s "http://localhost:8000/api/transcribe/$ID" | jq -r '.status')
  echo "Status: $STATUS"
  
  if [ "$STATUS" = "done" ]; then
    # Afficher résultats
    curl -s "http://localhost:8000/api/transcribe/$ID" | jq '{
      text: .text,
      duration: .duration,
      enrichment: .enrichment
    }'
    break
  fi
  
  sleep 3
done
```

### JavaScript/Node.js
```javascript
const FormData = require('form-data');
const fs = require('fs');
const axios = require('axios');

async function transcribeAndEnrich(filePath) {
  // 1. Upload
  const form = new FormData();
  form.append('file', fs.createReadStream(filePath));
  
  const uploadRes = await axios.post('http://localhost:8000/api/transcribe', form, {
    headers: form.getHeaders()
  });
  
  const transcriptionId = uploadRes.data.transcription_id;
  console.log('Transcription ID:', transcriptionId);
  
  // 2. Poll résultat
  while (true) {
    const result = await axios.get(`http://localhost:8000/api/transcribe/${transcriptionId}`);
    const data = result.data;
    
    console.log('Status:', data.status);
    
    if (data.status === 'done') {
      console.log('\n=== TRANSCRIPTION ===');
      console.log(data.text);
      
      if (data.enrichment) {
        console.log('\n=== ENRICHISSEMENT ===');
        console.log('Titre:', data.enrichment.title);
        console.log('Résumé:', data.enrichment.summary);
        console.log('Sentiment:', data.enrichment.sentiment);
        console.log('Points clés:', data.enrichment.bullets);
      }
      
      return data;
    }
    
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
}

transcribeAndEnrich('audio.wav').catch(console.error);
```

---

## 🎯 Métriques de Performance

### Attendues (config balanced)

**Transcription (small model)**

| Audio | Durée | Traitement | Ratio | Enrichissement | Total |
|-------|-------|------------|-------|----------------|-------|
| Court | 30s | 3-5s | 6-10x | 30-40s | ~45s |
| Moyen | 5min | 30-60s | 5-10x | 30-40s | ~90s |
| Long | 30min | 3-6min | 5-10x | 30-40s | 4-7min |

**Temps total** = Transcription + Enrichissement (en parallèle si batch)

### Facteurs d'amélioration

- ✅ **VAD activé**: +40% vitesse transcription
- ✅ **Audio propre**: +20% précision transcription
- ✅ **Modèle adapté**: +50% vitesse (tiny vs medium)
- ✅ **Multi-workers**: +30% sur audios longs
- ✅ **Threads CPU++**: +30% vitesse enrichissement
- ✅ **Batch enrichissement**: Traiter plusieurs simultanément

---

## ✅ Checklist de Production

Avant de déployer en production :

### Transcription
- [ ] Configuration validée: `make config-validate`
- [ ] Tests passés: `make test`
- [ ] Preset appliqué: `make config-balanced`
- [ ] FFmpeg installé: `ffmpeg -version`
- [ ] Espace disque suffisant: >20GB
- [ ] RAM suffisante: >8GB

### Enrichissement
- [ ] Modèle LLM téléchargé: `make list-models`
- [ ] Tables créées: `make db-migrate`
- [ ] Config enrichissement: Section `[ENRICHMENT]` dans config.ini
- [ ] Worker testé: `python3 test_enrichment_module.py`
- [ ] RAM suffisante: >10GB (avec modèle)

### Sécurité & Infrastructure
- [ ] Rate limiting configuré
- [ ] Backup de la DB planifié
- [ ] Logs configurés et rotatifs
- [ ] HTTPS configuré (Nginx)
- [ ] Monitoring en place
- [ ] Firewall configuré

---

## 🔥 Optimisations Avancées

### Pour serveurs puissants (8+ cores, 16GB+ RAM)
```ini
[PERFORMANCE]
max_workers = 8
vad_enabled = true

[WHISPER]
model = small
cpu_threads = 14

[ENRICHMENT]
n_threads = 8
batch_size = 5
n_ctx = 4096
```

### Pour GPU NVIDIA
```ini
[WHISPER]
device = cuda
compute_type = float16
model = medium  # Peut gérer plus gros

[ENRICHMENT]
# LLM reste sur CPU
n_threads = 6
```

### Pour RAM limitée (<8GB)
```ini
[WHISPER]
model = tiny

[PERFORMANCE]
max_workers = 2

[LIMITS]
max_file_size_mb = 50

[ENRICHMENT]
enabled = false  # Désactiver enrichissement
# OU
n_ctx = 2048
batch_size = 1
```

### Pour call centers avec beaucoup de silence
```ini
[PERFORMANCE]
vad_enabled = true

[VAD]
silence_thresh = -35
min_silence_len = 700

[ENRICHMENT]
generate_sentiment = true  # Important pour call centers
```

### Pour audio de qualité studio
```ini
[WHISPER]
model = medium
beam_size = 10

[VAD]
silence_thresh = -45

[ENRICHMENT]
model_path = models/mistral-7b-instruct-v0.3.Q5_K_M.gguf
n_ctx = 8192
temperature = 0.4
```

---

## 📞 Support & Aide

### Vérifier le statut
```bash
# Santé de l'API
curl http://localhost:8000/health

# Configuration
curl http://localhost:8000/config

# Logs
make logs
tail -f logs/vocalyx.log
tail -f logs/enrichment.log
```

### Obtenir de l'aide
```bash
# Aide sur les commandes
make help

# Vérifier l'installation
make check

# Infos système
make info

# Documentation API interactive
open http://localhost:8000/docs
```

### En cas de problème

1. **Vérifier les logs**
   ```bash
   make logs
   # ou
   tail -f logs/vocalyx.log
   tail -f logs/enrichment.log
   ```

2. **Vérifier la config**
   ```bash
   make config-validate
   ```

3. **Tester les modules**
   ```bash
   make test-transcribe
   make test-enrich
   ```

4. **Redémarrer proprement**
   ```bash
   make stop
   make clean
   make run-all
   ```

5. **Reset complet** (dernier recours)
   ```bash
   make clean-all
   make install-all
   make download-model
   make config-balanced
   make db-migrate
   make run-all
   ```

---

## 🚀 Passer en Production

### Option 1: Systemd (Linux)

```bash
# 1. Copier les fichiers
sudo cp -r . /opt/vocalyx
cd /opt/vocalyx

# 2. Service API
sudo nano /etc/systemd/system/vocalyx-api.service
```

```ini
[Unit]
Description=Vocalyx API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/vocalyx
Environment="PATH=/opt/vocalyx/venv/bin"
ExecStart=/opt/vocalyx/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# 3. Service Worker Enrichissement
sudo nano /etc/systemd/system/vocalyx-enrichment.service
```

```ini
[Unit]
Description=Vocalyx Enrichment Worker
After=network.target vocalyx-api.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/vocalyx
Environment="PATH=/opt/vocalyx/venv/bin"
ExecStart=/opt/vocalyx/venv/bin/python3 run_enrichment.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# 4. Activer et démarrer
sudo systemctl daemon-reload
sudo systemctl enable vocalyx-api vocalyx-enrichment
sudo systemctl start vocalyx-api vocalyx-enrichment
sudo systemctl status vocalyx-api vocalyx-enrichment
```

### Option 2: Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/vocalyx
server {
    listen 80;
    server_name vocalyx.votredomaine.com;
    
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/vocalyx /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# HTTPS avec Let's Encrypt
sudo certbot --nginx -d vocalyx.votredomaine.com
```

---

## 🎉 Vous êtes prêt !

Votre installation Vocalyx complète (Transcription + Enrichissement) est maintenant opérationnelle.

### Prochaines étapes

1. ✅ Lancer: `make run-all`
2. ✅ Tester: `make test`
3. ✅ Dashboard: http://localhost:8000/dashboard
4. ✅ Docs: http://localhost:8000/docs

### Ressources

- 📖 README complet: `docs/README.md`
- 🚀 Déploiement détaillé: `docs/DEPLOYMENT.md`
- 🎨 Module enrichissement: `enrichment/README.md`
- 📝 Guide logs: `docs/LOGS.md`
- 💡 Commandes: `make help`
- 📧 Support: guilhem.l.richard@gmail.com

---

**Vocalyx v1.4.0** - Transcription + Enrichissement Intelligent 🎙️✨

*La voix de vos clients, intelligemment exploitée !* 🚀