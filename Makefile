# Vocalyx Makefile
# Commandes pratiques pour le développement et la production

.PHONY: help install run dev test clean config stats deploy

# Variables
PYTHON := python3
VENV := venv
ACTIVATE := . $(VENV)/bin/activate
PORT := 8000

# Couleurs
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

help: ## Affiche l'aide
	@echo "$(BLUE)╔═══════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║        Vocalyx - Makefile Help       ║$(NC)"
	@echo "$(BLUE)╚═══════════════════════════════════════╝$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""

install: ## Installe les dépendances
	@echo "$(BLUE)📦 Installation des dépendances...$(NC)"
	@$(PYTHON) -m venv $(VENV)
	@$(ACTIVATE) && pip install --upgrade pip
	@$(ACTIVATE) && pip install -r requirements.txt
	@echo "$(GREEN)✅ Installation terminée$(NC)"
	@echo ""
	@echo "$(YELLOW)Activation de l'environnement:$(NC)"
	@echo "  source $(VENV)/bin/activate"

run: ## Lance l'application en production
	@echo "$(BLUE)🚀 Lancement de Vocalyx...$(NC)"
	@$(ACTIVATE) && $(PYTHON) app.py

dev: ## Lance l'application en mode développement (auto-reload)
	@echo "$(BLUE)🔧 Mode développement (auto-reload)...$(NC)"
	@$(ACTIVATE) && $(PYTHON) app.py

test: ## Lance les tests
	@echo "$(BLUE)🧪 Lancement des tests...$(NC)"
	@chmod +x test_vocalyx.sh
	@./test_vocalyx.sh

test-file: ## Teste avec un fichier spécifique (usage: make test-file FILE=audio.wav)
	@if [ -z "$(FILE)" ]; then \
		echo "$(RED)❌ Erreur: Spécifiez un fichier avec FILE=chemin$(NC)"; \
		echo "Exemple: make test-file FILE=mon_audio.wav"; \
		exit 1; \
	fi
	@echo "$(BLUE)🧪 Test avec $(FILE)...$(NC)"
	@./test_vocalyx.sh $(FILE)

config: ## Affiche la configuration actuelle
	@echo "$(BLUE)⚙️  Configuration actuelle:$(NC)"
	@echo ""
	@$(ACTIVATE) && $(PYTHON) config_manager.py show

config-validate: ## Valide la configuration
	@echo "$(BLUE)✓ Validation de la configuration...$(NC)"
	@$(ACTIVATE) && $(PYTHON) config_manager.py validate

config-speed: ## Applique le preset vitesse
	@echo "$(YELLOW)🚀 Application du preset VITESSE...$(NC)"
	@$(ACTIVATE) && $(PYTHON) config_manager.py preset speed

config-balanced: ## Applique le preset équilibré (recommandé)
	@echo "$(YELLOW)⚖️  Application du preset ÉQUILIBRÉ...$(NC)"
	@$(ACTIVATE) && $(PYTHON) config_manager.py preset balanced

config-accuracy: ## Applique le preset précision
	@echo "$(YELLOW)🎯 Application du preset PRÉCISION...$(NC)"
	@$(ACTIVATE) && $(PYTHON) config_manager.py preset accuracy

stats: ## Affiche les statistiques de la base de données
	@echo "$(BLUE)📊 Statistiques de la base...$(NC)"
	@$(ACTIVATE) && $(PYTHON) cleanup_db.py --stats

clean-db: ## Nettoie la base (transcriptions > 30 jours)
	@echo "$(YELLOW)🧹 Nettoyage de la base (>30 jours)...$(NC)"
	@$(ACTIVATE) && $(PYTHON) cleanup_db.py --days 30 --incomplete --vacuum

clean-errors: ## Supprime uniquement les transcriptions en erreur
	@echo "$(YELLOW)🧹 Suppression des erreurs...$(NC)"
	@$(ACTIVATE) && $(PYTHON) cleanup_db.py --status error --vacuum

clean-all: ## Nettoie agressivement (>7 jours + erreurs)
	@echo "$(RED)⚠️  Nettoyage agressif (>7 jours)...$(NC)"
	@$(ACTIVATE) && $(PYTHON) cleanup_db.py --days 7 --status error --incomplete --vacuum

