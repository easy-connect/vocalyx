#!/usr/bin/env python3
"""
Exemple d'utilisation de l'API d'enrichissement Vocalyx
Démontre le workflow complet : upload audio → transcription → enrichissement
"""

import requests
import time
import sys


API_URL = "http://localhost:8000"


def upload_and_transcribe(audio_file: str) -> str:
    """Upload un fichier audio et démarre la transcription"""
    
    print(f"📤 Upload: {audio_file}")
    
    with open(audio_file, 'rb') as f:
        files = {'file': f}
        response = requests.post(f"{API_URL}/api/transcribe", files=files)
    
    if response.status_code != 200:
        print(f"❌ Erreur upload: {response.status_code}")
        sys.exit(1)
    
    data = response.json()
    transcription_id = data['transcription_id']
    
    print(f"✅ Transcription créée: {transcription_id[:8]}...")
    return transcription_id


def wait_transcription(transcription_id: str, timeout: int = 300) -> dict:
    """Attend que la transcription soit terminée"""
    
    print(f"⏳ Attente transcription...")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = requests.get(f"{API_URL}/api/transcribe/{transcription_id}")
        
        if response.status_code != 200:
            print(f"❌ Erreur polling: {response.status_code}")
            sys.exit(1)
        
        data = response.json()
        status = data['status']
        
        if status == 'done':
            duration = data.get('duration', 0)
            processing_time = data.get('processing_time', 0)
            speed = duration / processing_time if processing_time > 0 else 0
            
            print(f"✅ Transcription terminée")
            print(f"   • Durée audio: {duration:.1f}s")
            print(f"   • Temps traitement: {processing_time:.1f}s")
            print(f"   • Vitesse: {speed:.1f}x temps réel")
            print(f"   • Langue: {data.get('language', 'N/A')}")
            print(f"   • Segments: {data.get('segments_count', 0)}")
            
            return data
        
        elif status == 'error':
            print(f"❌ Transcription en erreur: {data.get('error_message')}")
            sys.exit(1)
        
        time.sleep(2)
    
    print(f"❌ Timeout transcription ({timeout}s)")
    sys.exit(1)


