"""
enrichment_service.py - VERSION PROFESSIONNELLE
Architecture sans variables globales, avec injection de dépendances
"""

import os
import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from database import engine, Base
from api.enrichment_endpoints import router as enrichment_router
from logging_config import setup_logging, get_uvicorn_log_config

# ✅ Import des dépendances
from enrichment.dependencies import get_enrichment_config
from enrichment.engine import get_engine_state, EnrichmentEngineState
from enrichment.config import EnrichmentConfig

logger = setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file="logs/enrichment.log"
)

Base.metadata.create_all(bind=engine)


class ServiceState:
    """État du service (remplace les variables globales)"""
    
    def __init__(self):
        self.worker_task: asyncio.Task = None
        self.is_running = False


# Instance d'état (locale au module, mais bien encapsulée)
service_state = ServiceState()


async def auto_enrichment_worker(
    config: EnrichmentConfig,
    engine_state: EnrichmentEngineState
):
    """
    Worker automatique - VERSION SANS GLOBALES
    
    Args:
        config: Configuration passée explicitement
        engine_state: État du moteur passé explicitement
    """
    from database import SessionLocal
    from enrichment.models import Enrichment
    from enrichment.engine import run_enrichment_async
    
    logger.info(f"🚀 Worker démarré (batch={config.batch_size}, interval={config.poll_interval_seconds}s)")
    
    while service_state.is_running:
        try:
            db = SessionLocal()
            
            pending = (
                db.query(Enrichment)
                .filter(Enrichment.status == 'pending')
                .order_by(Enrichment.created_at.asc())
                .limit(config.batch_size)
                .all()
            )
            
            db.close()
            
            if pending:
                logger.info(f"📊 {len(pending)} enrichissement(s) en attente")
                
                tasks = [
                    asyncio.create_task(run_enrichment_async(e.transcription_id))
                    for e in pending
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"❌ Erreur #{i+1}: {result}")
            
            await asyncio.sleep(config.poll_interval_seconds)
            
        except asyncio.CancelledError:
            logger.info("✅ Worker arrêté")
            raise
        except Exception as e:
            logger.exception(f"❌ Erreur worker: {e}")
            await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan - VERSION SANS GLOBALES
    Tout est passé explicitement, rien n'est global
    """
    logger.info("=" * 60)
    logger.info("🎨 Démarrage service enrichissement")
    logger.info("=" * 60)
    
    # ✅ Récupérer les dépendances localement
    config = get_enrichment_config()
    engine_state = get_engine_state()
    
    # Initialiser le moteur
    await engine_state.initialize(config)
    
    # Démarrer le worker si enabled
    if config.enabled:
        logger.info("🔄 Démarrage worker automatique...")
        service_state.is_running = True
        
        # ✅ Passer les dépendances explicitement au worker
        service_state.worker_task = asyncio.create_task(
            auto_enrichment_worker(config, engine_state)
        )
        
        logger.info("✅ Worker démarré")
    
    logger.info("=" * 60)
    
    yield  # --- Service running ---
    
    # --- Shutdown ---
    logger.info("🛑 Arrêt service")
    
    # Arrêter le worker
    service_state.is_running = False
    
    if service_state.worker_task and not service_state.worker_task.done():
        logger.info("🛑 Arrêt worker...")
        service_state.worker_task.cancel()
        try:
            await service_state.worker_task
        except asyncio.CancelledError:
            pass
    
    # Nettoyer le moteur
    await engine_state.cleanup()
    
    logger.info("✅ Service arrêté")


# ============================================
# APPLICATION FASTAPI
# ============================================

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Vocalyx Enrichment Service",
    description="Service sans variables globales (Clean Architecture)",
    version="1.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.include_router(enrichment_router, prefix="/api")


@app.get("/", tags=["Root"])
def root():
    """Page d'accueil"""
    return {
        "service": "Vocalyx Enrichment Service",
        "version": "1.1.0",
        "architecture": "Clean (No Global Variables)",
        "status": "running" if service_state.is_running else "stopped",
    }


@app.get("/health", tags=["System"])
def health_check(
    config: EnrichmentConfig = Depends(get_enrichment_config)  # ✅ Injection
):
    """Health check avec injection de dépendances"""
    from enrichment.engine import get_engine_state
    from enrichment.models import get_stats_summary
    from database import SessionLocal
    
    engine_state = get_engine_state()
    
    status = "healthy"
    issues = []
    
    if not engine_state.is_initialized:
        issues.append("Engine not initialized")
        status = "degraded"
    
    if not service_state.is_running:
        issues.append("Worker not running")
        status = "degraded"
    
    db = SessionLocal()
    stats = get_stats_summary(db)
    db.close()
    
    return {
        "status": status,
        "service": "enrichment",
        "version": "1.1.0",
        "components": {
            "api": "running",
            "engine": "initialized" if engine_state.is_initialized else "not initialized",
            "worker": "running" if service_state.is_running else "stopped",
        },
        "config": {
            "enabled": config.enabled,
            "model": config.model_path,
            "batch_size": config.batch_size,
            "poll_interval": config.poll_interval_seconds
        },
        "stats": stats,
        "issues": issues if issues else None,
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    
    uvicorn.run(
        "enrichment_service:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_config=get_uvicorn_log_config()
    )