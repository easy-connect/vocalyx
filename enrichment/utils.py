"""
enrichment/utils.py

Fonctions utilitaires pour le module d'enrichissement.
Traitement de texte, parsing, nettoyage, validation.
"""

import re
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


def truncate_text(text: str, max_length: int = 15000, ellipsis: str = "...") -> str:
    """
    Tronque un texte à une longueur maximale.
    
    Args:
        text: Texte à tronquer
        max_length: Longueur maximale
        ellipsis: Caractères à ajouter si tronqué
        
    Returns:
        Texte tronqué
    """
    if not text or len(text) <= max_length:
        return text
    
    # Tronquer en gardant des mots entiers
    truncated = text[:max_length].rsplit(' ', 1)[0]
    return truncated + ellipsis


def clean_generated_text(text: str) -> str:
    """
    Nettoie le texte généré par le LLM.
    Supprime les artefacts, espaces superflus, etc.
    
    Args:
        text: Texte à nettoyer
        
    Returns:
        Texte nettoyé
    """
    if not text:
        return ""
    
    # Supprimer les tags XML/HTML résiduels
    text = re.sub(r'<[^>]+>', '', text)
    
    # Supprimer les marqueurs de prompt
    text = re.sub(r'\[INST\]|\[/INST\]|<s>|</s>', '', text)
    
    # Supprimer les guillemets de début/fin s'ils encadrent tout
    text = text.strip()
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    if text.startswith("'") and text.endswith("'"):
        text = text[1:-1]
    
    # Nettoyer les espaces multiples
    text = re.sub(r'\s+', ' ', text)
    
    # Supprimer les retours à la ligne multiples
    text = re.sub(r'\n\s*\n+', '\n', text)
    
    return text.strip()


def parse_bullets_from_text(text: str) -> List[str]:
    """
    Extrait les points clés depuis un texte formaté.
    Reconnaît différents formats: -, •, 1., etc.
    
    Args:
        text: Texte contenant des points clés
        
    Returns:
        Liste de points clés
    """
    bullets = []
    
    # Pattern pour détecter les bullets
    # Supporte: -, •, *, 1., 1), etc.
    pattern = r'^[\s]*(?:[-•*]|\d+[.)])\s*(.+)$'
    
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        match = re.match(pattern, line)
        if match:
            bullet = match.group(1).strip()
            if bullet:
                bullets.append(clean_generated_text(bullet))
        elif line and not bullets:
            # Si pas de marqueur mais c'est le seul contenu, l'ajouter quand même
            bullets.append(clean_generated_text(line))
    
    # Si aucun bullet trouvé, essayer de splitter sur les points
    if not bullets and '.' in text:
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        bullets = [clean_generated_text(s) for s in sentences[:5]]
    
    return bullets


def normalize_sentiment(sentiment_text: str) -> str:
    """
    Normalise le sentiment extrait depuis le LLM.
    
    Args:
        sentiment_text: Texte brut du sentiment
        
    Returns:
        Sentiment normalisé: positif, negatif, neutre, mixte
    """
    sentiment_text = sentiment_text.lower().strip()
    
    # Mapping des variations
    positive_keywords = ['positif', 'positive', 'satisfait', 'content', 'heureux', 'bon']
    negative_keywords = ['negatif', 'negative', 'insatisfait', 'mécontent', 'mauvais', 'problème']
    neutral_keywords = ['neutre', 'neutral', 'objectif', 'factuel']
    mixed_keywords = ['mixte', 'mitigé', 'ambivalent', 'partagé']
    
    # Vérifier les correspondances
    if any(kw in sentiment_text for kw in mixed_keywords):
        return "mixte"
    if any(kw in sentiment_text for kw in positive_keywords):
        return "positif"
    if any(kw in sentiment_text for kw in negative_keywords):
        return "negatif"
    if any(kw in sentiment_text for kw in neutral_keywords):
        return "neutre"
    
    # Par défaut
    return "neutre"


