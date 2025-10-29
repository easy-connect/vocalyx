#!/bin/bash
# Récupère le dernier ID done et lance l'enrichissement
TRANS_ID=$(curl -s http://localhost:8000/api/transcribe/recent | jq -r '.[0].id')
echo "Enrichissement de: $TRANS_ID"
curl -X POST "http://localhost:8001/api/enrichment/trigger/$TRANS_ID"
echo "Attente 40s..."
sleep 40
curl -s "http://localhost:8001/api/enrichment/$TRANS_ID" | jq