"""
enrichment/worker.py

Worker de traitement d'enrichissement des transcriptions.
Interroge la base de données pour trouver les transcriptions à enrichir,
génère le contenu enrichi via le LLM et met à jour la base.
"""

import logging
import time
import signal
import sys
from datetime import datetime
from typing import Optional, List

from sqlalchemy import and_
from sqlalchemy.orm import Session

from database import SessionLocal, Transcription
from enrichment.config import EnrichmentConfig
from enrichment.models import Enrichment, create_enrichment
from enrichment.processors import create_processor_from_config, TranscriptionProcessor
from enrichment.llm_engine import GenerationConfig

logger = logging.getLogger(__name__)


class EnrichmentWorker:
    """
    Worker pour traiter les enrichissements de transcriptions.
    
    Cycle de vie:
    1. Polling: Récupère les transcriptions terminées sans enrichissement
    2. Processing: Génère titre, résumé, points clés, sentiment
    3. Persistence: Sauvegarde dans la table enrichments
    4. Retry: Gère les échecs avec retry automatique
    """
    
    def __init__(self, config: EnrichmentConfig):
        """
        Args:
            config: Configuration d'enrichissement
        """
        self.config = config
        self.processor: Optional[TranscriptionProcessor] = None
        self.running = False
        self.processed_count = 0
        self.success_count = 0
        self.error_count = 0
        
        # Configuration de la génération
        self.gen_config = GenerationConfig(
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            top_p=config.top_p,
            top_k=config.top_k,
            repeat_penalty=config.repeat_penalty
        )
        
        logger.info(f"✨ EnrichmentWorker initialisé: {config}")

    async def process_transcription_async(self, transcription: Transcription):
        """
        Version asynchrone de _process_transcription.
        Utilise run_in_executor pour ne pas bloquer.
        """
        import asyncio
        loop = asyncio.get_event_loop()
        
        # Exécuter le traitement dans un thread séparé
        await loop.run_in_executor(
            None,  # Utilise le default executor
            self._process_transcription,
            transcription
        )
    
    def start(self):
        """Démarre le worker"""
        if not self.config.enabled:
            logger.warning("⚠️  Enrichissement désactivé dans la config")
            return
        
        try:
            # Charger le processeur (modèle LLM)
            logger.info("🔄 Chargement du processeur LLM...")
            self.processor = create_processor_from_config(self.config)
            logger.info("✅ Processeur LLM chargé avec succès")
            
            # Setup signal handlers
            signal.signal(signal.SIGINT, self._handle_shutdown)
            signal.signal(signal.SIGTERM, self._handle_shutdown)
            
            # Démarrer la boucle principale
            self.running = True
            logger.info("🚀 Worker démarré - En attente de transcriptions...")
            self._main_loop()
            
        except FileNotFoundError as e:
            logger.error(f"❌ Modèle LLM non trouvé: {e}")
            logger.error("💡 Téléchargez-le avec: make download-model")
            sys.exit(1)
        except Exception as e:
            logger.exception(f"❌ Erreur fatale au démarrage: {e}")
            sys.exit(1)
    
    def stop(self):
        """Arrête le worker proprement"""
        logger.info("🛑 Arrêt du worker...")
        self.running = False
    
    def _handle_shutdown(self, signum, frame):
        """Handler pour les signaux de shutdown"""
        logger.info(f"📡 Signal reçu: {signum}")
        self.stop()
    
    def _main_loop(self):
        """Boucle principale du worker"""
        while self.running:
            try:
                # Récupérer les transcriptions à enrichir
                transcriptions = self._get_pending_transcriptions()
                
                if not transcriptions:
                    # Pas de travail, attendre
                    time.sleep(self.config.poll_interval_seconds)
                    continue
                
                logger.info(f"📊 {len(transcriptions)} transcription(s) à enrichir")
                
                # Traiter chaque transcription
                for trans in transcriptions:
                    if not self.running:
                        break
                    
                    self._process_transcription(trans)
                
                # Afficher les stats
                self._log_stats()
                
            except KeyboardInterrupt:
                logger.info("⌨️  Interruption clavier")
                break
            except Exception as e:
                logger.exception(f"❌ Erreur dans la boucle principale: {e}")
                time.sleep(5)  # Attendre avant de retenter
        
        logger.info("✅ Worker arrêté")
        self._log_final_stats()
    
    def _get_pending_transcriptions(self) -> List[Transcription]:
        """
        Récupère les transcriptions terminées qui nécessitent un enrichissement.
        
        Returns:
            Liste de transcriptions
        """
        db = SessionLocal()
        try:
            # Requête pour trouver les transcriptions:
            # - status = 'done'
            # - enrichment_requested = 1
            # - pas encore d'enrichissement OU enrichissement en erreur
            
            # Sous-requête pour les IDs déjà enrichis (sauf erreurs)
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
                .order_by(Transcription.finished_at.desc())
                .limit(self.config.batch_size)
                .all()
            )
            
            return transcriptions
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération des transcriptions: {e}")
            return []
        finally:
            db.close()
    
    def _process_transcription(self, transcription: Transcription):
        """
        Traite une transcription: génère l'enrichissement et le sauvegarde.
        
        Args:
            transcription: Transcription à enrichir
        """
        trans_id = transcription.id[:8]
        db = SessionLocal()
        
        try:
            logger.info(f"[{trans_id}] 🎨 Début enrichissement")
            
            # Créer l'entrée enrichment
            enrichment = create_enrichment(db, transcription.id)
            if not enrichment:
                logger.error(f"[{trans_id}] ❌ Impossible de créer l'enrichissement")
                return
            
            # Marquer comme en cours
            enrichment.status = 'processing'
            enrichment.started_at = datetime.utcnow()
            db.commit()
            
            # Vérifier qu'on a du texte
            if not transcription.text or len(transcription.text.strip()) < self.config.min_transcription_chars:
                raise ValueError(
                    f"Texte trop court: {len(transcription.text) if transcription.text else 0} chars"
                )
            
            # Générer l'enrichissement
            logger.debug(f"[{trans_id}] 📝 Génération du contenu enrichi...")
            result = self.processor.process(
                text=transcription.text,
                method="all_in_one",  # Plus rapide
                config=self.gen_config
            )
            
            if not result.success:
                raise RuntimeError(f"Échec génération: {result.error_message}")
            
            # Sauvegarder les résultats
            enrichment.status = 'done'
            enrichment.title = result.title
            enrichment.summary = result.summary
            enrichment.bullets = result.bullets
            enrichment.sentiment = result.sentiment
            enrichment.sentiment_confidence = result.sentiment_confidence
            enrichment.topics = result.topics
            enrichment.llm_model = result.llm_model
            enrichment.generation_time = result.generation_time
            enrichment.tokens_generated = result.tokens_generated
            enrichment.finished_at = datetime.utcnow()
            
            db.commit()
            
            self.success_count += 1
            self.processed_count += 1
            
            logger.info(
                f"[{trans_id}] ✅ Enrichissement terminé | "
                f"Titre: \"{result.title[:40]}...\" | "
                f"Sentiment: {result.sentiment} | "
                f"Temps: {result.generation_time}s"
            )
            
        except Exception as e:
            logger.exception(f"[{trans_id}] ❌ Erreur lors de l'enrichissement: {e}")
            
            # Marquer comme erreur
            try:
                enrichment = db.query(Enrichment).filter(
                    Enrichment.transcription_id == transcription.id
                ).first()
                
                if enrichment:
                    enrichment.status = 'error'
                    enrichment.last_error = str(e)
                    enrichment.retry_count += 1
                    enrichment.finished_at = datetime.utcnow()
                    db.commit()
            except Exception as e2:
                logger.error(f"[{trans_id}] ❌ Erreur lors de la mise à jour de l'erreur: {e2}")
            
            self.error_count += 1
            self.processed_count += 1
            
        finally:
            db.close()
    
    def _log_stats(self):
        """Affiche les statistiques du worker"""
        if self.processed_count > 0 and self.processed_count % 5 == 0:
            success_rate = (self.success_count / self.processed_count) * 100
            logger.info(
                f"📊 Stats: {self.processed_count} traités | "
                f"{self.success_count} succès | "
                f"{self.error_count} erreurs | "
                f"Taux: {success_rate:.1f}%"
            )
    
    def _log_final_stats(self):
        """Affiche les statistiques finales"""
        logger.info("=" * 60)
        logger.info("📊 STATISTIQUES FINALES")
        logger.info("=" * 60)
        logger.info(f"Total traité:     {self.processed_count}")
        logger.info(f"Succès:          {self.success_count}")
        logger.info(f"Erreurs:         {self.error_count}")
        if self.processed_count > 0:
            success_rate = (self.success_count / self.processed_count) * 100
            logger.info(f"Taux de succès:  {success_rate:.1f}%")
        logger.info("=" * 60)


