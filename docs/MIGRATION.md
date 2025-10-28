# 🔄 Guide de Migration Vocalyx v1.3 → v1.4

Ce guide explique comment migrer votre installation Vocalyx vers la nouvelle architecture modulaire.

## 📋 Vue d'ensemble

### Ancienne structure (v1.3)
```
vocalyx/
├── app.py
├── transcription.py
├── audio_utils.py
├── cleanup_db.py
├── config_manager.py
└── README.md
```

### Nouvelle structure (v1.4)
```
vocalyx/
├── app.py
├── transcribe/          # 🆕 Module transcription
├── enrichment/          # 🆕 Module enrichissement
├── scripts/             # 🆕 Scripts utilitaires
├── docs/                # 🆕 Documentation
└── models/              # 🆕 Modèles LLM
```

---

## 🚀 Migration Automatique (Recommandé)

### Étape 1 : Préparation

```bash
# Se placer dans le répertoire Vocalyx
cd /path/to/vocalyx

# Vérifier qu'on est au bon endroit
ls app.py transcription.py  # Doit afficher les deux fichiers

# Arrêter Vocalyx si en cours d'exécution
pkill -f "app:app" || true
```

### Étape 2 : Télécharger les scripts de migration

```bash
# Télécharger migrate_structure.sh
curl -O https://raw.githubusercontent.com/votre-repo/vocalyx/main/migrate_structure.sh

# Télécharger validate_migration.py
curl -O https://raw.githubusercontent.com/votre-repo/vocalyx/main/validate_migration.py

# Télécharger le nouveau Makefile
curl -O https://raw.githubusercontent.com/votre-repo/vocalyx/main/Makefile

# Rendre exécutables
chmod +x migrate_structure.sh validate_migration.py
```

### Étape 3 : Exécuter la migration

```bash
# Lancer la migration automatique
./migrate_structure.sh
```

Le script va :
- ✅ Créer un backup automatique
- ✅ Créer la nouvelle structure de dossiers
- ✅ Déplacer les fichiers
- ✅ Mettre à jour les imports
- ✅ Modifier database.py

### Étape 4 : Valider la migration

```bash
# Valider que tout est OK
python3 validate_migration.py
```

Si tout est vert ✅, la migration est réussie !

### Étape 5 : Tester

```bash
# Activer l'environnement virtuel
source venv/bin/activate

# Vérifier l'installation
make check

# Tester l'API
make run

# Dans un autre terminal, tester une transcription
make test
```

---

## 🔧 Migration Manuelle

Si vous préférez migrer manuellement :

### 1. Créer la structure

```bash
mkdir -p transcribe enrichment models scripts docs
touch transcribe/__init__.py enrichment/__init__.py
```

### 2. Déplacer les fichiers

```bash
# Module transcription
mv transcription.py transcribe/
mv audio_utils.py transcribe/

# Scripts
mv cleanup_db.py scripts/
mv config_manager.py scripts/
mv test_vocalyx.sh scripts/
mv install.sh scripts/

# Documentation
mv README.md docs/
mv QUICKSTART.md docs/
mv DEPLOYMENT.md docs/
mv LOGS.md docs/
```

### 3. Créer transcribe/__init__.py

```python
"""Module de transcription Vocalyx"""

from .transcription import (
    initialize_whisper_model,
    cleanup_resources,
    run_transcription_optimized,
    whisper_model
)

from .audio_utils import (
    sanitize_filename,
    get_audio_duration,
    preprocess_audio,
    detect_speech_segments,
    split_audio_intelligent
)

__all__ = [
    'initialize_whisper_model',
    'cleanup_resources',
    'run_transcription_optimized',
    'whisper_model',
    'sanitize_filename',
    'get_audio_duration',
    'preprocess_audio',
    'detect_speech_segments',
    'split_audio_intelligent'
]
```

### 4. Mettre à jour app.py

Remplacer :
```python
from transcription import initialize_whisper_model
from audio_utils import sanitize_filename
```

Par :
```python
from transcribe.transcription import initialize_whisper_model
from transcribe.audio_utils import sanitize_filename
```

### 5. Mettre à jour api/endpoints.py

Même chose :
```python
from transcribe.transcription import run_transcription_optimized
from transcribe.audio_utils import sanitize_filename
```

