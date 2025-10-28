"""
enrichment/models.py

Modèles de données pour le module d'enrichissement.
Gère la table des enrichissements dans la base de données.
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Text, Integer, 
    DateTime, ForeignKey, JSON, Boolean
)
from sqlalchemy.orm import relationship

from database import Base, engine
import logging

logger = logging.getLogger(__name__)


class Enrichment(Base):
    """
    Modèle pour stocker les enrichissements de transcriptions.
    
    Chaque transcription peut avoir un enrichissement associé qui contient:
    - Un titre généré
    - Un résumé
    - Des points clés
    - Une analyse de sentiment
    - Des topics extraits (optionnel)
    """
    __tablename__ = "enrichments"
    
    # Clé primaire
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    
    # Relation avec la transcription
    transcription_id = Column(
        String, 
        ForeignKey("transcriptions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    
    # Statut de l'enrichissement
    status = Column(
        String,
        default="pending",
        nullable=False,
        index=True
    )
    # Valeurs possibles: pending, processing, done, error
    
    # Contenu enrichi
    title = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    bullets = Column(JSON, nullable=True)  # Liste de strings
    sentiment = Column(String, nullable=True)  # positif, negatif, neutre, mixte
    sentiment_confidence = Column(Float, nullable=True)
    topics = Column(JSON, nullable=True)  # Liste de topics (optionnel)
    
    # Métadonnées de génération
    model_used = Column(String, nullable=True)  # Ex: "mistral-7b-instruct-v0.3"
    generation_time = Column(Float, nullable=True)  # Temps total en secondes
    tokens_generated = Column(Integer, nullable=True)  # Nombre de tokens générés
    
    # Informations sur les tentatives
    retry_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    
    # Relation inverse (optionnelle, pour faciliter les requêtes)
    # transcription = relationship("Transcription", back_populates="enrichment")
    
    def __repr__(self):
        return f"<Enrichment(id={self.id}, transcription_id={self.transcription_id[:8]}..., status={self.status})>"
    
    def to_dict(self):
        """Convertit l'enrichissement en dictionnaire"""
        return {
            "id": self.id,
            "transcription_id": self.transcription_id,
            "status": self.status,
            "title": self.title,
            "summary": self.summary,
            "bullets": self.bullets,
            "sentiment": self.sentiment,
            "sentiment_confidence": self.sentiment_confidence,
            "topics": self.topics,
            "model_used": self.model_used,
            "generation_time": self.generation_time,
            "tokens_generated": self.tokens_generated,
            "retry_count": self.retry_count,
            "last_error": self.last_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }
    
    @property
    def is_complete(self) -> bool:
        """Vérifie si l'enrichissement est complet"""
        return self.status == "done" and all([
            self.title,
            self.summary,
            self.bullets,
            self.sentiment
        ])
    
    @property
    def processing_duration(self) -> float:
        """Calcule la durée de traitement"""
        if self.started_at and self.finished_at:
            delta = self.finished_at - self.started_at
            return round(delta.total_seconds(), 2)
        return 0.0


class EnrichmentStats(Base):
    """
    Table optionnelle pour stocker des statistiques d'enrichissement.
    Utile pour monitoring et analytics.
    """
    __tablename__ = "enrichment_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Compteurs quotidiens
    total_processed = Column(Integer, default=0)
    total_succeeded = Column(Integer, default=0)
    total_failed = Column(Integer, default=0)
    
    # Performances
    avg_generation_time = Column(Float, nullable=True)
    avg_tokens_generated = Column(Integer, nullable=True)
    
    # Qualité
    avg_sentiment_confidence = Column(Float, nullable=True)
    
    def __repr__(self):
        return f"<EnrichmentStats(date={self.date.date()}, processed={self.total_processed})>"


