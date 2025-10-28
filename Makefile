# Vocalyx Makefile - Version restructurée
# ==========================================

.PHONY: help install install-enrichment test test-transcribe test-enrich run run-transcribe run-enrichment dev stop clean clean-db clean-all docs

# Variables
PYTHON := python3
PIP := $(PYTHON) -m pip
VENV := venv
BIN := $(VENV)/bin
PYTHON_BIN := $(BIN)/python3
PIP_BIN := $(BIN)/pip3

# Couleurs
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m

# ==========================================
# HELP
# ==========================================

help:
	@echo "$(BLUE)╔═══════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║          Vocalyx - Makefile Commands                      ║$(NC)"
	@echo "$(BLUE)╚═══════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)📦 Installation:$(NC)"
	@echo "  make install              - Installer Vocalyx (transcription)"
	@echo "  make install-enrichment   - Installer module enrichissement"
	@echo "  make install-all          - Tout installer"
	@echo ""
	@echo "$(YELLOW)🚀 Exécution:$(NC)"
	@echo "  make run                  - Lancer l'API principale"
	@echo "  make run-transcribe       - Lancer uniquement transcription"
	@echo "  make run-enrichment       - Lancer le worker enrichissement"
	@echo "  make run-all              - Lancer API + worker enrichissement"
	@echo "  make dev                  - Mode développement (auto-reload)"
	@echo "  make stop                 - Arrêter tous les services"
	@echo ""
	@echo "$(YELLOW)🧪 Tests:$(NC)"
	@echo "  make test                 - Tests complets"
	@echo "  make test-transcribe      - Test transcription"
	@echo "  make test-enrich          - Test enrichissement"
	@echo "  make check                - Vérifier l'installation"
	@echo ""
	@echo "$(YELLOW)⚙️  Configuration:$(NC)"
	@echo "  make config               - Afficher la config"
	@echo "  make config-validate      - Valider config.ini"
	@echo "  make config-speed         - Preset vitesse"
	@echo "  make config-balanced      - Preset équilibré"
	@echo "  make config-accuracy      - Preset précision"
	@echo ""
	@echo "$(YELLOW)🗄️  Base de données:$(NC)"
	@echo "  make db-stats             - Statistiques DB"
	@echo "  make db-migrate           - Créer tables enrichment"
	@echo "  make clean-db             - Nettoyer DB (>30 jours)"
	@echo "  make clean-errors         - Supprimer erreurs"
	@echo "  make backup-db            - Backup DB"
	@echo ""
	@echo "$(YELLOW)🧹 Nettoyage:$(NC)"
	@echo "  make clean                - Nettoyer fichiers temp"
	@echo "  make clean-all            - Nettoyage complet"
	@echo "  make clean-logs           - Supprimer logs"
	@echo ""
	@echo "$(YELLOW)📚 Documentation:$(NC)"
	@echo "  make docs                 - Ouvrir documentation"
	@echo "  make urls                 - Afficher URLs utiles"
	@echo "  make info                 - Infos système"
	@echo ""
	@echo "$(YELLOW)🔧 Modèles LLM:$(NC)"
	@echo "  make download-model       - Télécharger modèle recommandé"
	@echo "  make list-models          - Lister modèles disponibles"
	@echo ""

# ==========================================
# INSTALLATION
# ==========================================

install:
	@echo "$(GREEN)📦 Installation de Vocalyx (transcription)...$(NC)"
	@if [ ! -d "$(VENV)" ]; then \
		echo "$(YELLOW)Création environnement virtuel...$(NC)"; \
		$(PYTHON) -m venv $(VENV); \
	fi
	@echo "$(YELLOW)Installation dépendances...$(NC)"
	@$(PIP_BIN) install --upgrade pip
	@$(PIP_BIN) install -r requirements-transcribe.txt
	@$(PIP_BIN) install -r requirements-enrichment.txt
	@mkdir -p tmp_uploads logs models
	@echo "$(GREEN)✅ Installation terminée !$(NC)"
	@echo ""
	@echo "$(BLUE)Prochaines étapes :$(NC)"
	@echo "  1. $(YELLOW)make config-balanced$(NC) - Configurer"
	@echo "  2. $(YELLOW)make run$(NC) - Lancer l'API"
	@echo "  3. $(YELLOW)make test$(NC) - Tester"

