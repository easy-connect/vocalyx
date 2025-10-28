# ⚡ Migration Rapide - Vocalyx v1.4

Guide express pour migrer en 5 minutes.

## 🚀 Quick Start

```bash
# 1. Télécharger les fichiers de migration
curl -O https://raw.githubusercontent.com/votre-repo/vocalyx/main/migrate_structure.sh
curl -O https://raw.githubusercontent.com/votre-repo/vocalyx/main/validate_migration.py
curl -O https://raw.githubusercontent.com/votre-repo/vocalyx/main/Makefile

# 2. Rendre exécutables
chmod +x migrate_structure.sh validate_migration.py

# 3. Arrêter Vocalyx
pkill -f "app:app" || systemctl stop vocalyx

# 4. Migrer
./migrate_structure.sh

# 5. Valider
python3 validate_migration.py

# 6. Relancer
make run
# ou
systemctl start vocalyx
```

## ✅ C'est fait !

Votre Vocalyx est maintenant en v1.4 avec la nouvelle architecture modulaire.

## 🎨 Installer l'enrichissement (optionnel)

```bash
# Installer le module
make install-enrichment

# Télécharger le modèle LLM (~4GB)
make download-model

# Créer les tables
make db-migrate

# Lancer le worker
make run-enrichment
```

## 📚 Documentation Complète

- **Guide détaillé** : [MIGRATION.md](MIGRATION.md)
- **Documentation** : [docs/README.md](docs/README.md)
- **Démarrage rapide** : [docs/QUICKSTART.md](docs/QUICKSTART.md)

## 🆘 Problème ?

```bash
# Rollback automatique
BACKUP_DIR=$(ls -td backup_* | head -1)
cp -r "$BACKUP_DIR"/* .
make run
```

## 🎯 Prochaines étapes

1. `make test` - Tester une transcription
2. `make config-balanced` - Configurer
3. `make help` - Voir toutes les commandes
4. Lire [docs/README.md](docs/README.md)

---

**Questions ?** guilhem.l.richard@gmail.com