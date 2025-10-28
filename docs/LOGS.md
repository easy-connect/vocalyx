# 📝 Guide des Logs Vocalyx

## Format uniforme des logs

Tous les logs de Vocalyx utilisent maintenant le même format :

```
YYYY-MM-DD HH:MM:SS,mmm [NIVEAU] nom_logger: message
```

### Exemple
```
2025-10-24 07:58:19,783 [INFO] vocalyx: 🚀 Loading Whisper model: small on cpu
2025-10-24 07:58:21,458 [INFO] vocalyx: ✅ Whisper loaded | VAD: True | Workers: 4
2025-10-24 07:58:33,366 [INFO] vocalyx: [ab9519a9] 📥 bca-short.wav (3.41MB) | VAD: True
2025-10-24 07:58:33,381 [INFO] vocalyx: [ab9519a9] 📏 Original audio duration: 111.9s
2025-10-24 07:58:35,049 [INFO] faster_whisper: Processing audio with duration 00:03.038
2025-10-24 07:58:52,683 [INFO] vocalyx: [ab9519a9] ✅ Completed: 21 segments | Audio: 111.9s
2025-10-24 07:59:10,123 [INFO] uvicorn.access: 127.0.0.1:45872 - "POST /transcribe HTTP/1.1" 200 OK
```

## Configuration du logging

### Dans config.ini

```ini
[LOGGING]
# Niveau de log: DEBUG, INFO, WARNING, ERROR, CRITICAL
level = INFO

# Activer les logs dans un fichier
file_enabled = true

# Chemin du fichier de log
file_path = logs/vocalyx.log

# Activer les couleurs (développement)
colored = false
```

### Niveaux de log

| Niveau | Usage | Exemple |
|--------|-------|---------|
| **DEBUG** | Détails techniques | Valeurs de variables, étapes détaillées |
| **INFO** | Informations générales | Démarrage, transcriptions, etc. |
| **WARNING** | Avertissements | Fichier suspect, fallback utilisé |
| **ERROR** | Erreurs | Échec de transcription, erreur DB |
| **CRITICAL** | Erreurs critiques | Crash imminent, modèle non chargé |

### Logs en mode développement

Activer les couleurs pour une meilleure lisibilité :

```ini
[LOGGING]
level = DEBUG
colored = true
```

Résultat :
- 🟢 INFO en vert
- 🟡 WARNING en jaune
- 🔴 ERROR en rouge
- 🔵 DEBUG en cyan

## Sources de logs

### 1. vocalyx (application)
```
2025-10-24 07:58:33,366 [INFO] vocalyx: [ab9519a9] 📥 bca-short.wav (3.41MB)
```
- Transcriptions
- Startup/Shutdown
- Configuration
- Erreurs applicatives

### 2. faster_whisper (modèle de transcription)
```
2025-10-24 07:58:35,049 [INFO] faster_whisper: Processing audio with duration 00:03.038
2025-10-24 07:58:35,159 [INFO] faster_whisper: VAD filter removed 00:00.000 of audio
```
- Traitement audio
- VAD (Voice Activity Detection)
- Progression de la transcription

### 3. uvicorn.access (requêtes HTTP)
```
2025-10-24 07:59:10,123 [INFO] uvicorn.access: 127.0.0.1:45872 - "POST /transcribe HTTP/1.1" 200 OK
```
- Requêtes API
- Codes de réponse HTTP
- IPs des clients

### 4. uvicorn (serveur web)
```
2025-10-24 07:58:18,500 [INFO] uvicorn: Started server process [18543]
2025-10-24 07:58:18,501 [INFO] uvicorn: Waiting for application startup.
2025-10-24 07:58:21,460 [INFO] uvicorn: Application startup complete.
```
- Démarrage/Arrêt du serveur
- Reload en mode développement
- Erreurs serveur

## Filtrage des logs

### Par niveau
```bash
# Voir uniquement les erreurs
grep "\[ERROR\]" logs/vocalyx.log
grep "\[CRITICAL\]" logs/vocalyx.log

# Voir warnings et erreurs
grep -E "\[(WARNING|ERROR|CRITICAL)\]" logs/vocalyx.log
```

### Par source
```bash
# Logs de l'application uniquement
grep "vocalyx:" logs/vocalyx.log

# Logs Whisper uniquement
grep "faster_whisper:" logs/vocalyx.log

# Logs des requêtes HTTP
grep "uvicorn.access:" logs/vocalyx.log
```

### Par transcription
```bash
# Suivre une transcription spécifique
grep "ab9519a9" logs/vocalyx.log
```