class EnrichmentQueue(Base):
    """
    File d'attente pour gérer les priorités d'enrichissement.
    Optionnel mais utile pour gérer la charge.
    """
    __tablename__ = "enrichment_queue"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    transcription_id = Column(
        String,
        ForeignKey("transcriptions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    
    priority = Column(Integer, default=0)  # Plus élevé = plus prioritaire
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    locked_at = Column(DateTime, nullable=True)  # Pour éviter le traitement concurrent
    locked_by = Column(String, nullable=True)  # Worker ID
    
    def __repr__(self):
        return f"<EnrichmentQueue(id={self.id}, priority={self.priority})>"


def create_tables():
    """
    Crée les tables d'enrichissement dans la base de données.
    À appeler lors de l'initialisation du module.
    """
    try:
        logger.info("🗄️  Création des tables d'enrichissement...")
        Base.metadata.create_all(bind=engine, tables=[
            Enrichment.__table__,
            EnrichmentStats.__table__,
            EnrichmentQueue.__table__
        ])
        logger.info("✅ Tables d'enrichissement créées avec succès")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur lors de la création des tables: {e}")
        return False


def drop_tables():
    """
    Supprime les tables d'enrichissement.
    ⚠️ À utiliser avec précaution !
    """
    try:
        logger.warning("🗑️  Suppression des tables d'enrichissement...")
        Base.metadata.drop_all(bind=engine, tables=[
            Enrichment.__table__,
            EnrichmentStats.__table__,
            EnrichmentQueue.__table__
        ])
        logger.info("✅ Tables supprimées")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur lors de la suppression: {e}")
        return False


# Fonctions utilitaires pour les requêtes courantes

def get_pending_enrichments(session, limit=10):
    """
    Récupère les enrichissements en attente.
    
    Args:
        session: Session SQLAlchemy
        limit: Nombre maximum d'enrichissements à récupérer
        
    Returns:
        Liste d'objets Enrichment
    """
    return (
        session.query(Enrichment)
        .filter(Enrichment.status == "pending")
        .order_by(Enrichment.created_at.asc())
        .limit(limit)
        .all()
    )


def get_enrichment_by_transcription_id(session, transcription_id: str):
    """
    Récupère l'enrichissement d'une transcription spécifique.
    
    Args:
        session: Session SQLAlchemy
        transcription_id: ID de la transcription
        
    Returns:
        Enrichment ou None
    """
    return (
        session.query(Enrichment)
        .filter(Enrichment.transcription_id == transcription_id)
        .first()
    )


def create_enrichment(session, transcription_id: str):
    """
    Crée un nouvel enrichissement pour une transcription.
    
    Args:
        session: Session SQLAlchemy
        transcription_id: ID de la transcription
        
    Returns:
        Enrichment créé ou None si erreur
    """
    try:
        # Vérifier qu'il n'existe pas déjà
        existing = get_enrichment_by_transcription_id(session, transcription_id)
        if existing:
            logger.warning(f"Enrichissement déjà existant pour {transcription_id}")
            return existing
        
        enrichment = Enrichment(
            transcription_id=transcription_id,
            status="pending",
            created_at=datetime.utcnow()
        )
        session.add(enrichment)
        session.commit()
        session.refresh(enrichment)
        
        logger.info(f"✅ Enrichissement créé: {enrichment.id} pour {transcription_id}")
        return enrichment
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Erreur création enrichissement: {e}")
        return None


def get_stats_summary(session):
    """
    Récupère un résumé des statistiques d'enrichissement.
    
    Args:
        session: Session SQLAlchemy
        
    Returns:
        Dictionnaire de statistiques
    """
    from sqlalchemy import func
    
    total = session.query(Enrichment).count()
    
    stats = {
        "total": total,
        "pending": session.query(Enrichment).filter(
            Enrichment.status == "pending"
        ).count(),
        "processing": session.query(Enrichment).filter(
            Enrichment.status == "processing"
        ).count(),
        "done": session.query(Enrichment).filter(
            Enrichment.status == "done"
        ).count(),
        "error": session.query(Enrichment).filter(
            Enrichment.status == "error"
        ).count(),
    }
    
    # Moyennes pour les enrichissements réussis
    if stats["done"] > 0:
        result = session.query(
            func.avg(Enrichment.generation_time).label("avg_time"),
            func.avg(Enrichment.tokens_generated).label("avg_tokens"),
            func.avg(Enrichment.sentiment_confidence).label("avg_confidence")
        ).filter(
            Enrichment.status == "done"
        ).first()
        
        stats["avg_generation_time"] = round(result.avg_time, 2) if result.avg_time else None
        stats["avg_tokens_generated"] = int(result.avg_tokens) if result.avg_tokens else None
        stats["avg_sentiment_confidence"] = round(result.avg_confidence, 2) if result.avg_confidence else None
    
    return stats


# Script de test
if __name__ == "__main__":
    """Script de test pour créer les tables et vérifier le modèle"""
    
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    print("\n" + "="*60)
    print("TEST: Modèles d'enrichissement")
    print("="*60 + "\n")
    
    # Créer les tables
    print("1. Création des tables...")
    if create_tables():
        print("   ✅ Tables créées\n")
    else:
        print("   ❌ Échec\n")
        exit(1)
    
    # Test d'insertion
    print("2. Test d'insertion...")
    from database import SessionLocal
    
    session = SessionLocal()
    
    try:
        # Créer un enrichissement test
        test_enrichment = Enrichment(
            transcription_id="test-uuid-12345",
            status="pending"
        )
        session.add(test_enrichment)
        session.commit()
        session.refresh(test_enrichment)
        
        print(f"   ✅ Enrichissement créé: {test_enrichment}")
        print(f"   ID: {test_enrichment.id}")
        print(f"   Dict: {test_enrichment.to_dict()}\n")
        
        # Test de récupération
        print("3. Test de récupération...")
        retrieved = get_enrichment_by_transcription_id(session, "test-uuid-12345")
        print(f"   ✅ Récupéré: {retrieved}\n")
        
        # Test des stats
        print("4. Test des statistiques...")
        stats = get_stats_summary(session)
        print(f"   ✅ Stats: {stats}\n")
        
        # Nettoyer
        print("5. Nettoyage...")
        session.delete(test_enrichment)
        session.commit()
        print("   ✅ Test nettoyé\n")
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}\n")
        session.rollback()
    finally:
        session.close()
    
    print("="*60)
    print("✅ Tests terminés avec succès !")
    print("="*60 + "\n")
    
    print("Pour utiliser ce module:")
    print("  1. make db-migrate  # Créer les tables")
    print("  2. python -c 'from enrichment.models import create_tables; create_tables()'")
    print("")