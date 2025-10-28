#!/usr/bin/env python3
"""
test_enrichment_module.py

Script de test complet pour le module d'enrichissement.
Teste tous les composants: config, LLM, processeur, worker.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
import uuid

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def print_section(title: str):
    """Affiche un titre de section"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def test_config():
    """Test 1: Configuration"""
    print_section("TEST 1: Configuration")
    
    try:
        from enrichment.config import EnrichmentConfig
        
        print("📝 Chargement de la configuration...")
        config = EnrichmentConfig()
        
        print(f"   ✅ Config chargée")
        print(f"   • Modèle: {config.model_path}")
        print(f"   • Threads: {config.n_threads}")
        print(f"   • Contexte: {config.n_ctx} tokens")
        print(f"   • Enabled: {config.enabled}")
        
        print("\n📝 Validation de la configuration...")
        is_valid, errors = config.validate()
        
        if is_valid:
            print("   ✅ Configuration valide")
        else:
            print("   ⚠️  Erreurs de configuration:")
            for error in errors:
                print(f"      • {error}")
        
        print("\n📝 Affichage de la config complète...")
        config_dict = config.to_dict()
        print(f"   • Sections: {list(config_dict.keys())}")
        
        return True, config
        
    except Exception as e:
        logger.exception(f"❌ Erreur: {e}")
        return False, None


def test_models():
    """Test 2: Modèles de base de données"""
    print_section("TEST 2: Modèles de base de données")
    
    try:
        from enrichment.models import (
            Enrichment, 
            create_tables, 
            get_pending_enrichments,
            create_enrichment
        )
        from database import SessionLocal
        
        print("📝 Création des tables...")
        if create_tables():
            print("   ✅ Tables créées")
        else:
            print("   ⚠️  Tables déjà existantes")
        
        print("\n📝 Test de création d'enrichissement...")
        db = SessionLocal()
        
        # Créer un enrichissement test
        test_id = str(uuid.uuid4())
        enrichment = create_enrichment(db, test_id)
        
        if enrichment:
            print(f"   ✅ Enrichissement créé: {enrichment.id}")
            print(f"   • Transcription ID: {enrichment.transcription_id[:8]}...")
            print(f"   • Status: {enrichment.status}")
            
            # Nettoyer
            db.delete(enrichment)
            db.commit()
            print("   ✅ Nettoyage effectué")
        else:
            print("   ❌ Échec création")
        
        db.close()
        return True
        
    except Exception as e:
        logger.exception(f"❌ Erreur: {e}")
        return False


def test_utils():
    """Test 3: Utilitaires"""
    print_section("TEST 3: Utilitaires")
    
    try:
        from enrichment.utils import (
            truncate_text,
            clean_generated_text,
            parse_bullets_from_text,
            normalize_sentiment,
            validate_enrichment_result,
            calculate_text_stats
        )
        
        print("📝 Test truncate_text...")
        long_text = "Ceci est un texte " * 50
        truncated = truncate_text(long_text, 50)
        print(f"   ✅ {len(long_text)} chars → {len(truncated)} chars")
        
        print("\n📝 Test clean_generated_text...")
        dirty = "<s>[INST] Texte à nettoyer [/INST]"
        clean = clean_generated_text(dirty)
        print(f"   ✅ '{dirty}' → '{clean}'")
        
        print("\n📝 Test parse_bullets_from_text...")
        bullets_text = "- Point 1\n- Point 2\n• Point 3"
        bullets = parse_bullets_from_text(bullets_text)
        print(f"   ✅ {len(bullets)} bullets extraits")
        
        print("\n📝 Test normalize_sentiment...")
        sentiments = [
            ("Le client est satisfait", "positif"),
            ("Problème majeur", "negatif"),
            ("Information neutre", "neutre")
        ]
        for text, expected in sentiments:
            result = normalize_sentiment(text)
            status = "✅" if result == expected else "❌"
            print(f"   {status} '{text[:30]}' → {result}")
        
        print("\n📝 Test validate_enrichment_result...")
        valid_result = {
            'title': 'Titre de test',
            'summary': 'Ceci est un résumé de test avec suffisamment de contenu.',
            'bullets': ['Point 1', 'Point 2', 'Point 3'],
            'sentiment': 'positif',
            'sentiment_confidence': 0.85
        }
        is_valid, errors = validate_enrichment_result(valid_result)
        if is_valid:
            print(f"   ✅ Validation réussie")
        else:
            print(f"   ❌ Erreurs: {errors}")
        
        print("\n📝 Test calculate_text_stats...")
        sample = "Ceci est un texte. Il contient des phrases."
        stats = calculate_text_stats(sample)
        print(f"   ✅ Stats: {stats['words']} mots, {stats['sentences']} phrases")
        
        return True
        
    except Exception as e:
        logger.exception(f"❌ Erreur: {e}")
        return False