### Temps réel
```bash
# Tous les logs
tail -f logs/vocalyx.log

# Uniquement erreurs
tail -f logs/vocalyx.log | grep -E "\[(ERROR|CRITICAL)\]"

# Uniquement transcriptions
tail -f logs/vocalyx.log | grep "vocalyx:"
```

## Analyse des logs

### Vérifier la santé

**Logs normaux au démarrage:**
```
2025-10-24 07:58:18,500 [INFO] uvicorn: Started server process [18543]
2025-10-24 07:58:18,501 [INFO] uvicorn: Waiting for application startup.
2025-10-24 07:58:19,783 [INFO] vocalyx: 🚀 Loading Whisper model: small on cpu
2025-10-24 07:58:21,458 [INFO] vocalyx: ✅ Whisper loaded | VAD: True | Workers: 4
2025-10-24 07:58:21,460 [INFO] uvicorn: Application startup complete.
```

**Logs d'une transcription réussie:**
```
2025-10-24 07:58:33,366 [INFO] vocalyx: [ab9519a9] 📥 bca-short.wav (3.41MB) | VAD: True
2025-10-24 07:58:33,381 [INFO] vocalyx: [ab9519a9] 📏 Original audio duration: 111.9s
2025-10-24 07:58:33,397 [INFO] vocalyx: ✅ Audio preprocessed: ab9519a9_processed.wav
2025-10-24 07:58:34,940 [INFO] vocalyx: 🎤 VAD: Detected 21 speech segments
2025-10-24 07:58:34,944 [INFO] vocalyx: 🎯 VAD: Created 4 optimized segments
2025-10-24 07:58:34,944 [INFO] vocalyx: [ab9519a9] 🔪 Created 4 segments
2025-10-24 07:58:35,049 [INFO] faster_whisper: Processing audio with duration 00:03.038
2025-10-24 07:58:52,683 [INFO] vocalyx: [ab9519a9] ✅ Completed: 21 segments | Audio: 111.9s | Processing: 19.3s | Speed: 5.8x realtime | VAD: True
```

### Détecter les problèmes

**Erreur de chargement du modèle:**
```
2025-10-24 08:00:00,000 [ERROR] vocalyx: ❌ Error loading Whisper model: ...
```
→ Vérifier que le modèle existe et que les ressources sont suffisantes

**Transcription échouée:**
```
2025-10-24 08:05:30,123 [ERROR] vocalyx: [xyz123] ❌ Error: Invalid or corrupted audio file
```
→ Vérifier la validité du fichier audio

**Erreurs de mémoire:**
```
2025-10-24 08:10:00,000 [CRITICAL] vocalyx: Out of memory
```
→ Réduire `max_workers` ou utiliser un modèle plus petit

**Rate limiting:**
```
2025-10-24 08:15:00,000 [WARNING] slowapi: Rate limit exceeded for 127.0.0.1
```
→ Client fait trop de requêtes

## Métriques dans les logs

### Identifier les performances

**Temps de traitement:**
```
Processing: 19.3s
```

**Ratio de vitesse:**
```
Speed: 5.8x realtime
```
Signifie que 1 minute d'audio est traitée en ~10 secondes

**Nombre de segments:**
```
21 segments
```
Plus il y a de segments, plus le découpage est fin

**VAD activé:**
```
VAD: True
```

**Taille du fichier:**
```
(3.41MB)
```

### Exemple de calcul

```
Audio: 111.9s | Processing: 19.3s | Speed: 5.8x realtime
```

Calcul : 111.9 / 19.3 = 5.8x

- **< 2x** : Lent (considérer optimisations)
- **2-5x** : Normal
- **5-10x** : Bon
- **> 10x** : Excellent

## Rotation des logs

### Configuration automatique

Créer `/etc/logrotate.d/vocalyx`:

```
/opt/vocalyx/logs/vocalyx.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 vocalyx vocalyx
    postrotate
        systemctl reload vocalyx > /dev/null 2>&1 || true
    endscript
}
```

### Manuel

```bash
# Archiver les logs
cd logs
gzip vocalyx.log
mv vocalyx.log.gz vocalyx-$(date +%Y%m%d).log.gz

# Nettoyer les anciens (>30 jours)
find logs/ -name "*.log.gz" -mtime +30 -delete
```

## Debugging

### Mode DEBUG

Activer temporairement :

```bash
# Dans config.ini
[LOGGING]
level = DEBUG

# Recharger
curl -X POST http://localhost:8000/config/reload
```