### 6. Mettre à jour database.py

Ajouter avant `created_at` :
```python
# Pour l'enrichissement
enrichment_requested = Column(Integer, default=1)
```

### 7. Remplacer le Makefile

Utiliser le nouveau Makefile fourni.

---

## ✅ Checklist de Validation

Après migration, vérifier :

- [ ] `python3 validate_migration.py` → Tout vert
- [ ] `make check` → Pas d'erreurs
- [ ] `make run` → API démarre sans erreur
- [ ] `make test` → Test transcription réussit
- [ ] Dashboard accessible : http://localhost:8000/dashboard
- [ ] Logs créés dans `logs/vocalyx.log`

---

## 🔄 Rollback (en cas de problème)

Si quelque chose ne va pas :

```bash
# Restaurer depuis le backup
BACKUP_DIR=$(ls -td backup_* | head -1)
echo "Restauration depuis $BACKUP_DIR"

# Arrêter Vocalyx
pkill -f "app:app" || true

# Restaurer les fichiers
rm -rf transcribe enrichment scripts docs models
cp -r "$BACKUP_DIR"/* .

# Relancer
source venv/bin/activate
python app.py
```

---

## 📊 Base de Données

### Migration de la colonne enrichment_requested

La colonne `enrichment_requested` est ajoutée automatiquement.

Si vous avez des transcriptions existantes, elles auront `enrichment_requested=1` par défaut.

Pour désactiver l'enrichissement sur certaines :

```python
# Dans la console Python
from database import SessionLocal, Transcription

db = SessionLocal()
transcription = db.query(Transcription).filter(Transcription.id == "votre-id").first()
transcription.enrichment_requested = 0
db.commit()
```

---

## 🆕 Nouvelles Fonctionnalités après Migration

### Makefile enrichi

```bash
make help                  # Aide complète
make install-enrichment    # Installer module enrichissement
make run-enrichment        # Lancer worker enrichissement
make download-model        # Télécharger modèle LLM
make db-migrate            # Créer tables enrichment
```

### Scripts réorganisés

```bash
python scripts/cleanup_db.py --stats
python scripts/config_manager.py show
bash scripts/test_vocalyx.sh
```

### Documentation structurée

- `docs/README.md` - Guide complet
- `docs/QUICKSTART.md` - Démarrage rapide
- `docs/DEPLOYMENT.md` - Déploiement production
- `docs/LOGS.md` - Guide des logs

---

## 🐛 Problèmes Connus

### ImportError: No module named 'transcribe'

**Cause** : Python ne trouve pas le nouveau module

**Solution** :
```bash
# Vérifier que __init__.py existe
ls transcribe/__init__.py

# Vérifier depuis Python
python3 -c "import transcribe; print(transcribe.__file__)"
```

### API démarre mais /transcribe échoue

**Cause** : Imports non mis à jour dans api/endpoints.py

**Solution** :
```bash
# Vérifier les imports
grep "from transcribe" api/endpoints.py

# Si absents, mettre à jour manuellement
```

### Scripts ne fonctionnent plus

**Cause** : Chemins obsolètes

**Solution** :
```bash
# Utiliser les nouvelles commandes
make clean-db      # au lieu de python cleanup_db.py
make config        # au lieu de python config_manager.py show
```

---

## 💡 Conseils

1. **Backup** : Le script crée un backup automatique, mais faites-en un manuel aussi
2. **Environnement** : Toujours travailler dans le venv
3. **Tests** : Tester après chaque étape majeure
4. **Logs** : Consulter `logs/vocalyx.log` en cas de problème
5. **Documentation** : Nouvelle doc dans `docs/`

---

## 📞 Support

En cas de problème :

1. Consulter les logs : `tail -f logs/vocalyx.log`
2. Valider la migration : `python3 validate_migration.py`
3. Vérifier les imports : `python3 -c "import transcribe"`
4. Rollback si nécessaire (voir section ci-dessus)
5. Ouvrir une issue sur GitHub avec les logs

---

## 🎯 Après la Migration

### Installer le module d'enrichissement

Une fois la migration terminée, vous pouvez installer le module d'enrichissement :

```bash
# 1. Installer les dépendances
make install-enrichment

# 2. Télécharger un modèle LLM
make download-model

# 3. Créer les tables de la base de données
make db-migrate

# 4. Lancer le worker d'enrichissement
make run-enrichment
```

