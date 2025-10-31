"""
enrichment_service.py - VERSION CORRIGÉE

Service complet d'enrichissement : API + Worker automatique
FIX: Le worker traite maintenant les enrichissements en status 'pending'
"""

import os
import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime

# Configuration logs llama-cpp
os.environ['LLAMA_CPP_LOG_LEVEL'] = '3'
import warnings
warnings.filterwarnings('ignore', category=RuntimeWarning, module='llama_cpp')

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn

from database import engine, Base
from api.enrichment_endpoints import router as enrichment_router
from logging_config import setup_logging, get_uvicorn_log_config

# Import du nouveau moteur
from enrichment.engine import (
    initialize_enrichment_engine,
    cleanup_enrichment_resources,
    enrichment_config
)

# Initialiser le logging
logger = setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file="logs/enrichment.log"
)

# Créer les tables
Base.metadata.create_all(bind=engine)

# Variable pour le worker automatique
worker_task = None


async def auto_enrichment_worker():
    """
    Worker automatique qui enrichit les transcriptions.
    
    FIX: Maintenant traite les enrichissements en status 'pending'
    au lieu de chercher uniquement les transcriptions sans enrichissement.
    """
    from database import SessionLocal, Transcription
    from enrichment.models import Enrichment, get_pending_enrichments
    from enrichment.engine import run_enrichment_async
    
    logger.info("🚀 Worker automatique d'enrichissement démarré")
    
    while True:
        try:
            db = SessionLocal()
            
            # ✅ FIX: Récupérer les enrichissements en status 'pending'
            # au lieu de chercher les transcriptions sans enrichissement
            pending_enrichments = (
                db.query(Enrichment)
                .filter(Enrichment.status == 'pending')
                .order_by(Enrichment.created_at.asc())
                .limit(enrichment_config.batch_size if enrichment_config else 3)
                .all()
            )
            
            db.close()
            
            if pending_enrichments:
                logger.info(f"📊 {len(pending_enrichments)} enrichissement(s) en attente")
                
                # Lancer les enrichissements en parallèle
                tasks = []
                for enrichment in pending_enrichments:
                    transcription_id = enrichment.transcription_id
                    logger.info(f"[{transcription_id[:8]}] 🎨 Lancement enrichissement #{enrichment.id}")
                    
                    task = asyncio.create_task(run_enrichment_async(transcription_id))
                    tasks.append(task)
                
                # Attendre que tous soient terminés
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Logger les erreurs éventuelles
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"❌ Erreur enrichissement #{i+1}: {result}")
            
            # Attendre avant le prochain cycle
            poll_interval = enrichment_config.poll_interval_seconds if enrichment_config else 15
            await asyncio.sleep(poll_interval)
            
        except asyncio.CancelledError:
            logger.info("✅ Worker automatique arrêté")
            raise
        except Exception as e:
            logger.exception(f"❌ Erreur dans le worker automatique: {e}")
            await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    global worker_task
    
    logger.info("=" * 60)
    logger.info("🎨 Démarrage du service d'enrichissement")
    logger.info("=" * 60)
    
    # Initialiser le moteur (processeur + executor)
    await initialize_enrichment_engine()
    
    # Démarrer le worker automatique
    if enrichment_config and enrichment_config.enabled:
        logger.info("🔄 Démarrage du worker automatique...")
        worker_task = asyncio.create_task(auto_enrichment_worker())
        logger.info("✅ Worker automatique démarré")
    
    logger.info("=" * 60)
    
    yield  # --- App runs here ---
    
    # --- Shutdown ---
    logger.info("🛑 Arrêt du service d'enrichissement")
    
    # Arrêter le worker
    if worker_task and not worker_task.done():
        logger.info("🛑 Arrêt du worker automatique...")
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
    
    # Nettoyer le moteur
    await cleanup_enrichment_resources()
    
    logger.info("✅ Service arrêté proprement")


# Créer l'application FastAPI
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Vocalyx Enrichment Service",
    description="Service d'enrichissement avec worker automatique intégré",
    version="1.0.1",  # Bump version
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://transcription:8000",
        os.getenv("TRANSCRIPTION_SERVICE_URL", "*")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Inclure les routes
app.include_router(enrichment_router, prefix="/api")


# Endpoints de base
@app.get("/", tags=["Root"])
def root():
    """Page d'accueil"""
    return {
        "service": "Vocalyx Enrichment Service",
        "version": "1.0.1",
        "status": "running",
        "fix": "Worker traite maintenant les enrichissements pending",
        "architecture": "API + Worker automatique",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "trigger": "/api/enrichment/trigger/{transcription_id}",
            "stats": "/api/enrichment/stats/summary"
        }
    }


@app.get("/health", tags=["System"])
def health_check():
    """Health check"""
    from enrichment.engine import enrichment_processor, enrichment_executor
    from enrichment.models import get_stats_summary
    from database import SessionLocal
    
    status = "healthy"
    issues = []
    
    # Vérifier le moteur
    if enrichment_processor is None:
        issues.append("Enrichment engine not loaded")
        status = "degraded"
    
    if enrichment_executor is None:
        issues.append("Executor not initialized")
        status = "degraded"
    
    # Vérifier le worker
    global worker_task
    if worker_task is None or worker_task.done():
        issues.append("Auto worker not running")
        status = "degraded"
    
    # Stats DB
    try:
        db = SessionLocal()
        stats = get_stats_summary(db)
        db.close()
    except Exception as e:
        issues.append(f"Database error: {str(e)}")
        status = "unhealthy"
        stats = None
    
    return {
        "status": status,
        "service": "enrichment",
        "version": "1.0.1",
        "components": {
            "api": "running",
            "engine": "loaded" if enrichment_processor else "not loaded",
            "executor": "running" if enrichment_executor else "not running",
            "auto_worker": "running" if worker_task and not worker_task.done() else "stopped"
        },
        "stats": stats,
        "timestamp": datetime.utcnow().isoformat(),
        "issues": issues if issues else None
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Vocalyx Enrichment Service")
    parser.add_argument("--host", default="0.0.0.0", help="Host")
    parser.add_argument("--port", type=int, default=8001, help="Port")
    parser.add_argument("--reload", action="store_true", help="Auto-reload")
    args = parser.parse_args()
    
    log_config = get_uvicorn_log_config(log_level=os.getenv("LOG_LEVEL", "INFO"))
    
    logger.info(f"🚀 Starting Enrichment Service on {args.host}:{args.port}")
    
    uvicorn.run(
        "enrichment_service:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_config=log_config
    )