def trigger_enrichment(transcription_id: str) -> int:
    """Déclenche l'enrichissement d'une transcription"""
    
    print(f"\n🎨 Déclenchement enrichissement...")
    
    response = requests.post(f"{API_URL}/api/enrichment/trigger/{transcription_id}")
    
    if response.status_code != 200:
        print(f"❌ Erreur déclenchement: {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    data = response.json()
    enrichment_id = data['enrichment_id']
    status = data['status']
    message = data['message']
    
    print(f"✅ {message}")
    print(f"   • Enrichment ID: {enrichment_id}")
    print(f"   • Status: {status}")
    
    return enrichment_id


def wait_enrichment(transcription_id: str, timeout: int = 120) -> dict:
    """Attend que l'enrichissement soit terminé"""
    
    print(f"⏳ Attente enrichissement (peut prendre 30-60s)...")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = requests.get(f"{API_URL}/api/enrichment/{transcription_id}")
        
        if response.status_code == 404:
            print(f"⚠️  Enrichissement pas encore créé, attente...")
            time.sleep(3)
            continue
        
        if response.status_code != 200:
            print(f"❌ Erreur polling: {response.status_code}")
            sys.exit(1)
        
        data = response.json()
        status = data['status']
        
        if status == 'done':
            gen_time = data.get('generation_time', 0)
            tokens = data.get('tokens_generated', 0)
            
            print(f"✅ Enrichissement terminé")
            print(f"   • Temps génération: {gen_time:.1f}s")
            print(f"   • Tokens générés: {tokens}")
            print(f"   • Modèle: {data.get('model_used', 'N/A')}")
            
            return data
        
        elif status == 'error':
            print(f"❌ Enrichissement en erreur: {data.get('last_error')}")
            sys.exit(1)
        
        elapsed = time.time() - start_time
        print(f"   Status: {status} ({elapsed:.0f}s)", end='\r')
        
        time.sleep(3)
    
    print(f"\n❌ Timeout enrichissement ({timeout}s)")
    sys.exit(1)


def display_results(transcription: dict, enrichment: dict):
    """Affiche les résultats complets"""
    
    print("\n" + "="*70)
    print("📊 RÉSULTATS COMPLETS")
    print("="*70)
    
    # Transcription
    print("\n📝 TRANSCRIPTION")
    print("-"*70)
    text = transcription.get('text', '')
    if len(text) > 200:
        print(f"Texte: {text[:200]}...")
    else:
        print(f"Texte: {text}")
    
    # Enrichissement
    print("\n🎨 ENRICHISSEMENT")
    print("-"*70)
    
    title = enrichment.get('title', 'N/A')
    summary = enrichment.get('summary', 'N/A')
    bullets = enrichment.get('bullets', [])
    sentiment = enrichment.get('sentiment', 'N/A')
    confidence = enrichment.get('sentiment_confidence', 0)
    
    print(f"📌 Titre:")
    print(f"   {title}")
    
    print(f"\n📄 Résumé:")
    print(f"   {summary}")
    
    print(f"\n🔹 Points clés:")
    for i, bullet in enumerate(bullets, 1):
        print(f"   {i}. {bullet}")
    
    sentiment_emoji = {
        'positif': '😊',
        'negatif': '😞',
        'neutre': '😐',
        'mixte': '🤔'
    }.get(sentiment, '❓')
    
    print(f"\n{sentiment_emoji} Sentiment: {sentiment} (confiance: {confidence:.0%})")
    
    topics = enrichment.get('topics')
    if topics:
        print(f"\n🏷️  Topics: {', '.join(topics)}")
    
    print("\n" + "="*70)


def get_combined(transcription_id: str) -> dict:
    """Récupère transcription + enrichissement en une requête"""
    
    response = requests.get(f"{API_URL}/api/enrichment/combined/{transcription_id}")
    
    if response.status_code != 200:
        print(f"❌ Erreur récupération combinée: {response.status_code}")
        sys.exit(1)
    
    return response.json()


def get_stats():
    """Affiche les statistiques globales"""
    
    response = requests.get(f"{API_URL}/api/enrichment/stats/summary")
    
    if response.status_code != 200:
        print(f"❌ Erreur stats: {response.status_code}")
        return
    
    stats = response.json()
    
    print("\n📊 STATISTIQUES GLOBALES")
    print("-"*70)
    print(f"Total enrichissements: {stats['total']}")
    print(f"  • En attente: {stats['pending']}")
    print(f"  • En cours: {stats['processing']}")
    print(f"  • Terminés: {stats['done']}")
    print(f"  • Erreurs: {stats['error']}")
    
    if stats.get('avg_generation_time'):
        print(f"\nMoyennes:")
        print(f"  • Temps génération: {stats['avg_generation_time']:.1f}s")
        print(f"  • Tokens générés: {stats.get('avg_tokens_generated', 0)}")
        print(f"  • Confiance sentiment: {stats.get('avg_sentiment_confidence', 0):.0%}")


def main():
    """Workflow complet"""
    
    # Vérifier argument
    if len(sys.argv) < 2:
        print("Usage: python enrichment_api_usage.py <audio_file>")
        print("\nExemple:")
        print("  python enrichment_api_usage.py mon_audio.wav")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    
    print("="*70)
    print("🎙️  VOCALYX - Workflow Complet (Transcription + Enrichissement)")
    print("="*70)
    
    try:
        # 1. Upload et transcription
        transcription_id = upload_and_transcribe(audio_file)
        transcription = wait_transcription(transcription_id)
        
        # 2. Enrichissement
        enrichment_id = trigger_enrichment(transcription_id)
        enrichment = wait_enrichment(transcription_id)
        
        # 3. Afficher résultats
        display_results(transcription, enrichment)
        
        # 4. Statistiques
        get_stats()
        
        print("\n✅ Workflow terminé avec succès !")
        print(f"\n💡 Vous pouvez aussi récupérer les données combinées avec:")
        print(f"   GET /api/enrichment/combined/{transcription_id}")
        
    except KeyboardInterrupt:
        print("\n\n⌨️  Interruption utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()