### Utiliser les nouvelles commandes

```bash
# Lancer tout (API + Worker)
make run-all

# Voir les statistiques
make db-stats

# Nettoyer les anciennes transcriptions
make clean-db

# Afficher les URLs
make urls

# Documentation interactive
make docs
```

---

## 📈 Améliorations Apportées

### Architecture
- ✅ **Modularité** : Code séparé en modules logiques
- ✅ **Scalabilité** : Ajout facile de nouveaux modules
- ✅ **Maintenabilité** : Code plus organisé et lisible

### Développement
- ✅ **Tests** : Structure facilitant les tests unitaires
- ✅ **Documentation** : Doc centralisée et accessible
- ✅ **Scripts** : Outils de gestion consolidés

### Production
- ✅ **Déploiement** : Séparation des services
- ✅ **Monitoring** : Logs séparés par module
- ✅ **Configuration** : Gestion simplifiée

---

## 🔮 Prochaines Étapes

Après avoir migré avec succès :

1. **Tester l'enrichissement**
   ```bash
   # Créer une transcription
   make test
   
   # Vérifier qu'elle est enrichie
   # (titre, résumé, points clés générés automatiquement)
   ```

2. **Configurer le déploiement systemd**
   ```bash
   # API
   sudo systemctl enable vocalyx
   sudo systemctl start vocalyx
   
   # Worker enrichissement
   sudo systemctl enable vocalyx-enrichment
   sudo systemctl start vocalyx-enrichment
   ```

3. **Mettre en place le monitoring**
   ```bash
   # Métriques Prometheus (optionnel)
   make install-monitoring
   ```

4. **Optimiser les performances**
   ```bash
   # Appliquer le preset adapté
   make config-balanced  # ou config-speed / config-accuracy
   ```

---

## 📝 Changelog v1.3 → v1.4

### Ajouté
- ✨ Module `transcribe/` pour la transcription
- ✨ Module `enrichment/` pour le post-traitement LLM
- ✨ Dossier `scripts/` pour les utilitaires
- ✨ Dossier `docs/` pour la documentation
- ✨ Dossier `models/` pour les modèles LLM
- ✨ Colonne `enrichment_requested` dans la table transcriptions
- ✨ Makefile enrichi avec 40+ commandes
- ✨ Scripts de migration et validation automatiques
- ✨ Support pour llama-cpp-python

### Modifié
- 🔄 Imports mis à jour dans `app.py` et `api/endpoints.py`
- 🔄 Structure de dossiers refactorisée
- 🔄 Documentation réorganisée
- 🔄 README.md simplifié avec liens vers docs/

### Déprécié
- ⚠️ Anciens chemins directs (transcription.py, audio_utils.py)
- ⚠️ Commandes scripts sans make

### Supprimé
- ❌ Aucun fichier supprimé (migration non-destructive)

---

## 🔐 Sécurité

### Fichiers sensibles après migration

Vérifier que `.gitignore` exclut :
- `models/*.gguf` (modèles LLM trop gros)
- `*.db` (base de données)
- `logs/*.log` (logs potentiellement sensibles)
- `tmp_uploads/*` (fichiers temporaires)
- `backup_*/` (backups)

### Permissions recommandées

```bash
# Fichiers de config
chmod 600 config.ini

# Scripts exécutables
chmod +x scripts/*.sh
chmod +x migrate_structure.sh
chmod +x validate_migration.py

# Base de données
chmod 600 transcriptions.db
```

---

## 🧪 Tests Post-Migration

### Test 1 : API de base
```bash
curl http://localhost:8000/health
# Doit retourner: {"status": "healthy", ...}
```

### Test 2 : Configuration
```bash
curl http://localhost:8000/config
# Doit retourner la config sans erreur
```

### Test 3 : Transcription
```bash
# Avec un fichier audio
curl -X POST "http://localhost:8000/api/transcribe" \
  -F "file=@test_audio.wav"
  
# Doit retourner: {"transcription_id": "...", "status": "pending"}
```

### Test 4 : Dashboard
```bash
# Dans le navigateur
open http://localhost:8000/dashboard
```