clean: ## Nettoie les fichiers temporaires
	@echo "$(BLUE)🧹 Nettoyage des fichiers temporaires...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type f -name "*.log" -delete 2>/dev/null || true
	@rm -rf .pytest_cache 2>/dev/null || true
	@rm -rf htmlcov 2>/dev/null || true
	@rm -rf tmp_uploads/* 2>/dev/null || true
	@echo "$(GREEN)✅ Nettoyage terminé$(NC)"

reset: clean ## Reset complet (supprime DB et config)
	@echo "$(RED)⚠️  RESET COMPLET - Suppression DB et config...$(NC)"
	@read -p "Êtes-vous sûr? (y/N): " confirm; \
	if [ "$$confirm" = "y" ]; then \
		rm -f transcriptions.db config.ini; \
		echo "$(GREEN)✅ Reset terminé$(NC)"; \
	else \
		echo "$(YELLOW)❌ Annulé$(NC)"; \
	fi

logs: ## Affiche les logs en temps réel
	@if [ -f logs/vocalyx.log ]; then \
		tail -f logs/vocalyx.log; \
	else \
		echo "$(YELLOW)⚠️  Pas de logs disponibles$(NC)"; \
	fi

docker-build: ## Construit l'image Docker
	@echo "$(BLUE)🐳 Construction de l'image Docker...$(NC)"
	@docker build -t vocalyx:latest .
	@echo "$(GREEN)✅ Image construite: vocalyx:latest$(NC)"

docker-run: ## Lance le conteneur Docker
	@echo "$(BLUE)🐳 Lancement du conteneur Docker...$(NC)"
	@docker run -d \
		-p $(PORT):8000 \
		-v $(PWD)/config.ini:/app/config.ini \
		-v $(PWD)/tmp_uploads:/app/tmp_uploads \
		-v $(PWD)/transcriptions.db:/app/transcriptions.db \
		--name vocalyx \
		vocalyx:latest
	@echo "$(GREEN)✅ Conteneur lancé sur http://localhost:$(PORT)$(NC)"

docker-stop: ## Arrête le conteneur Docker
	@echo "$(BLUE)🐳 Arrêt du conteneur...$(NC)"
	@docker stop vocalyx || true
	@docker rm vocalyx || true
	@echo "$(GREEN)✅ Conteneur arrêté$(NC)"

docker-logs: ## Affiche les logs Docker
	@docker logs -f vocalyx

deploy: ## Guide de déploiement
	@echo "$(BLUE)📚 Guide de déploiement:$(NC)"
	@echo ""
	@echo "1. $(YELLOW)Configuration:$(NC)"
	@echo "   make config-balanced"
	@echo ""
	@echo "2. $(YELLOW)Validation:$(NC)"
	@echo "   make config-validate"
	@echo ""
	@echo "3. $(YELLOW)Test:$(NC)"
	@echo "   make test"
	@echo ""
	@echo "4. $(YELLOW)Déploiement:$(NC)"
	@echo "   - Systemd: voir DEPLOYMENT.md"
	@echo "   - Docker: make docker-build && make docker-run"
	@echo ""
	@echo "$(GREEN)📖 Plus d'infos: DEPLOYMENT.md$(NC)"

check: ## Vérifie l'installation et la configuration
	@echo "$(BLUE)🔍 Vérification de l'installation...$(NC)"
	@echo ""
	@echo "$(YELLOW)1. Python version:$(NC)"
	@$(PYTHON) --version || echo "$(RED)❌ Python non trouvé$(NC)"
	@echo ""
	@echo "$(YELLOW)2. Environnement virtuel:$(NC)"
	@if [ -d "$(VENV)" ]; then \
		echo "$(GREEN)✅ venv existe$(NC)"; \
	else \
		echo "$(RED)❌ venv manquant (exécutez: make install)$(NC)"; \
	fi
	@echo ""
	@echo "$(YELLOW)3. FFmpeg:$(NC)"
	@which ffmpeg > /dev/null && echo "$(GREEN)✅ ffmpeg installé$(NC)" || echo "$(RED)❌ ffmpeg manquant$(NC)"
	@echo ""
	@echo "$(YELLOW)4. Configuration:$(NC)"
	@if [ -f "config.ini" ]; then \
		echo "$(GREEN)✅ config.ini existe$(NC)"; \
		$(ACTIVATE) && $(PYTHON) config_manager.py validate; \
	else \
		echo "$(YELLOW)⚠️  config.ini sera créé au premier lancement$(NC)"; \
	fi
	@echo ""
	@echo "$(YELLOW)5. Structure des dossiers:$(NC)"
	@if [ -d "templates" ]; then echo "$(GREEN)✅ templates/$(NC)"; else echo "$(RED)❌ templates/ manquant$(NC)"; fi
	@if [ -d "tmp_uploads" ]; then echo "$(GREEN)✅ tmp_uploads/$(NC)"; else echo "$(YELLOW)⚠️  tmp_uploads/ sera créé$(NC)"; fi

info: ## Affiche les informations du système
	@echo "$(BLUE)ℹ️  Informations système:$(NC)"
	@echo ""
	@echo "$(YELLOW)OS:$(NC)"
	@uname -s
	@echo ""
	@echo "$(YELLOW)CPU:$(NC)"
	@lscpu | grep "^Model name" || sysctl -n machdep.cpu.brand_string || echo "N/A"
	@echo ""
	@echo "$(YELLOW)Cores:$(NC)"
	@nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo "N/A"
	@echo ""
	@echo "$(YELLOW)RAM:$(NC)"
	@free -h 2>/dev/null | grep Mem || vm_stat 2>/dev/null | head -5 || echo "N/A"

urls: ## Affiche les URLs utiles
	@echo "$(BLUE)🔗 URLs utiles:$(NC)"
	@echo ""
	@echo "  $(GREEN)Dashboard:$(NC)    http://localhost:$(PORT)/dashboard"
	@echo "  $(GREEN)API Docs:$(NC)     http://localhost:$(PORT)/docs"
	@echo "  $(GREEN)Health:$(NC)       http://localhost:$(PORT)/health"
	@echo "  $(GREEN)Config:$(NC)       http://localhost:$(PORT)/config"
	@echo ""

.DEFAULT_GOAL := help