def test_prompts():
    """Test 4: Templates de prompts"""
    print_section("TEST 4: Templates de prompts")
    
    try:
        from enrichment.prompts import PromptBuilder
        
        print("📝 Création du PromptBuilder...")
        builder = PromptBuilder(model_type="mistral")
        print("   ✅ PromptBuilder créé")
        
        test_text = "Le client appelle pour une réclamation."
        
        print("\n📝 Test build_title...")
        prompt = builder.build_title(test_text)
        print(f"   ✅ Prompt titre généré ({len(prompt)} chars)")
        
        print("\n📝 Test build_summary...")
        prompt = builder.build_summary(test_text)
        print(f"   ✅ Prompt résumé généré ({len(prompt)} chars)")
        
        print("\n📝 Test build_all_in_one...")
        prompt = builder.build_all_in_one(test_text)
        print(f"   ✅ Prompt complet généré ({len(prompt)} chars)")
        
        return True
        
    except Exception as e:
        logger.exception(f"❌ Erreur: {e}")
        return False


def test_llm_engine(config):
    """Test 5: Moteur LLM"""
    print_section("TEST 5: Moteur LLM")
    
    model_path = Path(config.model_path)
    
    if not model_path.exists():
        print(f"⚠️  Modèle non trouvé: {model_path}")
        print("💡 Téléchargez-le avec: make download-model")
        return False
    
    try:
        from enrichment.llm_engine import LLMEngine, GenerationConfig
        
        print("📝 Création du moteur LLM...")
        engine = LLMEngine(
            model_path=str(model_path),
            n_ctx=2048,
            n_threads=4,
            n_batch=512,
            verbose=False
        )
        print("   ✅ Moteur créé")
        
        print("\n📝 Chargement du modèle...")
        print("   ⏳ Ceci peut prendre 30-60 secondes...")
        if engine.load():
            print(f"   ✅ Modèle chargé: {engine.model_info['name']}")
            print(f"   • Taille: {engine.model_info['size_mb']:.0f}MB")
            print(f"   • Temps: {engine.model_info['load_time']}s")
        else:
            print("   ❌ Échec du chargement")
            return False
        
        print("\n📝 Test de génération simple...")
        prompt = "<s>[INST] Résume en 5 mots: Le chat dort sur le canapé. [/INST]"
        
        gen_config = GenerationConfig(
            max_tokens=50,
            temperature=0.3
        )
        
        result = engine.generate(prompt, gen_config)
        
        if result:
            print(f"   ✅ Génération réussie")
            print(f"   • Texte: \"{result.text}\"")
            print(f"   • Tokens: {result.tokens_generated}")
            print(f"   • Vitesse: {result.tokens_per_second} tok/s")
        else:
            print("   ❌ Échec de génération")
        
        print("\n📝 Test d'extraction JSON...")
        json_prompt = """<s>[INST] Réponds en JSON:
{"sentiment": "positif", "confiance": 0.9} [/INST]"""
        
        result = engine.generate(json_prompt, gen_config)
        if result:
            data = engine.extract_json(result.text)
            if data:
                print(f"   ✅ JSON extrait: {data}")
            else:
                print(f"   ⚠️  Pas de JSON trouvé dans: {result.text}")
        
        print("\n📝 Statistiques du moteur...")
        stats = engine.get_stats()
        print(f"   • Générations: {stats['total_generations']}")
        print(f"   • Tokens totaux: {stats['total_tokens_generated']}")
        print(f"   • Vitesse moyenne: {stats['avg_tokens_per_second']} tok/s")
        
        # Décharger
        print("\n📝 Déchargement du modèle...")
        engine.unload()
        print("   ✅ Modèle déchargé")
        
        return True
        
    except Exception as e:
        logger.exception(f"❌ Erreur: {e}")
        return False


def test_processor(config):
    """Test 6: Processeur de transcriptions"""
    print_section("TEST 6: Processeur de transcriptions")
    
    model_path = Path(config.model_path)
    
    if not model_path.exists():
        print(f"⚠️  Modèle non trouvé: {model_path}")
        return False
    
    try:
        from enrichment.processors import create_processor_from_config
        from enrichment.llm_engine import GenerationConfig
        
        print("📝 Création du processeur...")
        print("   ⏳ Chargement du modèle LLM...")
        processor = create_processor_from_config(config)
        print(f"   ✅ Processeur créé")
        
        test_text = """
        Bonjour, je vous appelle car j'ai un problème avec ma commande.
        J'ai commandé un produit il y a une semaine et je ne l'ai toujours pas reçu.
        Le numéro de commande est ABC123.
        Pouvez-vous vérifier où en est ma livraison ?
        J'aimerais vraiment recevoir mon colis rapidement car c'est urgent.
        Merci de votre aide.
        """
        
        print("\n📝 Test can_process...")
        can_process, reason = processor.can_process(test_text)
        print(f"   {'✅' if can_process else '❌'} {reason}")
        
        if can_process:
            print("\n📝 Test process_all_in_one...")
            print("   ⏳ Génération en cours (30-60s)...")
            
            gen_config = GenerationConfig(
                max_tokens=500,
                temperature=0.3
            )
            
            result = processor.process(
                text=test_text,
                method="all_in_one",
                config=gen_config
            )
            
            if result.success:
                print(f"   ✅ Enrichissement généré en {result.generation_time}s")
                print(f"\n   📌 Titre: \"{result.title}\"")
                print(f"\n   📝 Résumé: {result.summary}")
                print(f"\n   🔹 Points clés:")
                for i, bullet in enumerate(result.bullets or [], 1):
                    print(f"      {i}. {bullet}")
                print(f"\n   😊 Sentiment: {result.sentiment} ({result.sentiment_confidence:.0%})")
                print(f"\n   ⚡ Performance:")
                print(f"      • Tokens: {result.tokens_generated}")
                print(f"      • Modèle: {result.model_used}")
            else:
                print(f"   ❌ Échec: {result.error_message}")
        
        return True
        
    except Exception as e:
        logger.exception(f"❌ Erreur: {e}")
        return False