### Test 5 : Modules Python
```python
# Dans Python
from transcribe import initialize_whisper_model
from transcribe.audio_utils import sanitize_filename

print("✅ Imports OK")
```

---

## 📊 Comparaison Avant/Après

### Structure des fichiers

| Avant (v1.3) | Après (v1.4) |
|--------------|--------------|
| `transcription.py` | `transcribe/transcription.py` |
| `audio_utils.py` | `transcribe/audio_utils.py` |
| `cleanup_db.py` | `scripts/cleanup_db.py` |
| `config_manager.py` | `scripts/config_manager.py` |
| `README.md` | `docs/README.md` |
| - | `enrichment/` (nouveau) |
| - | `models/` (nouveau) |

### Commandes

| Avant (v1.3) | Après (v1.4) |
|--------------|--------------|
| `python cleanup_db.py --stats` | `make db-stats` |
| `python config_manager.py show` | `make config` |
| `bash test_vocalyx.sh` | `make test` |
| `python app.py` | `make run` |
| - | `make run-enrichment` |
| - | `make download-model` |

---

## 💾 Backup et Restauration

### Créer un backup manuel

```bash
# Avant migration
tar -czf vocalyx_backup_$(date +%Y%m%d).tar.gz \
  --exclude=venv \
  --exclude=tmp_uploads \
  --exclude=logs \
  .

# Vérifier
tar -tzf vocalyx_backup_*.tar.gz | head
```

### Restaurer depuis backup

```bash
# Arrêter Vocalyx
pkill -f "app:app" || true

# Extraire
tar -xzf vocalyx_backup_YYYYMMDD.tar.gz

# Réinstaller dépendances si nécessaire
make install

# Relancer
make run
```

---

## 🌐 Migration en Production

### Avec Systemd

```bash
# 1. Arrêter l'ancien service
sudo systemctl stop vocalyx

# 2. Migrer
cd /opt/vocalyx
./migrate_structure.sh

# 3. Valider
python3 validate_migration.py

# 4. Mettre à jour le service systemd
sudo nano /etc/systemd/system/vocalyx.service
# Vérifier que WorkingDirectory et ExecStart sont corrects

# 5. Recharger et redémarrer
sudo systemctl daemon-reload
sudo systemctl start vocalyx

# 6. Vérifier
sudo systemctl status vocalyx
```

### Avec Docker

```bash
# 1. Arrêter le conteneur
docker stop vocalyx

# 2. Mettre à jour le code
git pull origin main

# 3. Reconstruire l'image
docker build -t vocalyx:v1.4 .

# 4. Relancer
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/config.ini:/app/config.ini \
  -v $(pwd)/transcriptions.db:/app/transcriptions.db \
  --name vocalyx \
  vocalyx:v1.4
```

---

## 🔍 Diagnostic

### La migration semble bloquée

```bash
# Vérifier les processus
ps aux | grep python

# Vérifier les fichiers
ls -la transcribe/ enrichment/ scripts/

# Vérifier les permissions
ls -l migrate_structure.sh validate_migration.py
```

### Erreurs d'imports

```bash
# Vérifier PYTHONPATH
echo $PYTHONPATH

# Vérifier que les __init__.py existent
find . -name "__init__.py"

# Tester manuellement
python3 << EOF
import sys
sys.path.insert(0, '.')
import transcribe
print(transcribe.__file__)
EOF
```

### Base de données corrompue

```bash
# Vérifier l'intégrité
sqlite3 transcriptions.db "PRAGMA integrity_check;"

# Restaurer depuis backup
cp backups/transcriptions_*.db transcriptions.db
```

---

## ✨ Fonctionnalités Futures

Avec cette nouvelle architecture, il sera plus facile d'ajouter :

- 🎯 **Module d'analyse** : Sentiment, catégorisation automatique
- 🔊 **Module de synthèse vocale** : TTS pour générer des réponses
- 📊 **Module de reporting** : Statistiques avancées, exports
- 🌍 **Module de traduction** : Traduction automatique multilingue
- 🤖 **Module d'agents** : Agents conversationnels intelligents

---

## 📧 Contact et Support

- **Email** : guilhem.l.richard@gmail.com
- **Documentation** : [docs/README.md](docs/README.md)
- **Issues** : GitHub Issues

---

**Version 1.4.0** | Dernière mise à jour : $(date +%Y-%m-%d)