def extract_topics(text: str, max_topics: int = 5) -> List[str]:
    """
    Extrait les topics/thèmes principaux d'un texte.
    Méthode simple basée sur la fréquence des mots.
    
    Args:
        text: Texte à analyser
        max_topics: Nombre maximum de topics
        
    Returns:
        Liste de topics
    """
    # Mots vides français
    stop_words = {
        'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'ou',
        'est', 'sont', 'a', 'ai', 'as', 'avec', 'dans', 'pour', 'sur',
        'par', 'en', 'au', 'aux', 'ce', 'ces', 'mon', 'ma', 'mes',
        'ton', 'ta', 'tes', 'son', 'sa', 'ses', 'notre', 'votre', 'leur',
        'je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles',
        'que', 'qui', 'quoi', 'dont', 'où', 'si', 'mais', 'car'
    }
    
    # Tokenizer simple
    words = re.findall(r'\b[a-zàâäéèêëïîôùûüÿç]{4,}\b', text.lower())
    
    # Compter les occurrences
    word_freq: Dict[str, int] = {}
    for word in words:
        if word not in stop_words:
            word_freq[word] = word_freq.get(word, 0) + 1
    
    # Trier par fréquence
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    
    # Retourner les top N
    topics = [word for word, freq in sorted_words[:max_topics] if freq > 1]
    
    return topics