install-enrichment:
	@echo "$(GREEN)🎨 Installation module enrichissement...$(NC)"
	@if [ ! -d "$(VENV)" ]; then \
		echo "$(RED)❌ Vocalyx doit être installé d'abord !$(NC)"; \
		echo "$(YELLOW)Exécutez: make install$(NC)"; \
		exit 1; \
	fi
	@$(PIP_BIN) install llama-cpp-python psutil python-json-logger
	@echo "$(GREEN)✅ Module enrichissement installé !$(NC)"
	@echo ""
	@echo "$(BLUE)Prochaines étapes :$(NC)"
	@echo "  1. $(YELLOW)make download-model$(NC) - Télécharger modèle LLM"
	@echo "  2. $(YELLOW)make db-migrate$(NC) - Créer tables"
	@echo "  3. $(YELLOW)make run-enrichment$(NC) - Lancer worker"

install-all: install install-enrichment
	@echo "$(GREEN)✅ Installation complète terminée !$(NC)"

# ==========================================
# EXÉCUTION
# ==========================================

run:
	@echo "$(GREEN)🚀 Lancement Vocalyx API...$(NC)"
	@$(PYTHON_BIN) app.py

run-transcribe: run

run-enrichment:
	@echo "$(GREEN)🎨 Lancement worker enrichissement...$(NC)"
	@if [ ! -f "run_enrichment.py" ]; then \
		echo "$(RED)❌ run_enrichment.py non trouvé !$(NC)"; \
		exit 1; \
	fi
	@$(PYTHON_BIN) run_enrichment.py

run-all:
	@echo "$(GREEN)🚀 Lancement Vocalyx complet (API + Worker)...$(NC)"
	@$(PYTHON_BIN) app.py & \
	sleep 5 && \
	$(PYTHON_BIN) run_enrichment.py &
	@echo "$(GREEN)✅ Services démarrés !$(NC)"
	@echo "$(YELLOW)Pour arrêter: make stop$(NC)"

dev:
	@echo "$(GREEN)🔧 Mode développement (auto-reload)...$(NC)"
	@$(BIN)/uvicorn app:app --reload --host 0.0.0.0 --port 8000

stop:
	@echo "$(YELLOW)🛑 Arrêt des services...$(NC)"
	@pkill -f "app:app" || true
	@pkill -f "run_enrichment.py" || true
	@echo "$(GREEN)✅ Services arrêtés$(NC)"

# ==========================================
# TESTS
# ==========================================

test:
	@echo "$(GREEN)🧪 Tests complets...$(NC)"
	@bash scripts/test_vocalyx.sh

test-transcribe:
	@echo "$(GREEN)🧪 Test transcription...$(NC)"
	@if [ -z "$(FILE)" ]; then \
		bash scripts/test_vocalyx.sh; \
	else \
		bash scripts/test_vocalyx.sh $(FILE); \
	fi

test-enrich:
	@echo "$(GREEN)🧪 Test enrichissement...$(NC)"
	@$(PYTHON_BIN) -c "from enrichment.worker import test_enrichment; test_enrichment()" || \
		echo "$(YELLOW)⚠️  Test enrichissement non encore implémenté$(NC)"

check:
	@echo "$(BLUE)🔍 Vérification installation...$(NC)"
	@echo ""
	@echo "$(YELLOW)Python:$(NC)"
	@$(PYTHON) --version || echo "$(RED)❌ Python non trouvé$(NC)"
	@echo ""
	@echo "$(YELLOW)FFmpeg:$(NC)"
	@ffmpeg -version | head -1 || echo "$(RED)❌ FFmpeg non trouvé$(NC)"
	@echo ""
	@echo "$(YELLOW)Environnement virtuel:$(NC)"
	@if [ -d "$(VENV)" ]; then \
		echo "$(GREEN)✅ venv existe$(NC)"; \
	else \
		echo "$(RED)❌ venv n'existe pas$(NC)"; \
	fi
	@echo ""
	@echo "$(YELLOW)Dépendances:$(NC)"
	@$(PIP_BIN) list | grep -E "(fastapi|faster-whisper|uvicorn)" || echo "$(RED)❌ Dépendances manquantes$(NC)"
	@echo ""
	@echo "$(YELLOW)Fichiers:$(NC)"
	@ls -lh config.ini database.py app.py 2>/dev/null || echo "$(RED)❌ Fichiers manquants$(NC)"

# ==========================================
# CONFIGURATION
# ==========================================

config:
	@$(PYTHON_BIN) scripts/config_manager.py show

config-validate:
	@$(PYTHON_BIN) scripts/config_manager.py validate

config-speed:
	@$(PYTHON_BIN) scripts/config_manager.py preset speed
	@echo "$(GREEN)✅ Preset vitesse appliqué$(NC)"

config-balanced:
	@$(PYTHON_BIN) scripts/config_manager.py preset balanced
	@echo "$(GREEN)✅ Preset équilibré appliqué$(NC)"

config-accuracy:
	@$(PYTHON_BIN) scripts/config_manager.py preset accuracy
	@echo "$(GREEN)✅ Preset précision appliqué$(NC)"

