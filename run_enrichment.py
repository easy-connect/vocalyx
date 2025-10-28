#!/usr/bin/env python3
"""
run_enrichment.py

Point d'entrée pour lancer le worker d'enrichissement Vocalyx.
Charge la configuration, initialise le worker et le lance.
"""

import sys
import os
import logging
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from enrichment.config import EnrichmentConfig
from enrichment.worker import EnrichmentWorker
from enrichment.models import create_tables
from logging_config import setup_logging


def print_banner():
    """Affiche la bannière de démarrage"""
    banner = """
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║              🎨 Vocalyx Enrichment Worker               ║
║                                                          ║
║  Génération automatique de titre, résumé et insights    ║
║  pour les transcriptions audio via LLM                   ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""
    print(banner)


def check_dependencies():
    """Vérifie que toutes les dépendances sont installées"""
    missing = []
    
    try:
        import llama_cpp
    except ImportError:
        missing.append("llama-cpp-python")
    
    try:
        import sqlalchemy
    except ImportError:
        missing.append("sqlalchemy")
    
    try:
        from database import Base
    except ImportError:
        missing.append("database.py (configuration DB)")
    
    if missing:
        print("❌ Dépendances manquantes:")
        for dep in missing:
            print(f"   - {dep}")
        print("\n💡 Installez-les avec:")
        print("   pip install -r requirements-enrichment.txt")
        return False
    
    return True


def check_model(config: EnrichmentConfig):
    """Vérifie que le modèle LLM existe"""
    model_path = Path(config.model_path)
    
    if not model_path.exists():
        print(f"❌ Modèle LLM non trouvé: {model_path}")
        print("\n💡 Téléchargez-le avec:")
        print("   make download-model")
        print("\nOu téléchargez manuellement depuis:")
        print("   https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.3-GGUF")
        return False
    
    # Vérifier la taille du fichier
    size_mb = model_path.stat().st_size / (1024 * 1024)
    print(f"✅ Modèle trouvé: {model_path.name} ({size_mb:.0f}MB)")
    
    return True


def check_database():
    """Vérifie que les tables de la base de données existent"""
    try:
        from database import engine, Base
        from enrichment.models import Enrichment
        
        # Vérifier que la table enrichments existe
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if 'enrichments' not in tables:
            print("⚠️  Table 'enrichments' non trouvée")
            print("💡 Créez-la avec: make db-migrate")
            
            response = input("\nCréer les tables maintenant? (y/N): ")
            if response.lower() == 'y':
                create_tables()
                print("✅ Tables créées")
            else:
                return False
        else:
            print("✅ Base de données configurée")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification de la DB: {e}")
        return False


def main():
    """Point d'entrée principal"""
    
    # Afficher la bannière
    print_banner()
    
    # Vérifier les dépendances
    print("🔍 Vérification des dépendances...")
    if not check_dependencies():
        sys.exit(1)
    print()
    
    # Charger la configuration
    print("⚙️  Chargement de la configuration...")
    try:
        config = EnrichmentConfig()
        print("✅ Configuration chargée")
    except Exception as e:
        print(f"❌ Erreur lors du chargement de la config: {e}")
        sys.exit(1)
    print()
    
    # Vérifier que l'enrichissement est activé
    if not config.enabled:
        print("⚠️  L'enrichissement est désactivé dans config.ini")
        print("💡 Activez-le avec: enabled = true dans la section [ENRICHMENT]")
        sys.exit(0)
    
    # Valider la configuration
    print("✔️  Validation de la configuration...")
    is_valid, errors = config.validate()
    if not is_valid:
        print("❌ Configuration invalide:")
        for error in errors:
            print(f"   • {error}")
        sys.exit(1)
    print("✅ Configuration valide")
    print()
    
    # Vérifier le modèle
    print("🔍 Vérification du modèle LLM...")
    if not check_model(config):
        sys.exit(1)
    print()
    
    # Vérifier la base de données
    print("🔍 Vérification de la base de données...")
    if not check_database():
        sys.exit(1)
    print()
    
    # Configurer le logging
    log_dir = Path(config.log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    setup_logging(
        log_level=config.log_level,
        log_file=config.log_file
    )
    
    logger = logging.getLogger(__name__)
    
    # Afficher les paramètres
    print("📋 Paramètres:")
    print(f"   • Modèle: {Path(config.model_path).name}")
    print(f"   • Threads: {config.n_threads}")
    print(f"   • Contexte: {config.n_ctx} tokens")
    print(f"   • Intervalle: {config.poll_interval_seconds}s")
    print(f"   • Batch: {config.batch_size} transcriptions")
    print(f"   • Logs: {config.log_file}")
    print()
    
    # Afficher les fonctionnalités activées
    features = []
    if config.generate_title:
        features.append("Titre")
    if config.generate_summary:
        features.append("Résumé")
    if config.generate_bullets:
        features.append("Points clés")
    if config.generate_sentiment:
        features.append("Sentiment")
    if config.generate_topics:
        features.append("Topics")
    
    print(f"✨ Fonctionnalités: {', '.join(features)}")
    print()
    
    # Demander confirmation
    print("="*60)
    response = input("Démarrer le worker? (Y/n): ")
    if response.lower() == 'n':
        print("❌ Annulé")
        sys.exit(0)
    print("="*60)
    print()
    
    # Créer et démarrer le worker
    try:
        logger.info("="*60)
        logger.info("🎨 Démarrage du worker d'enrichissement")
        logger.info("="*60)
        
        worker = EnrichmentWorker(config)
        worker.start()
        
    except KeyboardInterrupt:
        print("\n\n⌨️  Interruption par l'utilisateur")
        logger.info("⌨️  Arrêt demandé par l'utilisateur")
    except Exception as e:
        print(f"\n\n❌ Erreur fatale: {e}")
        logger.exception("❌ Erreur fatale")
        sys.exit(1)
    finally:
        print("\n✅ Worker arrêté proprement\n")


if __name__ == "__main__":
    main()