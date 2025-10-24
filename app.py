"""
vocalyx_production.py

FastAPI app avec configuration via fichier config.ini
Fix: Calcul correct de la durée audio
"""

import gc
import os
import time
import uuid
import json
import asyncio
import logging
import concurrent.futures
import soundfile as sf
import configparser
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple

from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Float, Text, Enum, DateTime, Integer
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from faster_whisper import WhisperModel
from pydub import AudioSegment
from pydub.effects import normalize
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Import du système de logging unifié
from logging_config import setup_logging, get_uvicorn_log_config

# ---------------------------------------------------------------------
# Configuration loading
# ---------------------------------------------------------------------
class Config:
    """Charge et gère la configuration depuis config.ini"""
    
    def __init__(self, config_file: str = "config.ini"):
        self.config = configparser.ConfigParser()
        self.config_file = config_file
        
        # Créer config par défaut si n'existe pas
        if not os.path.exists(config_file):
            self._create_default_config()
        
        self.config.read(config_file)
        self._load_settings()
        
    def _create_default_config(self):
        """Crée un fichier de configuration par défaut"""
        config = configparser.ConfigParser()
        
        config['WHISPER'] = {
            'model': 'small',
            'device': 'cpu',
            'compute_type': 'int8',
            'cpu_threads': '10',
            'language': 'fr'
        }
        
        config['PERFORMANCE'] = {
            'max_workers': '4',
            'segment_length_ms': '60000',
            'vad_enabled': 'true',
            'beam_size': '5',
            'temperature': '0.0'
        }
        
        config['LIMITS'] = {
            'max_file_size_mb': '100',
            'rate_limit_per_minute': '10',
            'allowed_extensions': 'wav,mp3,m4a,flac,ogg,webm'
        }
        
        config['PATHS'] = {
            'upload_dir': './tmp_uploads',
            'database_path': 'sqlite:///./transcriptions.db',
            'templates_dir': 'templates'
        }
        
        config['VAD'] = {
            'enabled': 'true',
            'min_silence_len': '500',
            'silence_thresh': '-40',
            'vad_threshold': '0.5',
            'min_speech_duration_ms': '250',
            'min_silence_duration_ms': '500'
        }
        
        config['LOGGING'] = {
            'level': 'INFO',
            'file_enabled': 'true',
            'file_path': 'logs/vocalyx.log',
            'colored': 'false'
        }
        
        with open(self.config_file, 'w') as f:
            config.write(f)
        
        logging.info(f"✅ Created default config file: {self.config_file}")
    
    def _load_settings(self):
        """Charge les paramètres dans des attributs"""
        # WHISPER
        self.model = self.config.get('WHISPER', 'model')
        self.device = self.config.get('WHISPER', 'device')
        self.compute_type = self.config.get('WHISPER', 'compute_type')
        self.cpu_threads = self.config.getint('WHISPER', 'cpu_threads')
        self.language = self.config.get('WHISPER', 'language')
        
        # PERFORMANCE
        self.max_workers = self.config.getint('PERFORMANCE', 'max_workers')
        self.segment_length_ms = self.config.getint('PERFORMANCE', 'segment_length_ms')
        self.vad_enabled = self.config.getboolean('PERFORMANCE', 'vad_enabled')
        self.beam_size = self.config.getint('PERFORMANCE', 'beam_size')
        self.temperature = self.config.getfloat('PERFORMANCE', 'temperature')
        
        # LIMITS
        self.max_file_size_mb = self.config.getint('LIMITS', 'max_file_size_mb')
        self.rate_limit = self.config.getint('LIMITS', 'rate_limit_per_minute')
        self.allowed_extensions = set(
            ext.strip() for ext in self.config.get('LIMITS', 'allowed_extensions').split(',')
        )
        
        # PATHS
        self.upload_dir = Path(self.config.get('PATHS', 'upload_dir'))
        self.database_path = self.config.get('PATHS', 'database_path')
        self.templates_dir = self.config.get('PATHS', 'templates_dir')
        
        # VAD
        self.vad_min_silence_len = self.config.getint('VAD', 'min_silence_len')
        self.vad_silence_thresh = self.config.getint('VAD', 'silence_thresh')
        self.vad_threshold = self.config.getfloat('VAD', 'vad_threshold')
        self.vad_min_speech_duration_ms = self.config.getint('VAD', 'min_speech_duration_ms')
        self.vad_min_silence_duration_ms = self.config.getint('VAD', 'min_silence_duration_ms')
        
        # Créer les répertoires
        self.upload_dir.mkdir(exist_ok=True)
    
    def reload(self):
        """Recharge la configuration depuis le fichier"""
        self.config.read(self.config_file)
        self._load_settings()
        logging.info("🔄 Configuration reloaded")


