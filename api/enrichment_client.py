"""
Client HTTP pour appeler le service d'enrichissement
Utilisé par le service de transcription
"""

import os
import logging
import requests
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class EnrichmentClient:
    """
    Client pour communiquer avec le service d'enrichissement.
    Permet au service de transcription de déclencher des enrichissements.
    """
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Args:
            base_url: URL du service d'enrichissement
                     Par défaut: http://localhost:8001
                     Peut être surchargé via env var ENRICHMENT_SERVICE_URL
        """
        self.base_url = (
            base_url 
            or os.getenv("ENRICHMENT_SERVICE_URL", "http://localhost:8001")
        ).rstrip('/')
        
        self.timeout = int(os.getenv("ENRICHMENT_TIMEOUT", "30"))
        
        logger.info(f"EnrichmentClient initialized: {self.base_url}")
    
    def is_available(self) -> bool:
        """
        Vérifie si le service d'enrichissement est disponible.
        
        Returns:
            True si le service répond, False sinon
        """
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                
                if status in ['healthy', 'degraded']:
                    logger.debug(f"Enrichment service is {status}")
                    return True
                else:
                    logger.warning(f"Enrichment service is {status}")
                    return False
            else:
                logger.warning(f"Enrichment service returned {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Enrichment service unavailable: {e}")
            return False
    
    def trigger_enrichment(
        self, 
        transcription_id: str,
        raise_on_error: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Déclenche l'enrichissement d'une transcription.
        
        Args:
            transcription_id: ID de la transcription à enrichir
            raise_on_error: Si True, lève une exception en cas d'erreur
        
        Returns:
            Dictionnaire avec les infos de l'enrichissement créé, ou None si erreur
        """
        url = f"{self.base_url}/api/enrichment/trigger/{transcription_id}"
        
        try:
            logger.info(f"[{transcription_id[:8]}] Triggering enrichment...")
            
            response = requests.post(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                
                enrichment_id = data.get('enrichment_id')
                status = data.get('status')
                message = data.get('message')
                
                logger.info(
                    f"[{transcription_id[:8]}] Enrichment triggered: "
                    f"ID={enrichment_id}, status={status}"
                )
                
                return data
            
            elif response.status_code == 404:
                logger.error(f"[{transcription_id[:8]}] Transcription not found")
                if raise_on_error:
                    raise ValueError(f"Transcription not found: {transcription_id}")
                return None
            
            elif response.status_code == 400:
                error = response.json().get('detail', 'Bad request')
                logger.error(f"[{transcription_id[:8]}] Bad request: {error}")
                if raise_on_error:
                    raise ValueError(error)
                return None
            
            else:
                logger.error(
                    f"[{transcription_id[:8]}] Unexpected status: "
                    f"{response.status_code}"
                )
                if raise_on_error:
                    raise RuntimeError(f"Enrichment service error: {response.status_code}")
                return None
        
        except requests.exceptions.Timeout:
            logger.error(f"[{transcription_id[:8]}] Timeout calling enrichment service")
            if raise_on_error:
                raise
            return None
        
        except requests.exceptions.RequestException as e:
            logger.error(f"[{transcription_id[:8]}] Error calling enrichment service: {e}")
            if raise_on_error:
                raise
            return None
    
    def get_enrichment(
        self, 
        transcription_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Récupère l'enrichissement d'une transcription.
        
        Args:
            transcription_id: ID de la transcription
        
        Returns:
            Dictionnaire avec l'enrichissement, ou None si non trouvé
        """
        url = f"{self.base_url}/api/enrichment/{transcription_id}"
        
        try:
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            else:
                logger.error(f"Error getting enrichment: {response.status_code}")
                return None
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling enrichment service: {e}")
            return None
    
    def get_combined(
        self, 
        transcription_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Récupère la transcription + enrichissement en une requête.
        
        Args:
            transcription_id: ID de la transcription
        
        Returns:
            Dictionnaire avec transcription et enrichissement
        """
        url = f"{self.base_url}/api/enrichment/combined/{transcription_id}"
        
        try:
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error getting combined: {response.status_code}")
                return None
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling enrichment service: {e}")
            return None
    
    def get_stats(self) -> Optional[Dict[str, Any]]:
        """
        Récupère les statistiques du service d'enrichissement.
        
        Returns:
            Dictionnaire avec les stats, ou None si erreur
        """
        url = f"{self.base_url}/api/enrichment/stats/summary"
        
        try:
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error getting stats: {response.status_code}")
                return None
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling enrichment service: {e}")
            return None


# ========================================
# Instance globale (singleton)
# ========================================

_enrichment_client: Optional[EnrichmentClient] = None


def get_enrichment_client() -> EnrichmentClient:
    """
    Retourne l'instance du client d'enrichissement (singleton).
    
    Returns:
        Instance de EnrichmentClient
    """
    global _enrichment_client
    
    if _enrichment_client is None:
        _enrichment_client = EnrichmentClient()
    
    return _enrichment_client


# ========================================
# Fonctions helper
# ========================================

def trigger_enrichment_async(transcription_id: str) -> bool:
    """
    Déclenche un enrichissement de manière asynchrone (fire-and-forget).
    N'attend pas la réponse, ne lève pas d'erreur.
    
    Args:
        transcription_id: ID de la transcription
    
    Returns:
        True si déclenché avec succès, False sinon
    """
    client = get_enrichment_client()
    
    # Vérifier disponibilité
    if not client.is_available():
        logger.warning("Enrichment service not available, skipping")
        return False
    
    # Déclencher (sans raise_on_error)
    result = client.trigger_enrichment(transcription_id, raise_on_error=False)
    
    return result is not None


def check_enrichment_service() -> Dict[str, Any]:
    """
    Vérifie l'état du service d'enrichissement.
    
    Returns:
        Dictionnaire avec l'état du service
    """
    client = get_enrichment_client()
    
    available = client.is_available()
    
    result = {
        "url": client.base_url,
        "available": available,
        "checked_at": datetime.utcnow().isoformat()
    }
    
    if available:
        stats = client.get_stats()
        if stats:
            result["stats"] = stats
    
    return result


# ========================================
# Tests
# ========================================

if __name__ == "__main__":
    """Script de test du client"""
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    print("\n" + "="*60)
    print("TEST: EnrichmentClient")
    print("="*60 + "\n")
    
    # Créer un client
    client = EnrichmentClient()
    
    # Test 1: Disponibilité
    print("1. Test disponibilité...")
    available = client.is_available()
    print(f"   {'✅' if available else '❌'} Service {'disponible' if available else 'indisponible'}\n")
    
    if not available:
        print("⚠️  Service d'enrichissement non accessible")
        print("   Démarrez-le avec: python app_enrichment.py")
        exit(1)
    
    # Test 2: Statistiques
    print("2. Test statistiques...")
    stats = client.get_stats()
    if stats:
        print(f"   ✅ Stats récupérées:")
        print(f"      Total: {stats.get('total', 0)}")
        print(f"      Done: {stats.get('done', 0)}")
        print(f"      Pending: {stats.get('pending', 0)}\n")
    else:
        print("   ❌ Échec récupération stats\n")
    
    # Test 3: Déclencher enrichissement (nécessite une transcription existante)
    print("3. Test trigger enrichissement...")
    print("   ⚠️  Nécessite une transcription existante (skip)\n")
    
    # Test 4: Check service
    print("4. Test check service...")
    check = check_enrichment_service()
    print(f"   ✅ URL: {check['url']}")
    print(f"   ✅ Disponible: {check['available']}")
    
    print("\n" + "="*60)
    print("✅ Tests terminés")
    print("="*60 + "\n")