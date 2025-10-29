"""
enrichment_service.py

Service complet d'enrichissement : API + Worker en un seul processus
Équivalent de app.py mais pour l'enrichissement uniquement
"""

import os
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from database import engine, Base
from api.enrichment_endpoints import router as enrichment_router
from logging_config import setup_logging, get_uvicorn_log_config

# Initialiser le logging
logger = setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file="logs/enrichment.log"
)

# Créer les tables si nécessaire
Base.metadata.create_all(bind=engine)

# Variable globale pour le worker
worker_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    global worker_task
    
    logger.info("=" * 60)
    logger.info("🎨 Démarrage du service d'enrichissement complet")
    logger.info("=" * 60)
    
    # Charger et valider la config
    from enrichment.config import EnrichmentConfig
    config = EnrichmentConfig()
    
    if not config.enabled:
        logger.warning("⚠️  Enrichissement désactivé dans config.ini")
    else:
        logger.info(f"✅ Config chargée: {config.model_path}")
        
        # Valider
        is_valid, errors = config.validate()
        if not is_valid:
            logger.error("❌ Configuration invalide:")
            for error in errors:
                logger.error(f"   • {error}")
        else:
            logger.info("✅ Configuration validée")
            
            # Démarrer le worker en background
            logger.info("🔄 Démarrage du worker d'enrichissement...")
            worker_task = asyncio.create_task(run_worker(config))
            logger.info("✅ Worker démarré en arrière-plan")
    
    logger.info("=" * 60)
    
    yield  # --- App runs here ---
    
    # --- Shutdown ---
    logger.info("🛑 Arrêt du service d'enrichissement")
    
    # Arrêter le worker
    if worker_task and not worker_task.done():
        logger.info("🛑 Arrêt du worker...")
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            logger.info("✅ Worker arrêté")


async def run_worker(config):
    """
    Worker d'enrichissement qui tourne en continu.
    Équivalent de run_enrichment.py mais en async.
    """
    from enrichment.worker import EnrichmentWorker
    
    try:
        worker = EnrichmentWorker(config)
        
        # Boucle principale
        while True:
            try:
                # Récupérer transcriptions à enrichir
                transcriptions = worker._get_pending_transcriptions()
                
                if transcriptions:
                    logger.info(f"📊 {len(transcriptions)} transcription(s) à enrichir")
                    
                    # Traiter chaque transcription
                    for trans in transcriptions:
                        worker._process_transcription(trans)
                    
                    # Log stats
                    worker._log_stats()
                
                # Attendre avant le prochain cycle
                await asyncio.sleep(config.poll_interval_seconds)
                
            except Exception as e:
                logger.exception(f"❌ Erreur dans le worker: {e}")
                await asyncio.sleep(5)  # Attendre avant de retenter
        
    except asyncio.CancelledError:
        logger.info("✅ Worker arrêté proprement")
        raise
    except Exception as e:
        logger.exception(f"❌ Erreur fatale dans le worker: {e}")


# Créer l'application FastAPI
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Vocalyx Enrichment Service",
    description="Service complet d'enrichissement (API + Worker)",
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


# ========================================
# Endpoints de base
# ========================================

@app.get("/", tags=["Root"])
def root():
    """Page d'accueil"""
    return {
        "service": "Vocalyx Enrichment Service (API + Worker)",
        "version": "1.0.0",
        "status": "running",
        "components": ["API", "Background Worker"],
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "trigger": "/api/enrichment/trigger/{transcription_id}",
            "get": "/api/enrichment/{transcription_id}",
            "stats": "/api/enrichment/stats/summary"
        }
    }


@app.get("/health", tags=["System"])
def health_check():
    """Health check"""
    from enrichment.config import EnrichmentConfig
    from enrichment.models import get_stats_summary
    from database import SessionLocal
    from datetime import datetime
    
    status = "healthy"
    issues = []
    
    # Vérifier config
    try:
        config = EnrichmentConfig()
        if not config.enabled:
            issues.append("Enrichment disabled in config")
            status = "degraded"
    except Exception as e:
        issues.append(f"Config error: {str(e)}")
        status = "unhealthy"
    
    # Vérifier DB
    try:
        db = SessionLocal()
        stats = get_stats_summary(db)
        db.close()
    except Exception as e:
        issues.append(f"Database error: {str(e)}")
        status = "unhealthy"
    
    # Vérifier worker
    global worker_task
    if worker_task is None or worker_task.done():
        issues.append("Worker not running")
        status = "degraded"
    
    return {
        "status": status,
        "service": "enrichment",
        "components": {
            "api": "running",
            "worker": "running" if worker_task and not worker_task.done() else "stopped"
        },
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