def test_enrichment():
    """
    Test simple pour vérifier que l'enrichissement fonctionne.
    Crée une transcription de test et l'enrichit.
    """
    import uuid
    from database import Base, engine
    
    # Créer les tables si nécessaire
    Base.metadata.create_all(bind=engine)
    from enrichment.models import create_tables
    create_tables()
    
    # Créer une transcription de test
    db = SessionLocal()
    test_id = str(uuid.uuid4())
    
    test_text = """
    Bonjour, je vous appelle car j'ai un problème avec ma commande.
    J'ai commandé un produit il y a une semaine et je ne l'ai toujours pas reçu.
    Le numéro de commande est ABC123.
    Pouvez-vous vérifier où en est ma livraison ?
    J'aimerais vraiment recevoir mon colis rapidement car c'est urgent.
    Merci de votre aide.
    """
    
    transcription = Transcription(
        id=test_id,
        status='done',
        language='fr',
        text=test_text,
        duration=30.0,
        processing_time=3.0,
        enrichment_requested=1,
        created_at=datetime.utcnow(),
        finished_at=datetime.utcnow()
    )
    
    db.add(transcription)
    db.commit()
    
    logger.info(f"✅ Transcription de test créée: {test_id}")
    
    # Créer et tester le worker
    config = EnrichmentConfig()
    config.batch_size = 1
    config.poll_interval_seconds = 1
    
    worker = EnrichmentWorker(config)
    
    # Traiter une fois
    transcriptions = worker._get_pending_transcriptions()
    if transcriptions:
        logger.info(f"📊 {len(transcriptions)} transcription(s) trouvée(s)")
        worker._process_transcription(transcriptions[0])
        
        # Vérifier le résultat
        enrichment = db.query(Enrichment).filter(
            Enrichment.transcription_id == test_id
        ).first()
        
        if enrichment and enrichment.status == 'done':
            logger.info("=" * 60)
            logger.info("✅ TEST RÉUSSI - Enrichissement généré:")
            logger.info("=" * 60)
            logger.info(f"Titre:   {enrichment.title}")
            logger.info(f"Résumé:  {enrichment.summary}")
            logger.info(f"Points:  {enrichment.bullets}")
            logger.info(f"Sentiment: {enrichment.sentiment} ({enrichment.sentiment_confidence})")
            logger.info("=" * 60)
        else:
            logger.error("❌ TEST ÉCHOUÉ - Enrichissement non créé")
    else:
        logger.warning("⚠️  Aucune transcription à traiter")
    
    # Nettoyer
    db.delete(transcription)
    if enrichment:
        db.delete(enrichment)
    db.commit()
    db.close()
    
    logger.info("🧹 Nettoyage terminé")


def main():
    """Point d'entrée principal du worker"""
    from logging_config import setup_logging
    
    # Charger la config
    config = EnrichmentConfig()
    
    # Configurer les logs
    setup_logging(
        log_level=config.log_level,
        log_file=config.log_file
    )
    
    logger.info("=" * 60)
    logger.info("🎨 Vocalyx Enrichment Worker")
    logger.info("=" * 60)
    
    # Valider la config
    is_valid, errors = config.validate()
    if not is_valid:
        logger.error("❌ Configuration invalide:")
        for error in errors:
            logger.error(f"  - {error}")
        sys.exit(1)
    
    logger.info("✅ Configuration validée")
    logger.info(f"📁 Modèle: {config.model_path}")
    logger.info(f"⏱️  Intervalle: {config.poll_interval_seconds}s")
    logger.info(f"📦 Batch: {config.batch_size}")
    logger.info("=" * 60)
    
    # Créer et démarrer le worker
    worker = EnrichmentWorker(config)
    worker.start()


if __name__ == "__main__":
    main()