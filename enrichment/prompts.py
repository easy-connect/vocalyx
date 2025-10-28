"""
enrichment/prompts.py
Templates de prompts pour enrichissement de transcriptions
"""

from typing import Dict, Any
from dataclasses import dataclass


SYSTEM_PROMPT = """Tu es un assistant spécialisé dans l'analyse d'appels clients de call center.
Tu génères des résumés clairs, concis et professionnels en français."""


@dataclass
class PromptTemplates:
    
    ALL_IN_ONE = """Analyse cette transcription d'appel client et génère :
1. Un titre court (max 10 mots)
2. Un résumé (2-3 phrases)
3. 3-5 points clés
4. Le sentiment général

Transcription :
{text}

Réponds au format JSON :
{{
  "titre": "titre ici",
  "resume": "résumé ici",
  "points_cles": ["point 1", "point 2", "point 3"],
  "sentiment": "positif|negatif|neutre|mixte",
  "confiance": 0.85
}}"""

    TITLE_ONLY = """Génère un titre court pour cette transcription (max 10 mots).

Transcription : {text}

Titre :"""

    SUMMARY_ONLY = """Résume cette transcription en 2-3 phrases.

Transcription : {text}

Résumé :"""

    BULLETS_ONLY = """Extrais 3-5 points clés de cette transcription.

Transcription : {text}

Points clés (format : - Point 1) :"""

    SENTIMENT_ONLY = """Analyse le sentiment de cette transcription.

Transcription : {text}

Sentiment (positif/negatif/neutre/mixte) :"""


class PromptBuilder:
    
    def __init__(self, model_type: str = "mistral"):
        self.model_type = model_type
        self.templates = PromptTemplates()
    
    def build_prompt(self, template: str, text: str, truncate: int = 10000) -> str:
        if len(text) > truncate:
            text = text[:truncate] + "..."
        
        instruction = template.format(text=text)
        
        if self.model_type == "mistral":
            return f"<s>[INST] {SYSTEM_PROMPT}\n\n{instruction} [/INST]"
        elif self.model_type == "llama":
            return f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{SYSTEM_PROMPT}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{instruction}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
        else:
            return f"System: {SYSTEM_PROMPT}\n\nUser: {instruction}\n\nAssistant:"
    
    def build_all_in_one(self, text: str) -> str:
        return self.build_prompt(self.templates.ALL_IN_ONE, text)
    
    def build_title(self, text: str) -> str:
        return self.build_prompt(self.templates.TITLE_ONLY, text)
    
    def build_summary(self, text: str) -> str:
        return self.build_prompt(self.templates.SUMMARY_ONLY, text)
    
    def build_bullets(self, text: str) -> str:
        return self.build_prompt(self.templates.BULLETS_ONLY, text)
    
    def build_sentiment(self, text: str) -> str:
        return self.build_prompt(self.templates.SENTIMENT_ONLY, text)


if __name__ == "__main__":
    builder = PromptBuilder(model_type="mistral")
    
    test_text = "Bonjour, je souhaite annuler ma commande. Le client service m'a dit que c'était possible."
    
    print("=== Test ALL IN ONE ===")
    print(builder.build_all_in_one(test_text)[:200])
    
    print("\n=== Test TITLE ===")
    print(builder.build_title(test_text)[:200])