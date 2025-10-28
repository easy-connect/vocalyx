"""
enrichment/config.py
Configuration du module d'enrichissement
"""

import os
import configparser
import logging
from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)


class EnrichmentConfig:
    """Configuration pour le module d'enrichissement"""
    
    def __init__(self, config_file: str = "config.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        
        if not os.path.exists(config_file):
            logger.warning(f"Config file not found: {config_file}, using defaults")
            self._set_defaults()
        else:
            self.config.read(config_file)
            self._load_settings()
    
    def _set_defaults(self):
        """Définit les valeurs par défaut"""
        self.enabled = True
        self.poll_interval_seconds = 15
        self.batch_size = 3
        self.max_retries = 3
        self.retry_delay_seconds = 60
        
        self.model_path = "models/mistral-7b-instruct-v0.3.Q4_K_M.gguf"
        self.model_type = "mistral"
        self.n_ctx = 4096
        self.n_threads = 6
        self.n_batch = 512
        self.temperature = 0.3
        self.top_p = 0.9
        self.top_k = 40
        self.repeat_penalty = 1.1
        self.max_tokens = 500
        
        self.max_transcription_chars = 15000
        self.min_transcription_chars = 100
        
        self.generate_title = True
        self.generate_summary = True
        self.generate_bullets = True
        self.generate_sentiment = True
        self.generate_topics = False
        
        self.prompt_language = "fr"
        self.output_language = "fr"
        
        self.database_path = "sqlite:///./transcriptions.db"
        
        self.log_level = "INFO"
        self.log_file = "logs/enrichment.log"
    
    def _load_settings(self):
        """Charge les paramètres depuis config.ini"""
        
        # ENRICHMENT section
        if self.config.has_section('ENRICHMENT'):
            self.enabled = self.config.getboolean('ENRICHMENT', 'enabled', fallback=True)
            self.poll_interval_seconds = self.config.getint('ENRICHMENT', 'poll_interval_seconds', fallback=15)
            self.batch_size = self.config.getint('ENRICHMENT', 'batch_size', fallback=3)
            self.max_retries = self.config.getint('ENRICHMENT', 'max_retries', fallback=3)
            self.retry_delay_seconds = self.config.getint('ENRICHMENT', 'retry_delay_seconds', fallback=60)
            
            self.model_path = self.config.get('ENRICHMENT', 'model_path', 
                                             fallback='models/mistral-7b-instruct-v0.3.Q4_K_M.gguf')
            self.model_type = self.config.get('ENRICHMENT', 'model_type', fallback='mistral')
            self.n_ctx = self.config.getint('ENRICHMENT', 'n_ctx', fallback=4096)
            self.n_threads = self.config.getint('ENRICHMENT', 'n_threads', fallback=6)
            self.n_batch = self.config.getint('ENRICHMENT', 'n_batch', fallback=512)
            self.temperature = self.config.getfloat('ENRICHMENT', 'temperature', fallback=0.3)
            self.top_p = self.config.getfloat('ENRICHMENT', 'top_p', fallback=0.9)
            self.top_k = self.config.getint('ENRICHMENT', 'top_k', fallback=40)
            self.repeat_penalty = self.config.getfloat('ENRICHMENT', 'repeat_penalty', fallback=1.1)
            self.max_tokens = self.config.getint('ENRICHMENT', 'max_tokens', fallback=500)
            
            self.max_transcription_chars = self.config.getint('ENRICHMENT', 'max_transcription_chars', fallback=15000)
            self.min_transcription_chars = self.config.getint('ENRICHMENT', 'min_transcription_chars', fallback=100)
            
            self.generate_title = self.config.getboolean('ENRICHMENT', 'generate_title', fallback=True)
            self.generate_summary = self.config.getboolean('ENRICHMENT', 'generate_summary', fallback=True)
            self.generate_bullets = self.config.getboolean('ENRICHMENT', 'generate_bullets', fallback=True)
            self.generate_sentiment = self.config.getboolean('ENRICHMENT', 'generate_sentiment', fallback=True)
            self.generate_topics = self.config.getboolean('ENRICHMENT', 'generate_topics', fallback=False)
            
            self.prompt_language = self.config.get('ENRICHMENT', 'prompt_language', fallback='fr')
            self.output_language = self.config.get('ENRICHMENT', 'output_language', fallback='fr')
        else:
            logger.warning("No [ENRICHMENT] section found, using defaults")
            self._set_defaults()
        
        # DATABASE section (fallback to main config if not in ENRICHMENT)
        if self.config.has_section('DATABASE'):
            self.database_path = self.config.get('DATABASE', 'database_path', 
                                                 fallback='sqlite:///./transcriptions.db')
        elif self.config.has_section('PATHS'):
            self.database_path = self.config.get('PATHS', 'database_path',
                                                 fallback='sqlite:///./transcriptions.db')
        else:
            self.database_path = 'sqlite:///./transcriptions.db'
        
        # LOGGING section
        if self.config.has_section('LOGGING'):
            self.log_level = self.config.get('LOGGING', 'level', fallback='INFO')
            self.log_file = self.config.get('LOGGING', 'file_path', fallback='logs/enrichment.log')
        else:
            self.log_level = 'INFO'
            self.log_file = 'logs/enrichment.log'
    
    def validate(self) -> tuple[bool, list[str]]:
        """
        Valide la configuration
        
        Returns:
            (is_valid, errors)
        """
        errors = []
        
        # Vérifier que le modèle existe
        if not Path(self.model_path).exists():
            errors.append(f"Model file not found: {self.model_path}")
        
        # Vérifier les valeurs numériques
        if self.n_ctx < 512:
            errors.append(f"n_ctx too small: {self.n_ctx} (min: 512)")
        
        if self.n_threads < 1:
            errors.append(f"n_threads must be >= 1: {self.n_threads}")
        
        if self.batch_size < 1:
            errors.append(f"batch_size must be >= 1: {self.batch_size}")
        
        if not 0 <= self.temperature <= 2:
            errors.append(f"temperature must be 0-2: {self.temperature}")
        
        if not 0 <= self.top_p <= 1:
            errors.append(f"top_p must be 0-1: {self.top_p}")
        
        if self.max_transcription_chars < self.min_transcription_chars:
            errors.append("max_transcription_chars must be > min_transcription_chars")
        
        # Vérifier qu'au moins une génération est activée
        if not any([
            self.generate_title,
            self.generate_summary,
            self.generate_bullets,
            self.generate_sentiment
        ]):
            errors.append("At least one generation option must be enabled")
        
        return len(errors) == 0, errors
    
    def to_dict(self) -> dict:
        """Retourne la config sous forme de dictionnaire"""
        return {
            'enabled': self.enabled,
            'worker': {
                'poll_interval_seconds': self.poll_interval_seconds,
                'batch_size': self.batch_size,
                'max_retries': self.max_retries,
                'retry_delay_seconds': self.retry_delay_seconds
            },
            'model': {
                'path': self.model_path,
                'type': self.model_type,
                'n_ctx': self.n_ctx,
                'n_threads': self.n_threads,
                'n_batch': self.n_batch
            },
            'generation': {
                'temperature': self.temperature,
                'top_p': self.top_p,
                'top_k': self.top_k,
                'repeat_penalty': self.repeat_penalty,
                'max_tokens': self.max_tokens
            },
            'limits': {
                'max_transcription_chars': self.max_transcription_chars,
                'min_transcription_chars': self.min_transcription_chars
            },
            'features': {
                'generate_title': self.generate_title,
                'generate_summary': self.generate_summary,
                'generate_bullets': self.generate_bullets,
                'generate_sentiment': self.generate_sentiment,
                'generate_topics': self.generate_topics
            },
            'language': {
                'prompt': self.prompt_language,
                'output': self.output_language
            },
            'database': {
                'path': self.database_path
            },
            'logging': {
                'level': self.log_level,
                'file': self.log_file
            }
        }
    
    def __repr__(self):
        return f"<EnrichmentConfig(model={Path(self.model_path).name}, enabled={self.enabled})>"


def create_default_enrichment_section() -> str:
    """
    Retourne le texte d'une section [ENRICHMENT] par défaut
    à ajouter dans config.ini
    """
    return """
[ENRICHMENT]
# Worker settings
enabled = true
poll_interval_seconds = 15
batch_size = 3
max_retries = 3
retry_delay_seconds = 60

# Model settings
model_path = models/mistral-7b-instruct-v0.3.Q4_K_M.gguf
model_type = mistral
n_ctx = 4096
n_threads = 6
n_batch = 512
temperature = 0.3
top_p = 0.9
top_k = 40
repeat_penalty = 1.1
max_tokens = 500

# Processing limits
max_transcription_chars = 15000
min_transcription_chars = 100

# Features
generate_title = true
generate_summary = true
generate_bullets = true
generate_sentiment = true
generate_topics = false

# Language
prompt_language = fr
output_language = fr

[DATABASE]
# Base de données (si pas déjà défini dans [PATHS])
database_path = sqlite:///./transcriptions.db
"""


if __name__ == "__main__":
    # Test de la config
    print("=== Test EnrichmentConfig ===\n")
    
    config = EnrichmentConfig()
    
    print("Configuration chargée:")
    print(f"  Enabled: {config.enabled}")
    print(f"  Model: {config.model_path}")
    print(f"  Model type: {config.model_type}")
    print(f"  Threads: {config.n_threads}")
    print(f"  Context: {config.n_ctx}")
    print(f"  Batch size: {config.batch_size}")
    print(f"  Temperature: {config.temperature}")
    
    print("\nValidation:")
    is_valid, errors = config.validate()
    if is_valid:
        print("  ✅ Configuration valide")
    else:
        print("  ❌ Erreurs de configuration:")
        for error in errors:
            print(f"    - {error}")
    
    print("\n=== Section [ENRICHMENT] par défaut ===")
    print(create_default_enrichment_section())