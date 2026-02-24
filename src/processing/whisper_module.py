"""
VoiceToVision - Módulo Whisper
Transcripción de audio usando OpenAI Whisper (local o API).
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, Callable
import whisper
import torch


class WhisperTranscriber:
    """
    Transcribe audio usando el modelo Whisper de OpenAI.
    Soporta ejecución local y detección automática de idioma.
    """
    
    # Modelos disponibles (de más rápido a más preciso)
    MODELS = {
        "tiny": "tiny",      # ~39 MB, ~32x speed
        "base": "base",      # ~74 MB, ~16x speed
        "small": "small",    # ~244 MB, ~6x speed
        "medium": "medium",  # ~769 MB, ~2x speed
        "large": "large",    # ~1550 MB, 1x speed
        "large-v2": "large-v2",
        "large-v3": "large-v3"
    }
    
    def __init__(self, config: Dict, logger):
        """
        Inicializa el transcriptor Whisper.
        
        Args:
            config: Configuración del sistema
            logger: Instancia de SystemLogger
        """
        self.config = config
        self.whisper_config = config.get("whisper", {})
        self.logger = logger
        
        # Configuración del modelo
        self.model_name = self.whisper_config.get("model", "base")
        self.language = self.whisper_config.get("language", "auto")
        
        # Modelo cargado (lazy loading)
        self._model = None
        self._device = None
        
        self.logger.info(f"Whisper configurado: modelo={self.model_name}, lang={self.language}")
    
    def _load_model(self):
        """
        Carga el modelo Whisper en memoria (lazy loading).
        """
        if self._model is not None:
            return
        
        self.logger.info(f"Cargando modelo Whisper: {self.model_name}")
        
        # Determinar dispositivo (CUDA si disponible, sino CPU)
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        
        self.logger.info(f"Dispositivo: {self._device}")
        
        try:
            self._model = whisper.load_model(self.model_name).to(self._device)
            self.logger.info(f"Modelo {self.model_name} cargado exitosamente")
        except Exception as e:
            self.logger.error(f"Error cargando modelo Whisper: {e}")
            raise
    
    async def transcribe(self,
                        audio_path: Path,
                        progress_callback: Optional[Callable] = None) -> Dict:
        """
        Transcribe un archivo de audio.
        
        Args:
            audio_path: Ruta al archivo de audio (preferiblemente WAV 16kHz)
            progress_callback: Función opcional para reportar progreso
        
        Returns:
            Diccionario con transcripción y metadatos
        """
        self.logger.info(f"Iniciando transcripción: {audio_path.name}")
        
        # Verificar que existe el archivo
        if not audio_path.exists():
            return {
                "success": False,
                "error": "Archivo de audio no encontrado",
                "file_path": str(audio_path)
            }
        
        # Cargar modelo si es necesario
        if self._model is None:
            try:
                # Cargar en thread separado para no bloquear
                await asyncio.to_thread(self._load_model)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"No se pudo cargar el modelo Whisper: {str(e)}",
                    "file_path": str(audio_path)
                }
        
        # Realizar transcripción en thread separado
        try:
            result = await asyncio.to_thread(
                self._transcribe_sync,
                str(audio_path),
                progress_callback
            )
            
            self.logger.info(
                f"Transcripción completada: {len(result['text'])} caracteres, "
                f"idioma: {result['language']}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error en transcripción: {e}")
            return {
                "success": False,
                "error": f"Error durante la transcripción: {str(e)}",
                "file_path": str(audio_path)
            }
    
    def _transcribe_sync(self,
                         audio_path: str,
                         progress_callback: Optional[Callable] = None) -> Dict:
        """
        Versión síncrona de la transcripción (ejecutada en thread).
        
        Args:
            audio_path: Ruta al archivo
            progress_callback: Callback de progreso
        
        Returns:
            Diccionario con resultados
        """
        # Opciones de transcripción
        options = {
            "verbose": False,
            "fp16": self._device == "cuda"  # Solo usar FP16 en GPU
        }
        
        # Especificar idioma si no es auto
        if self.language != "auto":
            options["language"] = self.language
        
        # Realizar transcripción
        result = self._model.transcribe(audio_path, **options)
        
        # Extraer información relevante
        transcription = {
            "success": True,
            "text": result["text"].strip(),
            "language": result.get("language", "unknown"),
            "duration": result.get("duration", 0),
            "segments": []
        }
        
        # Procesar segmentos si existen
        if "segments" in result:
            for seg in result["segments"]:
                transcription["segments"].append({
                    "start": seg.get("start", 0),
                    "end": seg.get("end", 0),
                    "text": seg.get("text", "").strip(),
                    "confidence": seg.get("avg_logprob", 0)
                })
        
        # Calcular confianza promedio
        if transcription["segments"]:
            avg_confidence = sum(
                s["confidence"] for s in transcription["segments"]
            ) / len(transcription["segments"])
            transcription["avg_confidence"] = avg_confidence
        
        return transcription
    
    async def detect_language(self, audio_path: Path) -> Dict:
        """
        Detecta el idioma de un audio sin transcribir completamente.
        
        Args:
            audio_path: Ruta al archivo de audio
        
        Returns:
            Diccionario con idioma detectado y confianza
        """
        if not audio_path.exists():
            return {
                "success": False,
                "error": "Archivo no encontrado"
            }
        
        # Cargar modelo si es necesario
        if self._model is None:
            await asyncio.to_thread(self._load_model)
        
        try:
            # Cargar audio y detectar idioma
            result = await asyncio.to_thread(
                lambda: self._model.detect_language(str(audio_path))
            )
            
            # El resultado es una tupla (probs, tokens)
            if isinstance(result, tuple) and len(result) > 0:
                probs = result[0]
                # Obtener idioma con mayor probabilidad
                detected_lang = max(probs, key=probs.get)
                confidence = probs[detected_lang]
                
                return {
                    "success": True,
                    "language": detected_lang,
                    "confidence": float(confidence),
                    "all_probabilities": {
                        k: float(v) for k, v in list(probs.items())[:5]
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "No se pudo detectar el idioma"
                }
                
        except Exception as e:
            self.logger.error(f"Error detectando idioma: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def transcribe_with_timestamps(self,
                                          audio_path: Path) -> Dict:
        """
        Transcribe con timestamps detallados para cada segmento.
        
        Args:
            audio_path: Ruta al archivo
        
        Returns:
            Transcripción con timestamps
        """
        result = await self.transcribe(audio_path)
        
        if not result["success"]:
            return result
        
        # Formatear con timestamps
        formatted_segments = []
        for seg in result.get("segments", []):
            start = self._format_timestamp(seg["start"])
            end = self._format_timestamp(seg["end"])
            formatted_segments.append(
                f"[{start} -> {end}] {seg['text']}"
            )
        
        result["formatted_with_timestamps"] = "\\n".join(formatted_segments)
        
        return result
    
    def _format_timestamp(self, seconds: float) -> str:
        """
        Formatea segundos a timestamp legible.
        
        Args:
            seconds: Tiempo en segundos
        
        Returns:
            String formateado (MM:SS o HH:MM:SS)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    def get_model_info(self) -> Dict:
        """
        Retorna información sobre el modelo cargado.
        
        Returns:
            Diccionario con información del modelo
        """
        return {
            "model_name": self.model_name,
            "device": self._device or "not_loaded",
            "loaded": self._model is not None,
            "available_models": list(self.MODELS.keys()),
            "language_setting": self.language
        }
    
    async def unload_model(self):
        """
        Descarga el modelo de memoria para liberar recursos.
        """
        if self._model is not None:
            self.logger.info("Descargando modelo Whisper de memoria")
            del self._model
            self._model = None
            
            # Forzar garbage collection
            import gc
            gc.collect()
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self.logger.info("Modelo descargado")
    
    @staticmethod
    def check_cuda_available() -> Dict:
        """
        Verifica disponibilidad de CUDA para aceleración GPU.
        
        Returns:
            Información sobre CUDA
        """
        return {
            "cuda_available": torch.cuda.is_available(),
            "cuda_devices": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "current_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        }
