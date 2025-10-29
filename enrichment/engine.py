"""
Moteur d'enrichissement global avec ThreadPoolExecutor
Équivalent de transcribe/transcription.py
"""

import asyncio
import concurrent.futures
import gc
import logging
from typing import Optional

from enrichment.config import EnrichmentConfig
from enrichment.processors import create_processor_from_config
from enrichment.worker import EnrichmentWorker

logger = logging.getLogger(__name__)

# Variables globales
enrichment_processor = None
enrichment_executor = None
enrichment_config = None

async def initialize_enrichment_engine():
    """
    Initialise le moteur d'enrichissement (processeur LLM + executor).
    Équivalent de initialize_whisper_model() pour la transcription.
    """
    global enrichment_processor, enrichment_executor, enrichment_config
    
    logger.info("🎨 Initialisation du moteur d'enrichissement...")
    
    # Charger la config
    enrichment_config = EnrichmentConfig()
    
    if not enrichment_config.enabled:
        logger.warning("⚠️  Enrichissement désactivé dans config.ini")
        return
    
    # Valider la config
    is_valid, errors = enrichment_config.validate()
    if not is_valid:
        logger.error("❌ Configuration invalide:")
        for error in errors:
            logger.error(f"   • {error}")
        return
    
    logger.info(f"✅ Config validée: {enrichment_config.model_path}")
    
    # Charger le processeur LLM (dans un executor pour ne pas bloquer)
    loop = asyncio.get_event_loop()
    
    # Créer l'executor avec le nombre de workers configuré
    max_workers = getattr(enrichment_config, 'max_workers', 2)
    enrichment_executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=max_workers
    )
    
    logger.info(f"🔄 Chargement du processeur LLM ({max_workers} workers)...")
    
    # Charger le processeur dans l'executor
    enrichment_processor = await loop.run_in_executor(
        enrichment_executor,
        create_processor_from_config,
        enrichment_config
    )
    
    logger.info(
        f"✅ Moteur d'enrichissement prêt | "
        f"Modèle: {enrichment_processor.llm.model_info.get('name', 'unknown')} | "
        f"Workers: {max_workers}"
    )


async def cleanup_enrichment_resources():
    """Nettoie les ressources du moteur d'enrichissement"""
    global enrichment_processor, enrichment_executor
    
    try:
        logger.info("🛑 Arrêt du moteur d'enrichissement...")
        
        enrichment_processor = None
        gc.collect()

        if enrichment_executor:
            logger.info("🧹 Arrêt des workers d'enrichissement...")
            enrichment_executor.shutdown(wait=False, cancel_futures=True)
            enrichment_executor = None
            
        logger.info("✅ Moteur d'enrichissement arrêté")
        
    except Exception as e:
        logger.warning(f"⚠️ Erreur lors du nettoyage: {e}")


async def run_enrichment_async(transcription_id: str):
    """
    Lance l'enrichissement d'une transcription de manière asynchrone.
    Équivalent de run_transcription_optimized().
    """
    global enrichment_processor, enrichment_executor, enrichment_config
    
    if enrichment_processor is None:
        logger.error(f"[{transcription_id[:8]}] ❌ Moteur d'enrichissement non initialisé")
        return
    
    from database import SessionLocal, Transcription
    from enrichment.models import create_enrichment
    from datetime import datetime
    
    db = SessionLocal()
    
    try:
        # Créer l'entrée enrichment
        enrichment = create_enrichment(db, transcription_id)
        if not enrichment:
            logger.warning(f"[{transcription_id[:8]}] Enrichissement déjà existant")
            db.close()
            return
        
        # Marquer comme processing
        enrichment.status = 'processing'
        enrichment.started_at = datetime.utcnow()
        db.commit()
        db.close()
        
        # Récupérer la transcription
        db = SessionLocal()
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id
        ).first()
        
        if not transcription or not transcription.text:
            enrichment = db.query(Enrichment).filter(
                Enrichment.transcription_id == transcription_id
            ).first()
            enrichment.status = 'error'
            enrichment.last_error = 'No transcription text'
            enrichment.finished_at = datetime.utcnow()
            db.commit()
            db.close()
            return
        
        text = transcription.text
        db.close()
        
        logger.info(f"[{transcription_id[:8]}] 🎨 Enrichissement démarré...")
        
        # Exécuter le traitement dans l'executor (non-bloquant)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            enrichment_executor,
            enrichment_processor.process,
            text,
            "all_in_one",
            enrichment_processor.gen_config if hasattr(enrichment_processor, 'gen_config') else None
        )
        
        # Sauvegarder le résultat
        db = SessionLocal()
        enrichment = db.query(Enrichment).filter(
            Enrichment.transcription_id == transcription_id
        ).first()
        
        if result.success:
            enrichment.status = 'done'
            enrichment.title = result.title
            enrichment.summary = result.summary
            enrichment.bullets = result.bullets
            enrichment.sentiment = result.sentiment
            enrichment.sentiment_confidence = result.sentiment_confidence
            enrichment.topics = result.topics
            enrichment.llm_model = result.model_used
            enrichment.generation_time = result.generation_time
            enrichment.tokens_generated = result.tokens_generated
            
            logger.info(
                f"[{transcription_id[:8]}] ✅ Enrichissement terminé | "
                f"Titre: \"{result.title[:40]}...\" | "
                f"Sentiment: {result.sentiment} | "
                f"Temps: {result.generation_time}s"
            )
        else:
            enrichment.status = 'error'
            enrichment.last_error = result.error_message
            logger.error(f"[{transcription_id[:8]}] ❌ Échec: {result.error_message}")
        
        enrichment.finished_at = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        logger.exception(f"[{transcription_id[:8]}] ❌ Erreur: {e}")
        
        db = SessionLocal()
        enrichment = db.query(Enrichment).filter(
            Enrichment.transcription_id == transcription_id
        ).first()
        
        if enrichment:
            enrichment.status = 'error'
            enrichment.last_error = str(e)
            enrichment.finished_at = datetime.utcnow()
            db.commit()
        
    finally:
        db.close()