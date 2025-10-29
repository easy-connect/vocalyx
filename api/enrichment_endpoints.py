"""
API REST pour l'enrichissement des transcriptions
Endpoints pour déclencher et suivre l'enrichissement
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from database import Transcription, SessionLocal
from enrichment.models import (
    Enrichment, 
    create_enrichment,
    get_enrichment_by_transcription_id,
    get_pending_enrichments,
    get_stats_summary
)
from api.dependencies import get_db

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/enrichment", tags=["Enrichment"])


# ========================================
# Modèles Pydantic pour les réponses
# ========================================

from pydantic import BaseModel

class EnrichmentResponse(BaseModel):
    """Réponse d'enrichissement"""
    id: int
    transcription_id: str
    status: str
    title: Optional[str] = None
    summary: Optional[str] = None
    bullets: Optional[list] = None
    sentiment: Optional[str] = None
    sentiment_confidence: Optional[float] = None
    topics: Optional[list] = None
    model_used: Optional[str] = None
    generation_time: Optional[float] = None
    tokens_generated: Optional[int] = None
    retry_count: int
    last_error: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None

class EnrichmentCreateResponse(BaseModel):
    """Réponse de création d'enrichissement"""
    enrichment_id: int
    transcription_id: str
    status: str
    message: str

class EnrichmentStatsResponse(BaseModel):
    """Réponse des statistiques"""
    total: int
    pending: int
    processing: int
    done: int
    error: int
    avg_generation_time: Optional[float] = None
    avg_tokens_generated: Optional[int] = None
    avg_sentiment_confidence: Optional[float] = None


# ========================================
# Endpoints
# ========================================