# Initialiser la configuration
config = Config()

# Configurer le logging uniforme pour toute l'application
logger = setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file="logs/vocalyx.log" if not os.getenv("NO_LOG_FILE") else None
)

# ---------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------
Base = declarative_base()
engine = create_engine(config.database_path, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


class Transcription(Base):
    __tablename__ = "transcriptions"
    id = Column(String, primary_key=True, index=True)
    status = Column(Enum("pending", "processing", "done", "error"), default="pending")
    language = Column(String, nullable=True)
    processing_time = Column(Float, nullable=True)
    duration = Column(Float, nullable=True)
    text = Column(Text, nullable=True)
    segments = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    segments_count = Column(Integer, nullable=True)
    vad_enabled = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)


Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------
executor = concurrent.futures.ThreadPoolExecutor(max_workers=config.max_workers)
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global whisper_model, executor

    # --- Startup ---
    logger.info(f"🚀 Loading Whisper model: {config.model} on {config.device}")
    whisper_model = WhisperModel(
        config.model,
        device=config.device,
        compute_type=config.compute_type,
        cpu_threads=config.cpu_threads
    )
    logger.info(f"✅ Whisper loaded | VAD: {config.vad_enabled} | Workers: {config.max_workers}")

    yield  # --- App runs here ---

    # --- Shutdown ---
    try:
        logger.info("🛑 Releasing Whisper model resources...")
        whisper_model = None
        gc.collect()

        if executor:
            logger.info("🧹 Shutting down thread pool executor...")
            executor.shutdown(wait=False, cancel_futures=True)
            executor = None
    except Exception as e:
        logger.warning(f"⚠️ Error while cleaning up resources: {e}")