# ==========================================
# BASE DE DONNÉES
# ==========================================

db-stats:
	@$(PYTHON_BIN) scripts/cleanup_db.py --stats

db-migrate:
	@echo "$(GREEN)🗄️  Migration base de données (tables enrichment)...$(NC)"
	@$(PYTHON_BIN) -c "from enrichment.models import create_tables; create_tables()"
	@echo "$(GREEN)✅ Tables créées !$(NC)"

clean-db:
	@$(PYTHON_BIN) scripts/cleanup_db.py --days 30 --incomplete --vacuum

clean-errors:
	@$(PYTHON_BIN) scripts/cleanup_db.py --status error

backup-db:
	@mkdir -p backups
	@cp transcriptions.db backups/transcriptions_$(shell date +%Y%m%d_%H%M%S).db
	@echo "$(GREEN)✅ Backup créé dans backups/$(NC)"

# ==========================================
# NETTOYAGE
# ==========================================

clean:
	@echo "$(YELLOW)🧹 Nettoyage fichiers temporaires...$(NC)"
	@rm -rf tmp_uploads/*
	@rm -rf __pycache__ */__pycache__ */*/__pycache__
	@rm -rf .pytest_cache
	@find . -name "*.pyc" -delete
	@find . -name "*.pyo" -delete
	@echo "$(GREEN)✅ Nettoyage terminé$(NC)"

clean-logs:
	@echo "$(YELLOW)🧹 Suppression logs...$(NC)"
	@rm -rf logs/*.log
	@echo "$(GREEN)✅ Logs supprimés$(NC)"

clean-all: clean clean-logs
	@echo "$(YELLOW)🧹 Nettoyage complet...$(NC)"
	@rm -rf $(VENV)
	@echo "$(GREEN)✅ Nettoyage complet terminé$(NC)"

# ==========================================
# MODÈLES LLM
# ==========================================

download-model:
	@echo "$(GREEN)📥 Téléchargement modèle recommandé (Mistral-7B-Instruct Q4_K_M)...$(NC)"
	@mkdir -p models
	@cd models && wget -c https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.3-GGUF/resolve/main/mistral-7b-instruct-v0.3.Q4_K_M.gguf
	@echo "$(GREEN)✅ Modèle téléchargé dans models/$(NC)"

list-models:
	@echo "$(BLUE)📋 Modèles disponibles dans models/:$(NC)"
	@ls -lh models/*.gguf 2>/dev/null || echo "$(YELLOW)Aucun modèle téléchargé$(NC)"

# ==========================================
# DOCUMENTATION
# ==========================================

docs:
	@if command -v xdg-open &> /dev/null; then \
		xdg-open docs/README.md; \
	elif command -v open &> /dev/null; then \
		open docs/README.md; \
	else \
		cat docs/README.md; \
	fi

urls:
	@echo "$(BLUE)🌐 URLs utiles :$(NC)"
	@echo ""
	@echo "  $(YELLOW)Dashboard:$(NC)     http://localhost:8000/dashboard"
	@echo "  $(YELLOW)API Docs:$(NC)      http://localhost:8000/docs"
	@echo "  $(YELLOW)Health:$(NC)        http://localhost:8000/health"
	@echo "  $(YELLOW)Config:$(NC)        http://localhost:8000/config"
	@echo ""

info:
	@echo "$(BLUE)ℹ️  Informations système :$(NC)"
	@echo ""
	@echo "$(YELLOW)OS:$(NC)"
	@uname -a
	@echo ""
	@echo "$(YELLOW)CPU:$(NC)"
	@lscpu | grep "Model name" || sysctl -n machdep.cpu.brand_string
	@echo ""
	@echo "$(YELLOW)RAM:$(NC)"
	@free -h | grep Mem || vm_stat | grep "Pages free"
	@echo ""
	@echo "$(YELLOW)Disque:$(NC)"
	@df -h . | tail -1
	@echo ""

# ==========================================
# DÉVELOPPEMENT
# ==========================================

lint:
	@echo "$(GREEN)🔍 Linting code...$(NC)"
	@$(PIP_BIN) install flake8 black || true
	@$(BIN)/flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	@$(BIN)/black --check .

format:
	@echo "$(GREEN)✨ Formatage code...$(NC)"
	@$(PIP_BIN) install black || true
	@$(BIN)/black .

# ==========================================
# DOCKER (optionnel)
# ==========================================

docker-build:
	@docker build -t vocalyx:latest .

docker-run:
	@docker run -d -p 8000:8000 -v $(PWD)/config.ini:/app/config.ini --name vocalyx vocalyx:latest

docker-stop:
	@docker stop vocalyx && docker rm vocalyx

docker-logs:
	@docker logs -f vocalyx