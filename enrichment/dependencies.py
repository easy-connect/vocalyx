"""
enrichment/dependencies.py
Dépendances FastAPI pour l'injection de configuration
"""

from functools import lru_cache
from enrichment.config import EnrichmentConfig

@lru_cache()
def get_enrichment_config() -> EnrichmentConfig:
    """
    Dépendance FastAPI pour récupérer la config (singleton via lru_cache)
    Usage: config: EnrichmentConfig = Depends(get_enrichment_config)
    """
    return EnrichmentConfig()