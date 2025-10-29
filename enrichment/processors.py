"""
enrichment/processors.py

Processeurs pour enrichir les transcriptions via LLM.
Gère la génération de titre, résumé, points clés et sentiment.
"""

import logging
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass

from enrichment.llm_engine import LLMEngine, GenerationConfig, GenerationResult
from enrichment.prompts import PromptBuilder
from enrichment.utils import (
    truncate_text, 
    clean_generated_text,
    parse_bullets_from_text,
    normalize_sentiment
)

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentResult:
    """Résultat d'un enrichissement"""
    success: bool
    title: Optional[str] = None
    summary: Optional[str] = None
    bullets: Optional[list] = None
    sentiment: Optional[str] = None
    sentiment_confidence: Optional[float] = None
    topics: Optional[list] = None
    
    # Métadonnées
    generation_time: Optional[float] = None
    tokens_generated: Optional[int] = None
    llm_model: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            "success": self.success,
            "title": self.title,
            "summary": self.summary,
            "bullets": self.bullets,
            "sentiment": self.sentiment,
            "sentiment_confidence": self.sentiment_confidence,
            "topics": self.topics,
            "generation_time": self.generation_time,
            "tokens_generated": self.tokens_generated,
            "llm_model": self.llm_model,
            "error_message": self.error_message
        }