app = FastAPI(
    title="Vocalyx API",
    description="Vocalyx transforme automatiquement les enregistrements de call centers en transcriptions enrichies et exploitables. "
                "\n\n**Configuration via config.ini**\n"
                "- Paramètres Whisper personnalisables\n"
                "- VAD (Voice Activity Detection) configurable\n"
                "- Limites et chemins configurables\n\n"
                "Vocalyx – La voix de vos clients, intelligemment exploitée",
    version="1.3.0",
    contact={"name": "Guilhem RICHARD", "email": "guilhem.l.richard@gmail.com"},
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

templates = Jinja2Templates(directory=config.templates_dir)

whisper_model = None

class TranscriptionResult(BaseModel):
    id: str
    status: str
    language: Optional[str] = None
    processing_time: Optional[float] = None
    duration: Optional[float] = None
    text: Optional[str] = None
    segments: Optional[list] = None
    error_message: Optional[str] = None
    segments_count: Optional[int] = None
    vad_enabled: Optional[bool] = None
    created_at: Optional[str] = None
    finished_at: Optional[str] = None


# ---------------------------------------------------------------------
# Database dependency
# ---------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------
# Audio Processing Utils
# ---------------------------------------------------------------------
def sanitize_filename(filename: str) -> str:
    """Nettoie le nom de fichier"""
    return "".join(c for c in filename if c.isalnum() or c in "._-")


def get_audio_duration(file_path: Path) -> float:
    """
    Obtient la durée réelle de l'audio en secondes.
    FIXE: Utilise soundfile pour une mesure précise.
    """
    try:
        info = sf.info(str(file_path))
        return round(info.duration, 2)
    except Exception as e:
        logger.warning(f"⚠️ Could not get duration with soundfile: {e}")
        # Fallback avec pydub
        try:
            audio = AudioSegment.from_file(str(file_path))
            return round(len(audio) / 1000.0, 2)
        except Exception as e2:
            logger.error(f"❌ Could not get duration: {e2}")
            return 0.0


def preprocess_audio(audio_path: Path) -> Path:
    """
    Pré-traite l'audio pour améliorer la qualité de transcription.
    """
    try:
        audio = AudioSegment.from_file(str(audio_path))
        
        # Normalisation du volume
        audio = normalize(audio)
        
        # Conversion en mono 16kHz
        audio = audio.set_channels(1).set_frame_rate(16000)
        
        # Export
        output_path = audio_path.parent / f"{audio_path.stem}_processed.wav"
        audio.export(str(output_path), format="wav")
        
        logger.info(f"✅ Audio preprocessed: {output_path.name}")
        return output_path
    except Exception as e:
        logger.warning(f"⚠️ Preprocessing failed, using original: {e}")
        return audio_path


def detect_speech_segments(audio_path: Path) -> List[Tuple[int, int]]:
    """
    Détecte les segments de parole (VAD).
    Retourne une liste de (start_ms, end_ms) des segments avec de la parole.
    """
    try:
        from pydub.silence import detect_nonsilent
        
        audio = AudioSegment.from_file(str(audio_path))
        
        speech_segments = detect_nonsilent(
            audio,
            min_silence_len=config.vad_min_silence_len,
            silence_thresh=config.vad_silence_thresh
        )
        
        if not speech_segments:
            return [(0, len(audio))]
        
        logger.info(f"🎤 VAD: Detected {len(speech_segments)} speech segments")
        return speech_segments
    except Exception as e:
        logger.warning(f"⚠️ VAD failed, using full audio: {e}")
        audio = AudioSegment.from_file(str(audio_path))
        return [(0, len(audio))]


def split_audio_intelligent(file_path: Path, use_vad: bool = True) -> List[Path]:
    """
    Découpe l'audio de manière intelligente.
    """
    segment_paths = []
    audio = AudioSegment.from_file(str(file_path))
    duration_ms = len(audio)
    duration_s = duration_ms / 1000
    
    try:
        # Audio court: pas de découpe
        if duration_s < 60:
            logger.info(f"📊 Audio court ({duration_s:.1f}s), pas de découpe")
            return [file_path]
        
        # VAD activé: découper selon les segments de parole
        if use_vad and config.vad_enabled:
            speech_segments = detect_speech_segments(file_path)
            
            # Grouper les segments proches (< 2s d'écart)
            merged_segments = []
            current_start, current_end = speech_segments[0]
            
            for start, end in speech_segments[1:]:
                if start - current_end < 2000:
                    current_end = end
                else:
                    merged_segments.append((current_start, current_end))
                    current_start, current_end = start, end
            merged_segments.append((current_start, current_end))
            
            # Exporter les segments
            for i, (start_ms, end_ms) in enumerate(merged_segments):
                segment = audio[start_ms:end_ms]
                segment_path = file_path.parent / f"{file_path.stem}_vad{i}.wav"
                segment.export(str(segment_path), format="wav")
                segment_paths.append(segment_path)
            
            logger.info(f"🎯 VAD: Created {len(segment_paths)} optimized segments")
            return segment_paths
        
        # Découpe classique par durée
        if duration_s < 180:
            # Audio moyen: découper en 2
            mid = duration_ms // 2
            for i, (start, end) in enumerate([(0, mid), (mid, duration_ms)]):
                segment = audio[start:end]
                segment_path = file_path.parent / f"{file_path.stem}_seg{i}.wav"
                segment.export(str(segment_path), format="wav")
                segment_paths.append(segment_path)
            logger.info(f"📊 Audio moyen ({duration_s:.1f}s), découpe en 2")
        else:
            # Audio long: découper par segments configurables
            for i, start_ms in enumerate(range(0, duration_ms, config.segment_length_ms)):
                segment = audio[start_ms:start_ms + config.segment_length_ms]
                segment_path = file_path.parent / f"{file_path.stem}_seg{i}.wav"
                segment.export(str(segment_path), format="wav")
                segment_paths.append(segment_path)
            logger.info(f"📊 Audio long ({duration_s:.1f}s), découpe en {len(segment_paths)}")
        
        return segment_paths
        
    except Exception as e:
        for seg_path in segment_paths:
            seg_path.unlink(missing_ok=True)
        raise e


def transcribe_segment(file_path: Path, translate: bool = False) -> tuple:
    """
    Transcrit un segment audio.
    Retourne: (text, segments_list, detected_language)
    """
    global whisper_model
    
    if whisper_model is None:
        raise RuntimeError("Whisper model not loaded")
    
    segments_list = []
    text_full = ""
    
    segments, info = whisper_model.transcribe(
        str(file_path),
        language=config.language,
        task="translate" if translate else "transcribe",
        beam_size=config.beam_size,
        best_of=config.beam_size,
        temperature=config.temperature,
        vad_filter=True,
        vad_parameters=dict(
            threshold=config.vad_threshold,
            min_speech_duration_ms=config.vad_min_speech_duration_ms,
            min_silence_duration_ms=config.vad_min_silence_duration_ms
        ),
        word_timestamps=False,
        condition_on_previous_text=True,
    )
    
    for seg in segments:
        segments_list.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip()
        })
        text_full += seg.text.strip() + " "
    
    return text_full.strip(), segments_list, info.language