def validate_enrichment_result(result: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Valide qu'un résultat d'enrichissement est complet et valide.
    
    Args:
        result: Dictionnaire du résultat d'enrichissement
        
    Returns:
        (is_valid, errors)
    """
    errors = []
    
    # Vérifier les champs obligatoires
    required_fields = ['title', 'summary', 'bullets', 'sentiment']
    for field in required_fields:
        if field not in result or not result[field]:
            errors.append(f"Champ manquant ou vide: {field}")
    
    # Vérifier le titre
    if 'title' in result and result['title']:
        if len(result['title']) > 200:
            errors.append(f"Titre trop long: {len(result['title'])} chars (max 200)")
        if len(result['title']) < 5:
            errors.append(f"Titre trop court: {len(result['title'])} chars (min 5)")
    
    # Vérifier le résumé
    if 'summary' in result and result['summary']:
        if len(result['summary']) < 20:
            errors.append(f"Résumé trop court: {len(result['summary'])} chars (min 20)")
        if len(result['summary']) > 1000:
            errors.append(f"Résumé trop long: {len(result['summary'])} chars (max 1000)")
    
    # Vérifier les bullets
    if 'bullets' in result:
        bullets = result['bullets']
        if not isinstance(bullets, list):
            errors.append("Bullets doit être une liste")
        elif len(bullets) == 0:
            errors.append("Bullets est vide")
        elif len(bullets) > 10:
            errors.append(f"Trop de bullets: {len(bullets)} (max 10)")
    
    # Vérifier le sentiment
    if 'sentiment' in result:
        valid_sentiments = ['positif', 'negatif', 'neutre', 'mixte']
        if result['sentiment'] not in valid_sentiments:
            errors.append(f"Sentiment invalide: {result['sentiment']} (doit être: {valid_sentiments})")
    
    # Vérifier la confiance
    if 'sentiment_confidence' in result:
        conf = result['sentiment_confidence']
        if not isinstance(conf, (int, float)):
            errors.append("Confiance doit être un nombre")
        elif not 0 <= conf <= 1:
            errors.append(f"Confiance invalide: {conf} (doit être 0-1)")
    
    return len(errors) == 0, errors


def format_enrichment_for_display(enrichment: Dict[str, Any]) -> str:
    """
    Formate un enrichissement pour affichage lisible.
    
    Args:
        enrichment: Dictionnaire d'enrichissement
        
    Returns:
        Texte formaté
    """
    lines = []
    
    lines.append("=" * 60)
    lines.append("📊 ENRICHISSEMENT")
    lines.append("=" * 60)
    
    if 'title' in enrichment and enrichment['title']:
        lines.append(f"\n📌 Titre:")
        lines.append(f"   {enrichment['title']}")
    
    if 'summary' in enrichment and enrichment['summary']:
        lines.append(f"\n📝 Résumé:")
        lines.append(f"   {enrichment['summary']}")
    
    if 'bullets' in enrichment and enrichment['bullets']:
        lines.append(f"\n🔹 Points clés:")
        for i, bullet in enumerate(enrichment['bullets'], 1):
            lines.append(f"   {i}. {bullet}")
    
    if 'sentiment' in enrichment:
        sentiment = enrichment['sentiment']
        confidence = enrichment.get('sentiment_confidence', 0)
        emoji = {
            'positif': '😊',
            'negatif': '😞',
            'neutre': '😐',
            'mixte': '🤔'
        }.get(sentiment, '❓')
        lines.append(f"\n{emoji} Sentiment: {sentiment} (confiance: {confidence:.0%})")
    
    if 'topics' in enrichment and enrichment['topics']:
        lines.append(f"\n🏷️  Topics: {', '.join(enrichment['topics'])}")
    
    lines.append("\n" + "=" * 60)
    
    return '\n'.join(lines)


def estimate_processing_time(text_length: int, model_size: str = "7B") -> float:
    """
    Estime le temps de traitement pour un texte donné.
    
    Args:
        text_length: Longueur du texte en caractères
        model_size: Taille du modèle (7B, 13B, etc.)
        
    Returns:
        Temps estimé en secondes
    """
    # Temps de base par token (approximatif)
    base_time_per_token = {
        "7B": 0.05,   # 20 tok/s
        "13B": 0.1,   # 10 tok/s
        "30B": 0.2,   # 5 tok/s
    }
    
    time_per_token = base_time_per_token.get(model_size, 0.05)
    
    # Estimation: 1 token ≈ 4 caractères
    estimated_tokens = text_length / 4
    
    # Temps de génération (on génère ~500 tokens)
    generation_tokens = 500
    total_tokens = estimated_tokens + generation_tokens
    
    estimated_time = total_tokens * time_per_token
    
    return round(estimated_time, 1)


def create_enrichment_summary(enrichment: Dict[str, Any]) -> str:
    """
    Crée un résumé court de l'enrichissement (une ligne).
    
    Args:
        enrichment: Dictionnaire d'enrichissement
        
    Returns:
        Résumé court
    """
    parts = []
    
    if 'title' in enrichment and enrichment['title']:
        title = enrichment['title'][:50]
        parts.append(f'"{title}"')
    
    if 'sentiment' in enrichment:
        emoji = {
            'positif': '😊',
            'negatif': '😞',
            'neutre': '😐',
            'mixte': '🤔'
        }.get(enrichment['sentiment'], '❓')
        parts.append(emoji)
    
    if 'bullets' in enrichment and enrichment['bullets']:
        parts.append(f"{len(enrichment['bullets'])} points")
    
    return ' | '.join(parts) if parts else "Enrichissement vide"


def sanitize_json_string(text: str) -> str:
    """
    Nettoie une chaîne pour qu'elle soit JSON-safe.
    
    Args:
        text: Texte à nettoyer
        
    Returns:
        Texte nettoyé
    """
    if not text:
        return ""
    
    # Échapper les caractères spéciaux JSON
    text = text.replace('\\', '\\\\')
    text = text.replace('"', '\\"')
    text = text.replace('\n', '\\n')
    text = text.replace('\r', '\\r')
    text = text.replace('\t', '\\t')
    
    return text


def calculate_text_stats(text: str) -> Dict[str, Any]:
    """
    Calcule des statistiques sur un texte.
    
    Args:
        text: Texte à analyser
        
    Returns:
        Dictionnaire de statistiques
    """
    if not text:
        return {
            'chars': 0,
            'words': 0,
            'sentences': 0,
            'avg_word_length': 0,
            'avg_sentence_length': 0
        }
    
    # Compter les caractères
    chars = len(text)
    
    # Compter les mots
    words = re.findall(r'\b\w+\b', text)
    word_count = len(words)
    
    # Compter les phrases
    sentences = re.split(r'[.!?]+', text)
    sentence_count = len([s for s in sentences if s.strip()])
    
    # Longueur moyenne des mots
    avg_word_length = sum(len(w) for w in words) / word_count if word_count > 0 else 0
    
    # Longueur moyenne des phrases (en mots)
    avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
    
    return {
        'chars': chars,
        'words': word_count,
        'sentences': sentence_count,
        'avg_word_length': round(avg_word_length, 1),
        'avg_sentence_length': round(avg_sentence_length, 1)
    }


def detect_language_simple(text: str) -> str:
    """
    Détection simple de la langue (français vs anglais).
    
    Args:
        text: Texte à analyser
        
    Returns:
        Code langue: 'fr' ou 'en'
    """
    # Mots indicateurs français
    fr_words = ['le', 'la', 'les', 'de', 'un', 'une', 'des', 'est', 'et', 'je', 'tu', 'il', 'elle']
    # Mots indicateurs anglais
    en_words = ['the', 'is', 'are', 'and', 'or', 'to', 'of', 'in', 'a', 'an', 'i', 'you', 'he', 'she']
    
    text_lower = text.lower()
    words = re.findall(r'\b\w+\b', text_lower)
    
    fr_count = sum(1 for word in words if word in fr_words)
    en_count = sum(1 for word in words if word in en_words)
    
    return 'fr' if fr_count > en_count else 'en'


def merge_bullets(bullets1: List[str], bullets2: List[str], max_bullets: int = 5) -> List[str]:
    """
    Fusionne deux listes de bullets en éliminant les doublons.
    
    Args:
        bullets1: Première liste
        bullets2: Deuxième liste
        max_bullets: Nombre maximum de bullets
        
    Returns:
        Liste fusionnée
    """
    # Normaliser les bullets
    normalized = {}
    for bullet in bullets1 + bullets2:
        # Nettoyer
        clean = clean_generated_text(bullet).lower()
        # Utiliser comme clé pour déduplication
        if clean and clean not in normalized:
            normalized[clean] = bullet
    
    # Retourner les max_bullets premiers
    return list(normalized.values())[:max_bullets]


def extract_keywords(text: str, max_keywords: int = 10) -> List[tuple[str, int]]:
    """
    Extrait les mots-clés les plus fréquents d'un texte.
    
    Args:
        text: Texte à analyser
        max_keywords: Nombre maximum de mots-clés
        
    Returns:
        Liste de tuples (mot, fréquence)
    """
    # Mots vides français communs
    stop_words = {
        'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'ou',
        'est', 'sont', 'a', 'ai', 'as', 'avec', 'dans', 'pour', 'sur',
        'par', 'en', 'au', 'aux', 'ce', 'ces', 'mon', 'ma', 'mes',
        'ton', 'ta', 'tes', 'son', 'sa', 'ses', 'notre', 'votre', 'leur',
        'je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles',
        'que', 'qui', 'quoi', 'dont', 'où', 'si', 'mais', 'car', 'donc',
        'pas', 'ne', 'plus', 'tout', 'bien', 'très', 'aussi', 'puis'
    }
    
    # Extraire les mots
    words = re.findall(r'\b[a-zàâäéèêëïîôùûüÿç]{3,}\b', text.lower())
    
    # Compter les fréquences
    word_freq = {}
    for word in words:
        if word not in stop_words:
            word_freq[word] = word_freq.get(word, 0) + 1
    
    # Trier par fréquence
    sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    
    return sorted_keywords[:max_keywords]


def format_time_elapsed(seconds: float) -> str:
    """
    Formate une durée en secondes en format lisible.
    
    Args:
        seconds: Durée en secondes
        
    Returns:
        Chaîne formatée (ex: "2m 30s", "45s", "1h 15m")
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"


def score_enrichment_quality(enrichment: Dict[str, Any]) -> float:
    """
    Attribue un score de qualité à un enrichissement.
    
    Args:
        enrichment: Dictionnaire d'enrichissement
        
    Returns:
        Score entre 0 et 1
    """
    score = 0.0
    max_score = 0.0
    
    # Titre présent et non vide (20%)
    max_score += 0.2
    if enrichment.get('title') and len(enrichment['title']) > 5:
        score += 0.2
    
    # Résumé présent et de bonne longueur (25%)
    max_score += 0.25
    summary = enrichment.get('summary', '')
    if summary and 50 <= len(summary) <= 500:
        score += 0.25
    elif summary:
        score += 0.15
    
    # Points clés présents et pertinents (30%)
    max_score += 0.3
    bullets = enrichment.get('bullets', [])
    if bullets:
        bullet_score = min(len(bullets) / 5, 1.0) * 0.3  # Idéal: 5 bullets
        score += bullet_score
    
    # Sentiment présent (15%)
    max_score += 0.15
    if enrichment.get('sentiment') in ['positif', 'negatif', 'neutre', 'mixte']:
        score += 0.15
    
    # Confiance du sentiment (10%)
    max_score += 0.1
    confidence = enrichment.get('sentiment_confidence', 0)
    if confidence > 0.7:
        score += 0.1
    elif confidence > 0.5:
        score += 0.05
    
    return round(score / max_score, 2) if max_score > 0 else 0.0


def create_enrichment_hash(text: str) -> str:
    """
    Crée un hash du texte pour détecter les doublons.
    
    Args:
        text: Texte à hasher
        
    Returns:
        Hash MD5
    """
    import hashlib
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def split_long_text(text: str, max_length: int = 10000, overlap: int = 200) -> List[str]:
    """
    Découpe un texte long en morceaux avec overlap.
    
    Args:
        text: Texte à découper
        max_length: Longueur maximale par morceau
        overlap: Nombre de caractères de chevauchement
        
    Returns:
        Liste de morceaux de texte
    """
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + max_length
        
        # Si pas à la fin, essayer de couper sur une phrase
        if end < len(text):
            # Chercher le dernier point avant end
            last_period = text[start:end].rfind('.')
            if last_period > max_length // 2:  # Au moins la moitié du chunk
                end = start + last_period + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Avancer avec overlap
        start = end - overlap
    
    return chunks


# === Tests unitaires ===

def test_utils():
    """Tests des fonctions utilitaires"""
    print("\n" + "="*60)
    print("🧪 Tests des utilitaires d'enrichissement")
    print("="*60 + "\n")
    
    # Test 1: truncate_text
    print("1. Test truncate_text")
    long_text = "Ceci est un texte très long " * 100
    truncated = truncate_text(long_text, 50)
    assert len(truncated) <= 53  # 50 + "..."
    print(f"   ✅ Texte tronqué: {len(long_text)} → {len(truncated)} chars")
    
    # Test 2: clean_generated_text
    print("\n2. Test clean_generated_text")
    dirty = '  <s>[INST]  Voici   un   texte  [/INST]  '
    clean = clean_generated_text(dirty)
    assert '<s>' not in clean
    assert '[INST]' not in clean
    print(f"   ✅ Texte nettoyé: '{clean}'")
    
    # Test 3: parse_bullets_from_text
    print("\n3. Test parse_bullets_from_text")
    bullet_text = """
    - Premier point important
    - Deuxième point clé
    • Troisième point avec puce
    1. Quatrième point numéroté
    """
    bullets = parse_bullets_from_text(bullet_text)
    assert len(bullets) == 4
    print(f"   ✅ {len(bullets)} bullets extraits")
    for b in bullets:
        print(f"      • {b}")
    
    # Test 4: normalize_sentiment
    print("\n4. Test normalize_sentiment")
    test_sentiments = [
        ("Le client est très satisfait", "positif"),
        ("Problème avec la commande", "negatif"),
        ("Information neutre", "neutre"),
        ("Sentiment mitigé", "mixte")
    ]
    for text, expected in test_sentiments:
        result = normalize_sentiment(text)
        assert result == expected
        print(f"   ✅ '{text[:30]}' → {result}")
    
    # Test 5: validate_enrichment_result
    print("\n5. Test validate_enrichment_result")
    valid_enrichment = {
        'title': 'Titre valide',
        'summary': 'Ceci est un résumé valide avec assez de contenu.',
        'bullets': ['Point 1', 'Point 2', 'Point 3'],
        'sentiment': 'positif',
        'sentiment_confidence': 0.85
    }
    is_valid, errors = validate_enrichment_result(valid_enrichment)
    assert is_valid
    print(f"   ✅ Validation réussie")
    
    # Test 6: calculate_text_stats
    print("\n6. Test calculate_text_stats")
    sample_text = "Ceci est un texte de test. Il contient plusieurs phrases. Voilà."
    stats = calculate_text_stats(sample_text)
    print(f"   ✅ Stats calculées:")
    print(f"      - Caractères: {stats['chars']}")
    print(f"      - Mots: {stats['words']}")
    print(f"      - Phrases: {stats['sentences']}")
    print(f"      - Longueur moy. mots: {stats['avg_word_length']}")
    
    # Test 7: extract_keywords
    print("\n7. Test extract_keywords")
    text = "Le client appelle pour un problème de commande. La commande n'est pas arrivée. Le client souhaite un remboursement."
    keywords = extract_keywords(text, max_keywords=5)
    print(f"   ✅ {len(keywords)} mots-clés extraits:")
    for word, freq in keywords[:3]:
        print(f"      • {word}: {freq} fois")
    
    # Test 8: score_enrichment_quality
    print("\n8. Test score_enrichment_quality")
    score = score_enrichment_quality(valid_enrichment)
    print(f"   ✅ Score qualité: {score:.0%}")
    
    print("\n" + "="*60)
    print("✅ Tous les tests passés !")
    print("="*60 + "\n")


if __name__ == "__main__":
    # Configurer le logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    # Lancer les tests
    test_utils()