class TranscriptionProcessor:
    """
    Processeur principal pour enrichir les transcriptions.
    Utilise le LLMEngine pour générer le contenu enrichi.
    """
    
    def __init__(
        self,
        llm_engine: LLMEngine,
        prompt_builder: PromptBuilder,
        max_text_length: int = 15000,
        min_text_length: int = 100
    ):
        """
        Args:
            llm_engine: Instance du moteur LLM
            prompt_builder: Builder de prompts
            max_text_length: Longueur max du texte à traiter
            min_text_length: Longueur min du texte à traiter
        """
        self.llm = llm_engine
        self.prompt_builder = prompt_builder
        self.max_text_length = max_text_length
        self.min_text_length = min_text_length
    
    def can_process(self, text: str) -> tuple[bool, str]:
        """
        Vérifie si le texte peut être traité.
        
        Returns:
            (can_process, reason)
        """
        if not text or not text.strip():
            return False, "Texte vide"
        
        text_len = len(text.strip())
        
        if text_len < self.min_text_length:
            return False, f"Texte trop court ({text_len} < {self.min_text_length})"
        
        if text_len > self.max_text_length:
            logger.warning(
                f"Texte long ({text_len} chars), sera tronqué à {self.max_text_length}"
            )
        
        return True, "OK"
    
    def process_all_in_one(
        self,
        text: str,
        config: Optional[GenerationConfig] = None
    ) -> EnrichmentResult:
        """
        Génère tous les enrichissements en une seule passe.
        Plus rapide mais moins flexible.
        
        Args:
            text: Texte de la transcription
            config: Configuration de génération
            
        Returns:
            EnrichmentResult
        """
        start_time = time.time()
        
        # Vérifier si traitable
        can_process, reason = self.can_process(text)
        if not can_process:
            return EnrichmentResult(
                success=False,
                error_message=reason
            )
        
        # Tronquer si nécessaire
        text = truncate_text(text, self.max_text_length)
        
        # Construire le prompt
        prompt = self.prompt_builder.build_all_in_one(text)
        
        # Générer
        logger.info("📝 Génération all-in-one...")
        result = self.llm.generate(prompt, config)
        
        if not result:
            return EnrichmentResult(
                success=False,
                error_message="Échec de génération LLM"
            )
        
        # Parser la réponse JSON
        data = self.llm.extract_json(result.text)
        
        if not data:
            logger.warning("⚠️  Pas de JSON valide, tentative de parsing manuel")
            return self._fallback_parsing(text, result, start_time)
        
        # Valider les clés
        required_keys = ["titre", "resume", "points_cles", "sentiment"]
        if not self.llm.validate_json_response(data, required_keys):
            logger.warning("⚠️  JSON incomplet, tentative de parsing manuel")
            return self._fallback_parsing(text, result, start_time)
        
        # Extraire et nettoyer
        generation_time = time.time() - start_time
        
        return EnrichmentResult(
            success=True,
            title=clean_generated_text(data.get("titre", "")),
            summary=clean_generated_text(data.get("resume", "")),
            bullets=data.get("points_cles", [])[:5],  # Max 5 points
            sentiment=normalize_sentiment(data.get("sentiment", "neutre")),
            sentiment_confidence=float(data.get("confiance", 0.0)),
            generation_time=round(generation_time, 2),
            tokens_generated=result.tokens_generated,
            llm_model=self.llm.model_info.get("name", "unknown")
        )
    
    def process_step_by_step(
        self,
        text: str,
        config: Optional[GenerationConfig] = None
    ) -> EnrichmentResult:
        """
        Génère les enrichissements en plusieurs étapes.
        Plus lent mais plus robuste.
        
        Args:
            text: Texte de la transcription
            config: Configuration de génération
            
        Returns:
            EnrichmentResult
        """
        start_time = time.time()
        
        # Vérifier si traitable
        can_process, reason = self.can_process(text)
        if not can_process:
            return EnrichmentResult(
                success=False,
                error_message=reason
            )
        
        # Tronquer si nécessaire
        text = truncate_text(text, self.max_text_length)
        
        total_tokens = 0
        errors = []
        
        # 1. Titre
        logger.debug("📝 Génération du titre...")
        title = None
        try:
            prompt = self.prompt_builder.build_title(text)
            result = self.llm.generate(prompt, config)
            if result:
                title = clean_generated_text(result.text)
                total_tokens += result.tokens_generated
        except Exception as e:
            logger.error(f"Erreur génération titre: {e}")
            errors.append(f"Titre: {e}")
        
        # 2. Résumé
        logger.debug("📝 Génération du résumé...")
        summary = None
        try:
            prompt = self.prompt_builder.build_summary(text)
            result = self.llm.generate(prompt, config)
            if result:
                summary = clean_generated_text(result.text)
                total_tokens += result.tokens_generated
        except Exception as e:
            logger.error(f"Erreur génération résumé: {e}")
            errors.append(f"Résumé: {e}")
        
        # 3. Points clés
        logger.debug("📝 Génération des points clés...")
        bullets = None
        try:
            prompt = self.prompt_builder.build_bullets(text)
            result = self.llm.generate(prompt, config)
            if result:
                bullets = parse_bullets_from_text(result.text)[:5]
                total_tokens += result.tokens_generated
        except Exception as e:
            logger.error(f"Erreur génération bullets: {e}")
            errors.append(f"Bullets: {e}")
        
        # 4. Sentiment
        logger.debug("📝 Analyse du sentiment...")
        sentiment = "neutre"
        sentiment_confidence = 0.5
        try:
            prompt = self.prompt_builder.build_sentiment(text)
            result = self.llm.generate(prompt, config)
            if result:
                sentiment_text = clean_generated_text(result.text)
                sentiment = normalize_sentiment(sentiment_text)
                # Confidence basique selon le texte
                if "très" in sentiment_text.lower():
                    sentiment_confidence = 0.9
                elif "assez" in sentiment_text.lower():
                    sentiment_confidence = 0.7
                else:
                    sentiment_confidence = 0.5
                total_tokens += result.tokens_generated
        except Exception as e:
            logger.error(f"Erreur analyse sentiment: {e}")
            errors.append(f"Sentiment: {e}")
        
        generation_time = time.time() - start_time
        
        # Vérifier qu'on a au moins quelque chose
        if not any([title, summary, bullets]):
            return EnrichmentResult(
                success=False,
                error_message=f"Aucun enrichissement généré. Erreurs: {'; '.join(errors)}"
            )
        
        return EnrichmentResult(
            success=True,
            title=title,
            summary=summary,
            bullets=bullets,
            sentiment=sentiment,
            sentiment_confidence=sentiment_confidence,
            generation_time=round(generation_time, 2),
            tokens_generated=total_tokens,
            llm_model=self.llm.model_info.get("name", "unknown"),
            error_message="; ".join(errors) if errors else None
        )
    
    def _fallback_parsing(
        self,
        text: str,
        generation_result: GenerationResult,
        start_time: float
    ) -> EnrichmentResult:
        """
        Parsing de secours quand le JSON n'est pas valide.
        Tente d'extraire ce qu'on peut du texte brut.
        """
        logger.info("🔧 Utilisation du parsing de secours...")
        
        generated_text = generation_result.text
        lines = [l.strip() for l in generated_text.split('\n') if l.strip()]
        
        title = None
        summary = None
        bullets = []
        sentiment = "neutre"
        
        # Chercher le titre (première ligne courte)
        for line in lines[:3]:
            if len(line) < 100 and not line.startswith('-'):
                title = clean_generated_text(line)
                break
        
        # Chercher le résumé (texte plus long)
        for line in lines:
            if len(line) > 50 and not line.startswith('-'):
                summary = clean_generated_text(line)
                break
        
        # Chercher les bullets
        for line in lines:
            if line.startswith('-') or line.startswith('•'):
                bullet = line.lstrip('-•').strip()
                if bullet:
                    bullets.append(clean_generated_text(bullet))
        
        # Chercher le sentiment
        sentiment_words = {
            'positif': ['positif', 'satisfait', 'content', 'heureux'],
            'negatif': ['negatif', 'insatisfait', 'mécontent', 'problème'],
            'neutre': ['neutre', 'objectif'],
            'mixte': ['mixte', 'mitigé']
        }
        
        for sent, keywords in sentiment_words.items():
            if any(kw in generated_text.lower() for kw in keywords):
                sentiment = sent
                break
        
        generation_time = time.time() - start_time
        
        return EnrichmentResult(
            success=True,
            title=title or "Transcription",
            summary=summary or "Résumé non disponible",
            bullets=bullets[:5] if bullets else ["Pas de points clés extraits"],
            sentiment=sentiment,
            sentiment_confidence=0.3,  # Faible confiance
            generation_time=round(generation_time, 2),
            tokens_generated=generation_result.tokens_generated,
            llm_model=self.llm.model_info.get("name", "unknown"),
            error_message="Parsing de secours utilisé"
        )
    
    def process(
        self,
        text: str,
        method: str = "all_in_one",
        config: Optional[GenerationConfig] = None
    ) -> EnrichmentResult:
        """
        Point d'entrée principal pour traiter une transcription.
        
        Args:
            text: Texte à enrichir
            method: "all_in_one" ou "step_by_step"
            config: Configuration de génération
            
        Returns:
            EnrichmentResult
        """
        if method == "step_by_step":
            return self.process_step_by_step(text, config)
        else:
            return self.process_all_in_one(text, config)