async def run_transcription_optimized(
    transcription_id: str,
    file_path: Path,
    translate: bool,
    use_vad: bool = True
):
    """Transcription optimisée avec durée correcte"""
    db = SessionLocal()
    entry = db.query(Transcription).filter(Transcription.id == transcription_id).first()
    if not entry:
        db.close()
        return

    entry.status = "processing"
    entry.vad_enabled = 1 if use_vad else 0
    db.commit()
    
    segment_paths = []
    processed_path = None

    try:
        start_time = time.time()
        
        # 1. Obtenir la durée RÉELLE de l'audio original
        original_duration = get_audio_duration(file_path)
        logger.info(f"[{transcription_id}] 📏 Original audio duration: {original_duration}s")
        
        # 2. Pré-traitement audio
        processed_path = preprocess_audio(file_path)
        
        # 3. Découpe intelligente
        segment_paths = split_audio_intelligent(processed_path, use_vad=use_vad)
        logger.info(f"[{transcription_id}] 🔪 Created {len(segment_paths)} segments")

        # 4. Transcription parallèle
        loop = asyncio.get_running_loop()
        
        if len(segment_paths) == 1:
            results = [await loop.run_in_executor(
                executor, transcribe_segment, segment_paths[0], translate
            )]
        else:
            results = await asyncio.gather(*[
                loop.run_in_executor(executor, transcribe_segment, seg, translate)
                for seg in segment_paths
            ])

        # 5. Assemblage des résultats
        full_text = ""
        full_segments = []
        language_detected = None
        time_offset = 0.0

        for text, segments_list, lang in results:
            for seg in segments_list:
                seg["start"] = round(seg["start"] + time_offset, 2)
                seg["end"] = round(seg["end"] + time_offset, 2)
                full_segments.append(seg)
            
            if segments_list:
                time_offset = full_segments[-1]["end"]
            
            full_text += text + " "
            if not language_detected:
                language_detected = lang

        processing_time = round(time.time() - start_time, 3)
        speed_ratio = round(original_duration / processing_time, 2) if processing_time > 0 else 0

        # 6. Mise à jour DB avec durée CORRECTE
        entry.status = "done"
        entry.language = language_detected
        entry.processing_time = processing_time
        entry.duration = original_duration  # ✅ FIX: Utiliser la durée originale
        entry.text = full_text.strip()
        entry.segments = json.dumps(full_segments)
        entry.segments_count = len(full_segments)
        entry.finished_at = datetime.utcnow()
        db.commit()
        
        logger.info(
            f"[{transcription_id}] ✅ Completed: {len(full_segments)} segments | "
            f"Audio: {original_duration:.1f}s | Processing: {processing_time:.1f}s | "
            f"Speed: {speed_ratio}x realtime | VAD: {use_vad}"
        )

    except Exception as e:
        logger.exception(f"[{transcription_id}] ❌ Error: {e}")
        entry.status = "error"
        entry.error_message = str(e)
        entry.finished_at = datetime.utcnow()
        db.commit()

    finally:
        db.close()
        # Cleanup
        try:
            file_path.unlink(missing_ok=True)
            if processed_path and processed_path != file_path:
                processed_path.unlink(missing_ok=True)
            for seg_path in segment_paths:
                seg_path.unlink(missing_ok=True)
        except Exception as e:
            logger.error(f"[{transcription_id}] Cleanup error: {e}")


# ---------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------
@app.post("/transcribe", summary="Créer une transcription", tags=["Transcriptions"])
@limiter.limit(f"{config.rate_limit}/minute")
async def create_transcription(
    request: Request,
    file: UploadFile = File(...),
    translate: Optional[bool] = False,
    use_vad: Optional[bool] = True
):
    if whisper_model is None:
        raise HTTPException(503, "Service starting up. Please wait.")
    
    filename = sanitize_filename(file.filename or "upload")
    ext = filename.split('.')[-1].lower()
    
    if ext not in config.allowed_extensions:
        raise HTTPException(400, f"Unsupported: {ext}")

    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    
    if file_size_mb > config.max_file_size_mb:
        raise HTTPException(413, f"File too large: {file_size_mb:.2f}MB")

    transcription_id = str(uuid.uuid4())
    tmp_path = config.upload_dir / f"{transcription_id}_{filename}"
    
    with open(tmp_path, "wb") as fh:
        fh.write(content)

    db = SessionLocal()
    db.add(Transcription(
        id=transcription_id,
        status="pending",
        vad_enabled=1 if use_vad else 0,
        created_at=datetime.utcnow()
    ))
    db.commit()
    db.close()

    logger.info(f"[{transcription_id}] 📥 {filename} ({file_size_mb:.2f}MB) | VAD: {use_vad}")
    
    asyncio.create_task(run_transcription_optimized(transcription_id, tmp_path, translate, use_vad))

    return {"transcription_id": transcription_id, "status": "pending"}