def test_worker(config):
    """Test 7: Worker d'enrichissement"""
    print_section("TEST 7: Worker d'enrichissement")
    
    model_path = Path(config.model_path)
    
    if not model_path.exists():
        print(f"⚠️  Modèle non trouvé: {model_path}")
        return False
    
    try:
        from enrichment.worker import EnrichmentWorker
        from database import SessionLocal, Transcription
        
        print("📝 Création d'une transcription de test...")
        
        test_id = str(uuid.uuid4())
        test_text = """
        Bonjour, je vous contacte concernant une réclamation.
        J'ai acheté un produit défectueux et je souhaite un remboursement.
        Merci de traiter ma demande rapidement.
        """
        
        db = SessionLocal()
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
        print(f"   ✅ Transcription créée: {test_id[:8]}...")
        
        print("\n📝 Création du worker...")
        worker = EnrichmentWorker(config)
        print("   ✅ Worker créé")
        
        print("\n📝 Recherche de transcriptions à enrichir...")
        transcriptions = worker._get_pending_transcriptions()
        print(f"   ✅ {len(transcriptions)} transcription(s) trouvée(s)")
        
        if transcriptions:
            print("\n📝 Traitement de la transcription...")
            print("   ⏳ Génération en cours (30-60s)...")
            worker._process_transcription(transcriptions[0])
            
            # Vérifier le résultat
            from enrichment.models import get_enrichment_by_transcription_id
            enrichment = get_enrichment_by_transcription_id(db, test_id)
            
            if enrichment and enrichment.status == 'done':
                print(f"\n   ✅ Enrichissement créé avec succès!")
                print(f"   📌 Titre: {enrichment.title}")
                print(f"   📝 Résumé: {enrichment.summary[:80]}...")
                print(f"   🔹 Points: {len(enrichment.bullets or [])} bullets")
                print(f"   😊 Sentiment: {enrichment.sentiment}")
                
                # Nettoyer
                db.delete(enrichment)
            else:
                print("   ❌ Enrichissement non créé ou en erreur")
        
        # Nettoyer la transcription
        db.delete(transcription)
        db.commit()
        db.close()
        
        print("\n   ✅ Nettoyage effectué")
        
        return True
        
    except Exception as e:
        logger.exception(f"❌ Erreur: {e}")
        return False


def main():
    """Lance tous les tests"""
    
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*20 + "🧪 TEST SUITE ENRICHMENT" + " "*24 + "║")
    print("╚" + "="*68 + "╝")
    
    results = {}
    config = None
    
    # Test 1: Configuration
    success, config = test_config()
    results['Config'] = success
    
    if not success or not config:
        print("\n❌ Impossible de continuer sans configuration valide")
        return False
    
    # Test 2: Modèles DB
    results['Models'] = test_models()
    
    # Test 3: Utilitaires
    results['Utils'] = test_utils()
    
    # Test 4: Prompts
    results['Prompts'] = test_prompts()
    
    # Tests avec LLM (optionnels si pas de modèle)
    model_path = Path(config.model_path)
    
    if model_path.exists():
        # Test 5: Moteur LLM
        results['LLM Engine'] = test_llm_engine(config)
        
        # Test 6: Processeur (si LLM OK)
        if results['LLM Engine']:
            results['Processor'] = test_processor(config)
        
        # Test 7: Worker (si tout OK)
        if all([results['LLM Engine'], results.get('Processor', False)]):
            results['Worker'] = test_worker(config)
    else:
        print("\n⚠️  Tests LLM ignorés (modèle non trouvé)")
        print("💡 Téléchargez-le avec: make download-model")
    
    # Résumé
    print_section("RÉSUMÉ DES TESTS")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status}  {test_name}")
    
    print(f"\n📊 Résultats: {passed}/{total} tests réussis")
    
    if failed == 0:
        print("\n🎉 Tous les tests sont passés!")
        print("✅ Le module d'enrichissement est prêt à l'emploi")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) échoué(s)")
        print("💡 Vérifiez les erreurs ci-dessus")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⌨️  Interruption par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"❌ Erreur fatale: {e}")
        sys.exit(1)