Logs DEBUG supplémentaires :
- Valeurs des variables
- Étapes de traitement détaillées
- Paramètres de configuration
- États internes

**⚠️ Attention:** Le mode DEBUG génère beaucoup de logs. Ne pas utiliser en production continue.

### Tracer une transcription

```bash
# Obtenir l'ID de transcription
ID="ab9519a9-86f9-45c3-8011-fdffe010aa7f"

# Voir tous ses logs
grep "$ID" logs/vocalyx.log

# Avec timestamps et contexte
grep -B 2 -A 2 "$ID" logs/vocalyx.log
```

### Logs en temps réel avec filtres

```bash
# Voir uniquement les transcriptions complétées
tail -f logs/vocalyx.log | grep "✅ Completed"

# Voir les erreurs en temps réel
tail -f logs/vocalyx.log | grep -E "\[ERROR\]|\[CRITICAL\]" --color

# Voir les uploads
tail -f logs/vocalyx.log | grep "📥"
```

## Monitoring via logs

### Script de monitoring

**monitor_vocalyx.sh:**
```bash
#!/bin/bash

LOG_FILE="logs/vocalyx.log"

# Compter les transcriptions des dernières 24h
COMPLETED=$(grep -c "✅ Completed" "$LOG_FILE")
ERRORS=$(grep -c "\[ERROR\]" "$LOG_FILE")

echo "📊 Statistiques 24h:"
echo "  ✅ Transcriptions: $COMPLETED"
echo "  ❌ Erreurs: $ERRORS"

# Taux d'erreur
if [ $COMPLETED -gt 0 ]; then
    ERROR_RATE=$(echo "scale=2; ($ERRORS * 100) / $COMPLETED" | bc)
    echo "  📈 Taux d'erreur: $ERROR_RATE%"
fi

# Vitesse moyenne
AVG_SPEED=$(grep "Speed:" "$LOG_FILE" | \
    grep -oP 'Speed: \K[0-9.]+' | \
    awk '{sum+=$1; count++} END {printf "%.1f", sum/count}')
echo "  ⚡ Vitesse moyenne: ${AVG_SPEED}x realtime"
```

### Alertes par email

**alert_errors.sh:**
```bash
#!/bin/bash

ERRORS=$(tail -100 logs/vocalyx.log | grep -c "\[ERROR\]")

if [ $ERRORS -gt 10 ]; then
    echo "⚠️ Plus de 10 erreurs détectées!" | \
        mail -s "Alert Vocalyx" admin@example.com
fi
```

Ajouter au cron :
```bash
# Vérifier toutes les heures
0 * * * * /opt/vocalyx/alert_errors.sh
```

## Exportation des logs

### Vers un fichier CSV

```bash
# Extraire les métriques de performance
grep "✅ Completed" logs/vocalyx.log | \
    sed -E 's/.*\[([a-f0-9-]+)\].*Audio: ([0-9.]+)s.*Processing: ([0-9.]+)s.*Speed: ([0-9.]+)x.*/\1,\2,\3,\4/' \
    > performance.csv
```

### Vers Elasticsearch (optionnel)

Utiliser Filebeat pour envoyer les logs vers Elasticsearch :

```yaml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /opt/vocalyx/logs/vocalyx.log
  multiline.pattern: '^\d{4}-\d{2}-\d{2}'
  multiline.negate: true
  multiline.match: after

output.elasticsearch:
  hosts: ["localhost:9200"]
  index: "vocalyx-%{+yyyy.MM.dd}"
```

## FAQ Logs

**Q: Les logs prennent trop de place**
```bash
# Activer la compression
[LOGGING]
level = INFO  # Pas DEBUG

# Rotation plus agressive
rotate 3  # Au lieu de 7 jours
```

**Q: Comment désactiver les logs Uvicorn?**
```ini
[LOGGING]
level = WARNING  # Ne loguer que warnings et erreurs
```

**Q: Logs colorés ne s'affichent pas**
```ini
[LOGGING]
colored = true
```
Et vérifier que le terminal supporte les couleurs.

**Q: Comment exporter vers Syslog?**
Modifier `logging_config.py` pour ajouter un handler SysLog :
```python
from logging.handlers import SysLogHandler

syslog = SysLogHandler(address='/dev/log')
handlers.append(syslog)
```

---

## Ressources

- **Configuration**: `config.ini` section `[LOGGING]`
- **Code source**: `logging_config.py`
- **Rotation**: `/etc/logrotate.d/vocalyx`
- **Monitoring**: Scripts dans le dossier racine

Pour plus d'informations, consultez [README.md](README.md)