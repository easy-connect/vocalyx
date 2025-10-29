"""
enrichment/llm_engine.py

Wrapper pour llama-cpp-python optimisé pour CPU
Gère le chargement, la génération et le cache du modèle LLM
"""

import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import json
import re

try:
    from llama_cpp import Llama
except ImportError:
    raise ImportError(
        "llama-cpp-python n'est pas installé. "
        "Installez-le avec: pip install llama-cpp-python"
    )

logger = logging.getLogger(__name__)


@dataclass
class GenerationConfig:
    """Configuration pour la génération de texte"""
    max_tokens: int = 500
    temperature: float = 0.3
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    stop: List[str] = None
    
    def __post_init__(self):
        if self.stop is None:
            self.stop = ["</s>", "[/INST]", "\n\n\n"]


@dataclass
class GenerationResult:
    """Résultat d'une génération"""
    text: str
    tokens_generated: int
    generation_time: float
    tokens_per_second: float
    prompt_tokens: int
    finish_reason: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "tokens_generated": self.tokens_generated,
            "generation_time": self.generation_time,
            "tokens_per_second": self.tokens_per_second,
            "prompt_tokens": self.prompt_tokens,
            "finish_reason": self.finish_reason
        }


class LLMEngine:
    """
    Moteur LLM basé sur llama-cpp-python
    Optimisé pour CPU avec support de quantization
    """
    
    def __init__(
        self,
        model_path: str,
        n_ctx: int = 4096,
        n_threads: int = 6,
        n_batch: int = 512,
        verbose: bool = False
    ):
        """
        Initialise le moteur LLM
        
        Args:
            model_path: Chemin vers le fichier .gguf
            n_ctx: Taille du contexte (tokens)
            n_threads: Nombre de threads CPU
            n_batch: Taille du batch pour le traitement
            verbose: Mode verbeux
        """
        self.model_path = Path(model_path)
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.n_batch = n_batch
        self.verbose = verbose
        
        self.model: Optional[Llama] = None
        self.is_loaded = False
        self.model_info: Dict[str, Any] = {}
        
        # Statistiques
        self.total_generations = 0
        self.total_tokens_generated = 0
        self.total_generation_time = 0.0
        
    def load(self) -> bool:
        """Charge le modèle en mémoire"""
        if self.is_loaded:
            logger.warning("Modèle déjà chargé")
            return True
        
        if not self.model_path.exists():
            logger.error(f"❌ Modèle non trouvé: {self.model_path}")
            return False
        
        try:
            logger.info(f"🔄 Chargement du modèle: {self.model_path.name}")
            start_time = time.time()
            
            # Supprimer les logs llama-cpp pendant le chargement
            import sys
            import os
            old_stderr = sys.stderr
            
            try:
                # Rediriger stderr vers /dev/null
                sys.stderr = open(os.devnull, 'w')
                
                self.model = Llama(
                    model_path=str(self.model_path),
                    n_ctx=self.n_ctx,
                    n_threads=self.n_threads,
                    n_batch=self.n_batch,
                    verbose=False,
                    use_mmap=True,
                    use_mlock=False,
                    logits_all=False,
                )
            finally:
                # Restaurer stderr
                sys.stderr.close()
                sys.stderr = old_stderr
            
            load_time = time.time() - start_time
            
            # Extraire les infos du modèle
            self.model_info = {
                "path": str(self.model_path),
                "name": self.model_path.stem,
                "size_mb": self.model_path.stat().st_size / (1024 * 1024),
                "n_ctx": self.n_ctx,
                "n_threads": self.n_threads,
                "n_batch": self.n_batch,
                "load_time": round(load_time, 2)
            }
            
            self.is_loaded = True
            
            logger.info(
                f"✅ Modèle chargé: {self.model_info['name']} "
                f"({self.model_info['size_mb']:.0f}MB) "
                f"en {load_time:.1f}s"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement: {e}")
            return False
    
    def unload(self):
        """Décharge le modèle de la mémoire"""
        if self.model is not None:
            del self.model
            self.model = None
            self.is_loaded = False
            logger.info("🗑️  Modèle déchargé")
    
    def generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None
    ) -> Optional[GenerationResult]:
        """
        Génère du texte à partir d'un prompt
        
        Args:
            prompt: Le prompt à compléter
            config: Configuration de génération
            
        Returns:
            GenerationResult ou None en cas d'erreur
        """
        if not self.is_loaded:
            logger.error("❌ Modèle non chargé. Appelez load() d'abord.")
            return None
        
        if config is None:
            config = GenerationConfig()
        
        try:
            logger.debug(f"📝 Génération (max_tokens={config.max_tokens})")
            start_time = time.time()
            
            # Génération
            output = self.model(
                prompt,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                top_p=config.top_p,
                top_k=config.top_k,
                repeat_penalty=config.repeat_penalty,
                stop=config.stop,
                echo=False  # Ne pas répéter le prompt
            )
            
            generation_time = time.time() - start_time
            
            # Extraire les informations
            text = output['choices'][0]['text']
            finish_reason = output['choices'][0].get('finish_reason', 'unknown')
            
            # Statistiques de tokens
            usage = output.get('usage', {})
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            
            tokens_per_second = completion_tokens / generation_time if generation_time > 0 else 0
            
            # Mettre à jour les stats globales
            self.total_generations += 1
            self.total_tokens_generated += completion_tokens
            self.total_generation_time += generation_time
            
            result = GenerationResult(
                text=text.strip(),
                tokens_generated=completion_tokens,
                generation_time=round(generation_time, 2),
                tokens_per_second=round(tokens_per_second, 1),
                prompt_tokens=prompt_tokens,
                finish_reason=finish_reason
            )
            
            logger.debug(
                f"✅ Généré {completion_tokens} tokens "
                f"en {generation_time:.1f}s "
                f"({tokens_per_second:.1f} tok/s)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la génération: {e}")
            return None
    
    def generate_with_retry(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Optional[GenerationResult]:
        """
        Génère avec retry automatique en cas d'erreur
        
        Args:
            prompt: Le prompt
            config: Configuration
            max_retries: Nombre max de tentatives
            retry_delay: Délai entre tentatives (secondes)
            
        Returns:
            GenerationResult ou None
        """
        for attempt in range(max_retries):
            try:
                result = self.generate(prompt, config)
                if result is not None:
                    return result
                    
            except Exception as e:
                logger.warning(
                    f"⚠️  Tentative {attempt + 1}/{max_retries} échouée: {e}"
                )
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Backoff exponentiel
        
        logger.error(f"❌ Échec après {max_retries} tentatives")
        return None
    
    def extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extrait et parse du JSON depuis le texte généré
        
        Args:
            text: Texte contenant potentiellement du JSON
            
        Returns:
            Dict parsé ou None
        """
        # Chercher un bloc JSON avec regex
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                # Nettoyer le texte
                cleaned = match.strip()
                
                # Parser
                data = json.loads(cleaned)
                logger.debug(f"✅ JSON extrait et parsé: {list(data.keys())}")
                return data
                
            except json.JSONDecodeError:
                continue
        
        logger.warning("⚠️  Aucun JSON valide trouvé dans la réponse")
        return None
    
    def validate_json_response(
        self,
        data: Dict[str, Any],
        required_keys: List[str]
    ) -> bool:
        """
        Valide qu'une réponse JSON contient les clés requises
        
        Args:
            data: Dictionnaire à valider
            required_keys: Liste des clés obligatoires
            
        Returns:
            True si valide
        """
        missing_keys = [key for key in required_keys if key not in data]
        
        if missing_keys:
            logger.warning(f"⚠️  Clés manquantes: {missing_keys}")
            return False
        
        # Vérifier que les valeurs ne sont pas vides
        empty_keys = [
            key for key in required_keys
            if not data[key] or (isinstance(data[key], str) and not data[key].strip())
        ]
        
        if empty_keys:
            logger.warning(f"⚠️  Clés vides: {empty_keys}")
            return False
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques du moteur
        
        Returns:
            Dictionnaire de statistiques
        """
        avg_tokens_per_sec = (
            self.total_tokens_generated / self.total_generation_time
            if self.total_generation_time > 0 else 0
        )
        
        return {
            "is_loaded": self.is_loaded,
            "model_info": self.model_info,
            "total_generations": self.total_generations,
            "total_tokens_generated": self.total_tokens_generated,
            "total_generation_time": round(self.total_generation_time, 2),
            "avg_tokens_per_second": round(avg_tokens_per_sec, 1)
        }
    
    def __enter__(self):
        """Context manager: charge le modèle"""
        self.load()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager: décharge le modèle"""
        self.unload()
    
    def __repr__(self):
        status = "loaded" if self.is_loaded else "not loaded"
        model_name = self.model_info.get('name', self.model_path.name)
        return f"<LLMEngine({model_name}, {status})>"


# Fonction helper pour créer une instance depuis config
def create_llm_engine_from_config(config) -> LLMEngine:
    """
    Crée une instance LLMEngine depuis un objet de configuration
    
    Args:
        config: Objet config avec attributs model_path, n_ctx, etc.
        
    Returns:
        Instance de LLMEngine
    """
    return LLMEngine(
        model_path=config.model_path,
        n_ctx=config.n_ctx,
        n_threads=config.n_threads,
        n_batch=config.n_batch,
        verbose=config.log_level == "DEBUG"
    )


# Test du module
if __name__ == "__main__":
    """Script de test du moteur LLM"""
    
    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    # Chemin du modèle (à adapter)
    model_path = "models/mistral-7b-instruct-v0.3.Q4_K_M.gguf"
    
    if not Path(model_path).exists():
        print(f"❌ Modèle non trouvé: {model_path}")
        print("Téléchargez-le avec: make download-model")
        exit(1)
    
    # Test du moteur
    print("\n🧪 Test du moteur LLM\n")
    
    # Utiliser le context manager
    with LLMEngine(
        model_path=model_path,
        n_ctx=2048,
        n_threads=6,
        n_batch=512
    ) as engine:
        
        # Test 1: Génération simple
        print("📝 Test 1: Génération simple")
        prompt = """<s>[INST] Résume cette phrase en 5 mots maximum:
"Le chat noir dort paisiblement sur le canapé rouge." [/INST]"""
        
        result = engine.generate(
            prompt,
            GenerationConfig(max_tokens=50, temperature=0.3)
        )
        
        if result:
            print(f"✅ Réponse: {result.text}")
            print(f"   Tokens: {result.tokens_generated}")
            print(f"   Vitesse: {result.tokens_per_second} tok/s")
        
        # Test 2: Génération JSON
        print("\n📝 Test 2: Génération JSON")
        prompt_json = """<s>[INST] Analyse ce texte et réponds en JSON:
"Le client est très satisfait du service."

Format JSON:
{
  "sentiment": "positif|negatif|neutre",
  "confiance": 0.95
}
[/INST]"""
        
        result = engine.generate(
            prompt_json,
            GenerationConfig(max_tokens=100, temperature=0.2)
        )
        
        if result:
            print(f"✅ Réponse brute: {result.text}")
            data = engine.extract_json(result.text)
            if data:
                print(f"✅ JSON parsé: {data}")
        
        # Afficher les stats finales
        print("\n📊 Statistiques:")
        stats = engine.get_stats()
        print(f"  Générations: {stats['total_generations']}")
        print(f"  Tokens totaux: {stats['total_tokens_generated']}")
        print(f"  Temps total: {stats['total_generation_time']}s")
        print(f"  Vitesse moyenne: {stats['avg_tokens_per_second']} tok/s")
    
    print("\n✅ Test terminé !")