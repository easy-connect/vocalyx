"""
enrichment_service.py

Service complet d'enrichissement : API + Worker automatique
Architecture identique à app.py (transcription)
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
    Worker automatique qui enrichit les transcriptions terminées.
    Tourne en arrière-plan et utilise l'executor du moteur.
    """
    from database import SessionLocal, Transcription
    from enrichment.models import Enrichment, get_pending_enrichments
    from enrichment.engine import run_enrichment_async
    from sqlalchemy import and_
    
    logger.info("🚀 Worker automatique d'enrichissement démarré")
    
    while True:
        try:
            # Récupérer les transcriptions à enrichir
            db = SessionLocal()
            
            # Sous-requête pour les IDs déjà enrichis
            subquery = db.query(Enrichment.transcription_id).filter(
                Enrichment.status.in_(['done', 'processing', 'pending'])
            )
            
            transcriptions = (
                db.query(Transcription)
                .filter(
                    and_(
                        Transcription.status == 'done',
                        Transcription.enrichment_requested == 1,
                        ~Transcription.id.in_(subquery)
                    )
                )
                .limit(enrichment_config.batch_size if enrichment_config else 3)
                .all()
            )
            
            db.close()
            
            if transcriptions:
                logger.info(f"📊 {len(transcriptions)} transcription(s) à enrichir")
                
                # Lancer les enrichissements en parallèle (non-bloquant)
                tasks = []
                for trans in transcriptions:
                    task = asyncio.create_task(run_enrichment_async(trans.id))
                    tasks.append(task)
                
                # Attendre que tous soient terminés
                await asyncio.gather(*tasks, return_exceptions=True)
            
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
    version="1.0.0",
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
        "version": "1.0.0",
        "status": "running",
        "architecture": "API + Worker automatique (comme transcription)",
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