# Factory pour créer un processeur
def create_processor_from_config(config) -> TranscriptionProcessor:
    """
    Crée un processeur depuis la configuration.
    
    Args:
        config: Objet EnrichmentConfig
        
    Returns:
        TranscriptionProcessor configuré
    """
    from enrichment.llm_engine import create_llm_engine_from_config
    
    # Créer le moteur LLM
    llm_engine = create_llm_engine_from_config(config)
    
    # Charger le modèle
    if not llm_engine.load():
        raise RuntimeError("Impossible de charger le modèle LLM")
    
    # Créer le prompt builder
    prompt_builder = PromptBuilder(model_type=config.model_type)
    
    # Créer le processeur
    processor = TranscriptionProcessor(
        llm_engine=llm_engine,
        prompt_builder=prompt_builder,
        max_text_length=config.max_transcription_chars,
        min_text_length=config.min_transcription_chars
    )
    
    return processor


# Script de test
if __name__ == "__main__":
    """Test du processeur"""
    
    import logging
    from enrichment.config import EnrichmentConfig
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    print("\n" + "="*60)
    print("TEST: Processeur d'enrichissement")
    print("="*60 + "\n")
    
    # Charger la config
    config = EnrichmentConfig()
    
    # Texte de test
    test_text = """
    Bonjour, je vous appelle car j'ai un problème avec ma commande.
    J'ai commandé un produit il y a une semaine et je ne l'ai toujours pas reçu.
    Le numéro de commande est ABC123.
    Pouvez-vous vérifier où en est ma livraison ?
    J'aimerais vraiment recevoir mon colis rapidement car c'est urgent.
    Merci de votre aide.
    """
    
    try:
        # Créer le processeur
        print("1. Création du processeur...")
        processor = create_processor_from_config(config)
        print(f"   ✅ Processeur créé avec modèle: {processor.llm.model_info['name']}\n")
        
        # Vérifier si traitable
        print("2. Vérification du texte...")
        can_process, reason = processor.can_process(test_text)
        print(f"   {'✅' if can_process else '❌'} {reason}\n")
        
        if can_process:
            # Test all-in-one
            print("3. Test all-in-one...")
            result = processor.process(test_text, method="all_in_one")
            
            if result.success:
                print(f"   ✅ Succès !")
                print(f"   Titre: {result.title}")
                print(f"   Résumé: {result.summary}")
                print(f"   Points clés: {result.bullets}")
                print(f"   Sentiment: {result.sentiment} ({result.sentiment_confidence})")
                print(f"   Temps: {result.generation_time}s")
                print(f"   Tokens: {result.tokens_generated}\n")
            else:
                print(f"   ❌ Échec: {result.error_message}\n")
        
    except FileNotFoundError:
        print("❌ Modèle LLM non trouvé. Téléchargez-le avec: make download-model\n")
    except Exception as e:
        print(f"❌ Erreur: {e}\n")
        import traceback
        traceback.print_exc()
    
    print("="*60)
    print("Test terminé")
    print("="*60 + "\n")