@app.get("/transcribe/recent", response_model=List[TranscriptionResult], tags=["Transcriptions"])
def get_recent_transcriptions(limit: int = Query(10, ge=1, le=100), db: Session = Depends(get_db)):
    entries = db.query(Transcription).order_by(Transcription.created_at.desc()).limit(limit).all()
    
    results = []
    for entry in entries:
        segments = json.loads(entry.segments) if entry.segments else []
        results.append({
            "id": entry.id,
            "status": entry.status,
            "language": entry.language,
            "processing_time": float(entry.processing_time) if entry.processing_time else None,
            "duration": float(entry.duration) if entry.duration else None,
            "text": entry.text,
            "segments": segments,
            "error_message": entry.error_message,
            "segments_count": entry.segments_count,
            "vad_enabled": bool(entry.vad_enabled),
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
            "finished_at": entry.finished_at.isoformat() if entry.finished_at else None,
        })
    return results


@app.get("/transcribe/{transcription_id}", response_model=TranscriptionResult, tags=["Transcriptions"])
def get_transcription(transcription_id: str, db: Session = Depends(get_db)):
    entry = db.query(Transcription).filter(Transcription.id == transcription_id).first()
    if not entry:
        raise HTTPException(404, "Not found")
    
    segments = json.loads(entry.segments) if entry.segments else []
    return {
        "id": entry.id,
        "status": entry.status,
        "language": entry.language,
        "processing_time": float(entry.processing_time) if entry.processing_time else None,
        "duration": float(entry.duration) if entry.duration else None,
        "text": entry.text,
        "segments": segments,
        "error_message": entry.error_message,
        "segments_count": entry.segments_count,
        "vad_enabled": bool(entry.vad_enabled),
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "finished_at": entry.finished_at.isoformat() if entry.finished_at else None,
    }


@app.delete("/transcribe/{transcription_id}", tags=["Transcriptions"])
def delete_transcription(transcription_id: str, db: Session = Depends(get_db)):
    entry = db.query(Transcription).filter(Transcription.id == transcription_id).first()
    if not entry:
        raise HTTPException(404, "Not found")
    db.delete(entry)
    db.commit()
    return {"status": "deleted", "id": transcription_id}


@app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
def dashboard(request: Request, limit: int = 10, db: Session = Depends(get_db)):
    entries = db.query(Transcription).order_by(Transcription.created_at.desc()).limit(limit).all()
    return templates.TemplateResponse("dashboard.html", {"request": request, "entries": entries})


@app.get("/config", tags=["System"])
def get_config():
    """Retourne la configuration actuelle (sans données sensibles)"""
    return {
        "whisper": {
            "model": config.model,
            "device": config.device,
            "compute_type": config.compute_type,
            "language": config.language,
        },
        "performance": {
            "max_workers": config.max_workers,
            "segment_length_ms": config.segment_length_ms,
            "vad_enabled": config.vad_enabled,
        },
        "limits": {
            "max_file_size_mb": config.max_file_size_mb,
            "rate_limit_per_minute": config.rate_limit,
            "allowed_extensions": list(config.allowed_extensions),
        }
    }


@app.post("/config/reload", tags=["System"])
def reload_config():
    """Recharge la configuration depuis le fichier"""
    try:
        config.reload()
        return {"status": "success", "message": "Configuration reloaded"}
    except Exception as e:
        raise HTTPException(500, f"Failed to reload config: {str(e)}")


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy" if whisper_model else "starting",
        "model_loaded": whisper_model is not None,
        "timestamp": datetime.utcnow().isoformat(),
        "config_file": "config.ini"
    }


if __name__ == "__main__":
    import uvicorn
    
    # Obtenir la configuration de logging pour Uvicorn
    log_config = get_uvicorn_log_config(
        log_level=os.getenv("LOG_LEVEL", "INFO")
    )
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=log_config
    )