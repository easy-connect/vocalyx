#!/bin/bash
set -e

echo "==== Vocalyx Installation Script ===="

# Vérifie Python 3.11+
if ! command -v python3 &>/dev/null; then
    echo "Python 3 n'est pas installé."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if [[ "$PYTHON_VERSION" < "3.11" ]]; then
    echo "Python 3.11+ requis. Version actuelle : $PYTHON_VERSION"
    exit 1
fi

# Création du venv
if [ ! -d "venv" ]; then
    echo "Création du venv..."
    python3 -m venv venv
fi

# Activation du venv
source venv/bin/activate

# Mise à jour pip
pip install --upgrade pip

# Installation des dépendances
echo "Installation des dépendances..."
pip install -r requirements.txt

# Création des dossiers nécessaires
mkdir -p tmp_uploads templates

echo "==== Installation terminée ===="
echo "Pour activer le venv : source venv/bin/activate"
