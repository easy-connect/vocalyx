"""
Service d'Enrichissement Vocalyx - API Dédiée
Port par défaut: 8001

Service séparé pour l'enrichissement, permet scalabilité indépendante
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn

from config import Config
from database import engine, Base
from api.enrichment_endpoints import router as enrichment_router
from logging_config import setup_logging, get_uvicorn_log_config

# Initialiser la configuration
config = Config()

# Configurer le logging
logger = setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file="logs/enrichment_api.log"
)

# Créer les tables si nécessaire
Base.metadata.create_all(bind=engine)

# Initialiser le limiteur de taux
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("🎨 Démarrage du service d'enrichissement")
    
    # Vérifier que le module d'enrichissement est configuré
    try:
        from enrichment.config import EnrichmentConfig
        enrich_config = EnrichmentConfig()
        
        if not enrich_config.enabled:
            logger.warning("⚠️  Enrichissement désactivé dans config.ini")
        else:
            logger.info(f"✅ Enrichissement activé (modèle: {enrich_config.model_path})")
    except Exception as e:
        logger.warning(f"⚠️  Impossible de charger la config d'enrichissement: {e}")
    
    yield  # --- App runs here ---
    
    # --- Shutdown ---
    logger.info("🛑 Arrêt du service d'enrichissement")

# Créer l'application FastAPI
app = FastAPI(
    title="Vocalyx Enrichment API",
    description="Service d'enrichissement de transcriptions via LLM",
    version="1.0.0",
    contact={"name": "Guilhem RICHARD", "email": "guilhem.l.richard@gmail.com"},
    lifespan=lifespan
)

# CORS - Permettre aux services de transcription d'appeler ce service
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",  # Service transcription local
        "http://transcription:8000",  # Service transcription Docker
        os.getenv("TRANSCRIPTION_SERVICE_URL", "*")  # Configurable
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurer le limiteur de taux
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Inclure les routes d'enrichissement
app.include_router(enrichment_router, prefix="/api")


# ========================================
# Endpoints de base (health, config)
# ========================================

@app.get("/", tags=["Root"])
def root():
    """Page d'accueil du service d'enrichissement"""
    return {
        "service": "Vocalyx Enrichment API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "config": "/config",
            "trigger": "/api/enrichment/trigger/{transcription_id}",
            "get": "/api/enrichment/{transcription_id}",
            "stats": "/api/enrichment/stats/summary"
        }
    }


@app.get("/health", tags=["System"])
def health_check():
    """Health check du service"""
    from enrichment.config import EnrichmentConfig
    from enrichment.models import get_stats_summary
    from database import SessionLocal
    
    status = "healthy"
    issues = []
    
    # Vérifier la config
    try:
        enrich_config = EnrichmentConfig()
        if not enrich_config.enabled:
            issues.append("Enrichment disabled in config")
            status = "degraded"
    except Exception as e:
        issues.append(f"Config error: {str(e)}")
        status = "unhealthy"
    
    # Vérifier la DB
    try:
        db = SessionLocal()
        stats = get_stats_summary(db)
        db.close()
    except Exception as e:
        issues.append(f"Database error: {str(e)}")
        status = "unhealthy"
    
    return {
        "status": status,
        "service": "enrichment",
        "timestamp": datetime.utcnow().isoformat(),
        "issues": issues if issues else None
    }


@app.get("/config", tags=["System"])
def get_config():
    """Configuration du service d'enrichissement"""
    from enrichment.config import EnrichmentConfig
    
    try:
        config = EnrichmentConfig()
        return config.to_dict()
    except Exception as e:
        return {
            "error": f"Failed to load config: {str(e)}"
        }


@app.get("/stats", tags=["System"])
def get_service_stats():
    """Statistiques du service"""
    from enrichment.models import get_stats_summary
    from database import SessionLocal
    
    db = SessionLocal()
    try:
        stats = get_stats_summary(db)
        return {
            "service": "enrichment",
            "enrichments": stats
        }
    finally:
        db.close()


# ========================================
# Gestion des erreurs
# ========================================

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handler personnalisé pour les erreurs HTTP"""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handler pour les erreurs non gérées"""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# ========================================
# Point d'entrée
# ========================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Vocalyx Enrichment Service")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8001, help="Port to bind")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()
    
    log_config = get_uvicorn_log_config(
        log_level=os.getenv("LOG_LEVEL", "INFO")
    )
    
    logger.info(f"🚀 Starting Enrichment Service on {args.host}:{args.port}")
    
    uvicorn.run(
        "app_enrichment:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_config=log_config
    )