@router.post("/trigger/{transcription_id}", response_model=EnrichmentCreateResponse)
@limiter.limit("10/minute")
async def trigger_enrichment(
    transcription_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Déclenche l'enrichissement d'une transcription
    
    - **transcription_id**: ID de la transcription à enrichir
    
    Retourne l'ID et le statut de l'enrichissement créé
    """
    
    # 1. Vérifier que la transcription existe
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id
    ).first()
    
    if not transcription:
        raise HTTPException(
            status_code=404,
            detail=f"Transcription not found: {transcription_id}"
        )
    
    # 2. Vérifier que la transcription est terminée
    if transcription.status != "done":
        raise HTTPException(
            status_code=400,
            detail=f"Transcription must be 'done' (current: {transcription.status})"
        )
    
    # 3. Vérifier qu'il n'y a pas déjà un enrichissement en cours ou terminé
    existing = get_enrichment_by_transcription_id(db, transcription_id)
    
    if existing:
        # Si déjà en pending/processing, retourner l'existant
        if existing.status in ["pending", "processing"]:
            return EnrichmentCreateResponse(
                enrichment_id=existing.id,
                transcription_id=transcription_id,
                status=existing.status,
                message=f"Enrichment already {existing.status}"
            )
        
        # Si terminé avec succès, ne pas recréer
        if existing.status == "done":
            return EnrichmentCreateResponse(
                enrichment_id=existing.id,
                transcription_id=transcription_id,
                status="done",
                message="Enrichment already completed"
            )
        
        # Si erreur, on peut retenter (mettre à jour le retry_count)
        if existing.status == "error":
            existing.status = "pending"
            existing.retry_count += 1
            existing.last_error = None
            db.commit()
            db.refresh(existing)
            
            logger.info(
                f"[{transcription_id[:8]}] Retry enrichment "
                f"(attempt {existing.retry_count})"
            )
            
            return EnrichmentCreateResponse(
                enrichment_id=existing.id,
                transcription_id=transcription_id,
                status="pending",
                message=f"Retry enrichment (attempt {existing.retry_count})"
            )
    
    # 4. Créer un nouvel enrichissement
    enrichment = create_enrichment(db, transcription_id)
    
    if not enrichment:
        raise HTTPException(
            status_code=500,
            detail="Failed to create enrichment"
        )
    
    logger.info(f"[{transcription_id[:8]}] 🎨 Enrichment triggered: {enrichment.id}")
    
    return EnrichmentCreateResponse(
        enrichment_id=enrichment.id,
        transcription_id=transcription_id,
        status="pending",
        message="Enrichment queued successfully"
    )


@router.get("/{transcription_id}", response_model=EnrichmentResponse)
async def get_enrichment(
    transcription_id: str,
    db: Session = Depends(get_db)
):
    """
    Récupère l'enrichissement d'une transcription
    
    - **transcription_id**: ID de la transcription
    
    Retourne le détail de l'enrichissement ou 404 si non trouvé
    """
    
    enrichment = get_enrichment_by_transcription_id(db, transcription_id)
    
    if not enrichment:
        raise HTTPException(
            status_code=404,
            detail=f"No enrichment found for transcription: {transcription_id}"
        )
    
    return EnrichmentResponse(
        id=enrichment.id,
        transcription_id=enrichment.transcription_id,
        status=enrichment.status,
        title=enrichment.title,
        summary=enrichment.summary,
        bullets=enrichment.bullets,
        sentiment=enrichment.sentiment,
        sentiment_confidence=enrichment.sentiment_confidence,
        topics=enrichment.topics,
        model_used=enrichment.model_used,
        generation_time=enrichment.generation_time,
        tokens_generated=enrichment.tokens_generated,
        retry_count=enrichment.retry_count,
        last_error=enrichment.last_error,
        created_at=enrichment.created_at.isoformat() if enrichment.created_at else None,
        started_at=enrichment.started_at.isoformat() if enrichment.started_at else None,
        finished_at=enrichment.finished_at.isoformat() if enrichment.finished_at else None
    )


@router.get("/pending/list", response_model=List[EnrichmentResponse])
async def list_pending_enrichments(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Liste les enrichissements en attente
    
    - **limit**: Nombre maximum d'enrichissements à retourner
    """
    
    enrichments = get_pending_enrichments(db, limit=limit)
    
    return [
        EnrichmentResponse(
            id=e.id,
            transcription_id=e.transcription_id,
            status=e.status,
            title=e.title,
            summary=e.summary,
            bullets=e.bullets,
            sentiment=e.sentiment,
            sentiment_confidence=e.sentiment_confidence,
            topics=e.topics,
            model_used=e.model_used,
            generation_time=e.generation_time,
            tokens_generated=e.tokens_generated,
            retry_count=e.retry_count,
            last_error=e.last_error,
            created_at=e.created_at.isoformat() if e.created_at else None,
            started_at=e.started_at.isoformat() if e.started_at else None,
            finished_at=e.finished_at.isoformat() if e.finished_at else None
        )
        for e in enrichments
    ]


@router.get("/stats/summary", response_model=EnrichmentStatsResponse)
async def get_enrichment_stats(db: Session = Depends(get_db)):
    """
    Récupère les statistiques globales des enrichissements
    
    Retourne le nombre d'enrichissements par statut et les moyennes
    """
    
    stats = get_stats_summary(db)
    
    return EnrichmentStatsResponse(
        total=stats.get("total", 0),
        pending=stats.get("pending", 0),
        processing=stats.get("processing", 0),
        done=stats.get("done", 0),
        error=stats.get("error", 0),
        avg_generation_time=stats.get("avg_generation_time"),
        avg_tokens_generated=stats.get("avg_tokens_generated"),
        avg_sentiment_confidence=stats.get("avg_sentiment_confidence")
    )


@router.delete("/{transcription_id}")
async def delete_enrichment(
    transcription_id: str,
    db: Session = Depends(get_db)
):
    """
    Supprime l'enrichissement d'une transcription
    
    - **transcription_id**: ID de la transcription
    
    Utile pour retenter un enrichissement ou nettoyer
    """
    
    enrichment = get_enrichment_by_transcription_id(db, transcription_id)
    
    if not enrichment:
        raise HTTPException(
            status_code=404,
            detail=f"No enrichment found for transcription: {transcription_id}"
        )
    
    db.delete(enrichment)
    db.commit()
    
    logger.info(f"[{transcription_id[:8]}] 🗑️  Enrichment deleted: {enrichment.id}")
    
    return {
        "status": "deleted",
        "enrichment_id": enrichment.id,
        "transcription_id": transcription_id
    }


@router.post("/retry/{transcription_id}")
@limiter.limit("5/minute")
async def retry_enrichment(
    transcription_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Retente un enrichissement en erreur
    
    - **transcription_id**: ID de la transcription
    
    Équivalent à supprimer puis recréer, mais garde l'historique des tentatives
    """
    
    enrichment = get_enrichment_by_transcription_id(db, transcription_id)
    
    if not enrichment:
        raise HTTPException(
            status_code=404,
            detail=f"No enrichment found for transcription: {transcription_id}"
        )
    
    if enrichment.status not in ["error", "done"]:
        raise HTTPException(
            status_code=400,
            detail=f"Can only retry 'error' or 'done' enrichments (current: {enrichment.status})"
        )
    
    # Reset vers pending
    enrichment.status = "pending"
    enrichment.retry_count += 1
    enrichment.last_error = None
    enrichment.started_at = None
    enrichment.finished_at = None
    
    db.commit()
    db.refresh(enrichment)
    
    logger.info(
        f"[{transcription_id[:8]}] 🔄 Enrichment retry: {enrichment.id} "
        f"(attempt {enrichment.retry_count})"
    )
    
    return {
        "status": "pending",
        "enrichment_id": enrichment.id,
        "transcription_id": transcription_id,
        "retry_count": enrichment.retry_count,
        "message": f"Retry queued (attempt {enrichment.retry_count})"
    }


# ========================================
# Endpoint combiné (Transcription + Enrichissement)
# ========================================

@router.get("/combined/{transcription_id}")
async def get_transcription_with_enrichment(
    transcription_id: str,
    db: Session = Depends(get_db)
):
    """
    Récupère la transcription ET son enrichissement en une seule requête
    
    - **transcription_id**: ID de la transcription
    
    Pratique pour le dashboard
    """
    
    # Récupérer la transcription
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id
    ).first()
    
    if not transcription:
        raise HTTPException(
            status_code=404,
            detail=f"Transcription not found: {transcription_id}"
        )
    
    # Récupérer l'enrichissement (optionnel)
    enrichment = get_enrichment_by_transcription_id(db, transcription_id)
    
    # Construire la réponse
    response = {
        "transcription": {
            "id": transcription.id,
            "status": transcription.status,
            "language": transcription.language,
            "duration": float(transcription.duration) if transcription.duration else None,
            "processing_time": float(transcription.processing_time) if transcription.processing_time else None,
            "text": transcription.text,
            "segments_count": transcription.segments_count,
            "vad_enabled": bool(transcription.vad_enabled),
            "created_at": transcription.created_at.isoformat() if transcription.created_at else None,
            "finished_at": transcription.finished_at.isoformat() if transcription.finished_at else None
        },
        "enrichment": None
    }
    
    if enrichment:
        response["enrichment"] = {
            "id": enrichment.id,
            "status": enrichment.status,
            "title": enrichment.title,
            "summary": enrichment.summary,
            "bullets": enrichment.bullets,
            "sentiment": enrichment.sentiment,
            "sentiment_confidence": enrichment.sentiment_confidence,
            "topics": enrichment.topics,
            "model_used": enrichment.model_used,
            "generation_time": enrichment.generation_time,
            "tokens_generated": enrichment.tokens_generated,
            "created_at": enrichment.created_at.isoformat() if enrichment.created_at else None,
            "finished_at": enrichment.finished_at.isoformat() if enrichment.finished_at else None
        }
    
    return response