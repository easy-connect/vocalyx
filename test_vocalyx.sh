#!/bin/bash
# test_vocalyx.sh - Script de test pour Vocalyx

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

API_URL="${API_URL:-http://localhost:8000}"
TEST_FILE="${1:-test_audio.wav}"

echo -e "${BLUE}╔═══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Vocalyx API Test Suite             ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════╝${NC}"
echo ""

# Fonction d'aide
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Test 1: Health Check
echo -e "\n${YELLOW}[1/6] Health Check${NC}"
if curl -s "${API_URL}/health" | grep -q "healthy"; then
    print_success "API is healthy"
else
    print_error "API is not responding"
    exit 1
fi

# Test 2: Configuration
echo -e "\n${YELLOW}[2/6] Configuration Check${NC}"
CONFIG=$(curl -s "${API_URL}/config")
MODEL=$(echo $CONFIG | grep -o '"model":"[^"]*"' | cut -d'"' -f4)
VAD=$(echo $CONFIG | grep -o '"vad_enabled":[^,}]*' | cut -d':' -f2)
print_info "Model: ${MODEL}"
print_info "VAD enabled: ${VAD}"

# Test 3: Vérifier le fichier audio
echo -e "\n${YELLOW}[3/6] Audio File Check${NC}"
if [ ! -f "$TEST_FILE" ]; then
    print_warning "Test file not found: $TEST_FILE"
    print_info "Creating a 5-second test audio file..."
    
    # Créer un fichier audio test avec ffmpeg (ton de 440Hz pendant 5s)
    if command -v ffmpeg &> /dev/null; then
        ffmpeg -f lavfi -i "sine=frequency=440:duration=5" -ac 1 -ar 16000 test_audio.wav -y 2>&1 | grep -v "^$"
        TEST_FILE="test_audio.wav"
        print_success "Test audio created: test_audio.wav"
    else
        print_error "ffmpeg not found. Please provide an audio file."
        echo "Usage: $0 <path_to_audio_file.wav>"
        exit 1
    fi
fi

FILE_SIZE=$(du -h "$TEST_FILE" | cut -f1)
print_success "Using audio file: $TEST_FILE (${FILE_SIZE})"

# Test 4: Upload & Transcription
echo -e "\n${YELLOW}[4/6] Transcription Test${NC}"
print_info "Uploading file..."

START_TIME=$(date +%s)
RESPONSE=$(curl -s -X POST "${API_URL}/transcribe" \
    -F "file=@${TEST_FILE}" \
    -F "use_vad=true")

TRANSCRIPTION_ID=$(echo $RESPONSE | grep -o '"transcription_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TRANSCRIPTION_ID" ]; then
    print_error "Failed to create transcription"
    echo "Response: $RESPONSE"
    exit 1
fi

print_success "Transcription created: ${TRANSCRIPTION_ID}"

# Test 5: Polling status
echo -e "\n${YELLOW}[5/6] Monitoring Transcription${NC}"
print_info "Waiting for completion..."

MAX_WAIT=300  # 5 minutes max
ELAPSED=0
STATUS="pending"

while [ "$STATUS" != "done" ] && [ "$STATUS" != "error" ] && [ $ELAPSED -lt $MAX_WAIT ]; do
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    
    STATUS_RESPONSE=$(curl -s "${API_URL}/transcribe/${TRANSCRIPTION_ID}")
    STATUS=$(echo $STATUS_RESPONSE | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    
    if [ "$STATUS" = "processing" ]; then
        echo -ne "\r${BLUE}Processing... ${ELAPSED}s${NC}"
    elif [ "$STATUS" = "done" ]; then
        echo -ne "\r"
        print_success "Transcription completed in ${ELAPSED}s"
        break
    elif [ "$STATUS" = "error" ]; then
        echo -ne "\r"
        print_error "Transcription failed"
        ERROR=$(echo $STATUS_RESPONSE | grep -o '"error_message":"[^"]*"' | cut -d'"' -f4)
        echo "Error: $ERROR"
        exit 1
    fi
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    print_error "Timeout waiting for transcription"
    exit 1
fi

END_TIME=$(date +%s)
TOTAL_TIME=$((END_TIME - START_TIME))

# Test 6: Résultats
echo -e "\n${YELLOW}[6/6] Results${NC}"

RESULT=$(curl -s "${API_URL}/transcribe/${TRANSCRIPTION_ID}")

# Extraire les informations
TEXT=$(echo $RESULT | grep -o '"text":"[^"]*"' | cut -d'"' -f4 | head -c 100)
DURATION=$(echo $RESULT | grep -o '"duration":[0-9.]*' | cut -d':' -f2)
PROC_TIME=$(echo $RESULT | grep -o '"processing_time":[0-9.]*' | cut -d':' -f2)
LANGUAGE=$(echo $RESULT | grep -o '"language":"[^"]*"' | cut -d'"' -f4)
SEGMENTS=$(echo $RESULT | grep -o '"segments_count":[0-9]*' | cut -d':' -f2)

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  TRANSCRIPTION RESULTS                 ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BLUE}ID:${NC}               $TRANSCRIPTION_ID"
echo -e "  ${BLUE}Language:${NC}         $LANGUAGE"
echo -e "  ${BLUE}Duration:${NC}         ${DURATION}s"
echo -e "  ${BLUE}Processing time:${NC}  ${PROC_TIME}s"
echo -e "  ${BLUE}Total time:${NC}       ${TOTAL_TIME}s"
echo -e "  ${BLUE}Segments:${NC}         $SEGMENTS"

if [ ! -z "$DURATION" ] && [ ! -z "$PROC_TIME" ]; then
    SPEED=$(echo "scale=2; $DURATION / $PROC_TIME" | bc)
    echo -e "  ${BLUE}Speed:${NC}            ${SPEED}x realtime"
fi

echo ""
echo -e "  ${BLUE}Text preview:${NC}"
echo -e "  ${NC}\"${TEXT}...\"${NC}"
echo ""

# Performance rating
if [ ! -z "$SPEED" ]; then
    SPEED_INT=$(echo $SPEED | cut -d'.' -f1)
    if [ "$SPEED_INT" -gt 10 ]; then
        echo -e "  ${GREEN}★★★★★ Excellent performance!${NC}"
    elif [ "$SPEED_INT" -gt 5 ]; then
        echo -e "  ${GREEN}★★★★☆ Good performance${NC}"
    elif [ "$SPEED_INT" -gt 2 ]; then
        echo -e "  ${YELLOW}★★★☆☆ Average performance${NC}"
    else
        echo -e "  ${RED}★★☆☆☆ Slow performance${NC}"
        print_warning "Consider using a smaller model or enabling VAD"
    fi
fi

echo ""
print_success "All tests passed!"
echo ""
echo -e "${BLUE}View full details:${NC} ${API_URL}/transcribe/${TRANSCRIPTION_ID}"
echo -e "${BLUE}Dashboard:${NC}        ${API_URL}/dashboard"
echo -e "${BLUE}API Docs:${NC}         ${API_URL}/docs"
echo ""

# Cleanup option
read -p "Delete test transcription? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    curl -s -X DELETE "${API_URL}/transcribe/${TRANSCRIPTION_ID}" > /dev/null
    print_success "Test transcription deleted"
fi

exit 0