# MIT License
# Copyright (c) 2026 VoiceToVision
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
VoiceToVision - Procesador de Audio
Validación, conversión y manejo de archivos de audio.
"""


import os
import asyncio
import tempfile
from pathlib import Path
from typing import Optional, Dict, Tuple, BinaryIO
import aiofiles
import ffmpeg
from pydub import AudioSegment
import json


class AudioProcessor:
    """
    Procesa archivos de audio: validación, conversión,
    limpieza y preparación para transcripción.
    """
    
    # Formatos soportados para entrada
    SUPPORTED_INPUT = {'.mp3', '.wav', '.ogg', '.m4a', '.webm', '.mp4', '.flac'}
    
    # Formato de salida optimizado para Whisper
    OUTPUT_FORMAT = 'wav'
    OUTPUT_CODEC = 'pcm_s16le'
    OUTPUT_SAMPLE_RATE = 16000
    
    def __init__(self, config: Dict, security_manager, logger):
        """
        Inicializa el procesador de audio.
        
        Args:
            config: Configuración del sistema
            security_manager: Instancia de SecurityManager
            logger: Instancia de SystemLogger
        """
        self.config = config
        self.system_config = config.get("system", {})
        self.security = security_manager
        self.logger = logger
        
        # Configuración
        self.temp_folder = Path(self.system_config.get("temp_folder", "./temp"))
        self.temp_folder.mkdir(parents=True, exist_ok=True)
        
        self.max_size_mb = self.system_config.get("max_audio_size_mb", 25)
        
        # Configuración de limpieza
        self.whisper_config = config.get("whisper", {})
        self.remove_fillers = self.whisper_config.get("remove_filler_words", True)
        self.filler_words = set(self.whisper_config.get("filler_words", []))
    
    async def validate_audio(self, 
                            file_path: Path, 
                            user_id: str) -> Dict:
        """
        Valida un archivo de audio completo.
        
        Args:
            file_path: Ruta al archivo
            user_id: ID del usuario para logging
        
        Returns:
            Diccionario con resultado de validación
        """
        self.logger.info(f"Validando audio: {file_path} para usuario {user_id}")
        
        # Verificar que existe
        if not file_path.exists():
            return {
                "valid": False,
                "error": "Archivo no encontrado",
                "file_path": str(file_path)
            }
        
        # Verificar que es archivo
        if not file_path.is_file():
            return {
                "valid": False,
                "error": "La ruta no es un archivo",
                "file_path": str(file_path)
            }
        
        # Verificar extensión
        ext_check = self.security.check_file_extension(file_path.name)
        if not ext_check["valid"]:
            return {
                "valid": False,
                "error": ext_check["error"],
                "extension": ext_check["extension"]
            }
        
        # Verificar tamaño
        size_bytes = file_path.stat().st_size
        size_check = self.security.check_audio_size(size_bytes)
        if not size_check["valid"]:
            self.logger.warning(
                f"Audio excede tamaño límite: {size_check['size_mb']}MB "
                f"por usuario {user_id}"
            )
            return {
                "valid": False,
                "error": size_check["error"],
                "size_mb": size_check["size_mb"]
            }
        
        # Verificar integridad con ffprobe
        try:
            probe = await asyncio.to_thread(
                ffmpeg.probe,
                str(file_path)
            )
            
            audio_streams = [
                stream for stream in probe.get('streams', [])
                if stream.get('codec_type') == 'audio'
            ]
            
            if not audio_streams:
                return {
                    "valid": False,
                    "error": "El archivo no contiene pista de audio",
                    "file_path": str(file_path)
                }
            
            audio_info = audio_streams[0]
            
            # Extraer información útil
            duration = float(audio_info.get('duration', 0))
            bitrate = audio_info.get('bit_rate', 'unknown')
            codec = audio_info.get('codec_name', 'unknown')
            
            # Verificar duración razonable (1 segundo a 2 horas)
            if duration < 1:
                return {
                    "valid": False,
                    "error": "Audio demasiado corto (< 1 segundo)",
                    "duration": duration
                }
            
            if duration > 7200:  # 2 horas
                return {
                    "valid": False,
                    "error": "Audio demasiado largo (> 2 horas)",
                    "duration": duration
                }
            
            self.logger.info(
                f"Audio validado: {file_path.name} "
                f"({duration:.1f}s, {codec}, {size_bytes/1024/1024:.1f}MB)"
            )
            
            return {
                "valid": True,
                "file_path": str(file_path),
                "duration": duration,
                "codec": codec,
                "bitrate": bitrate,
                "size_mb": size_check["size_mb"],
                "sample_rate": audio_info.get('sample_rate', 'unknown'),
                "channels": audio_info.get('channels', 'unknown')
            }
            
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if hasattr(e, 'stderr') else str(e)
            self.logger.error(f"Error ffprobe en {file_path}: {error_msg}")
            return {
                "valid": False,
                "error": f"Archivo de audio corrupto o no soportado: {error_msg[:100]}",
                "file_path": str(file_path)
            }
        except Exception as e:
            self.logger.error(f"Error validando audio {file_path}: {e}")
            return {
                "valid": False,
                "error": f"Error de validación: {str(e)}",
                "file_path": str(file_path)
            }
    
    async def convert_for_whisper(self, 
                                   input_path: Path,
                                   output_name: Optional[str] = None) -> Dict:
        """
        Convierte audio al formato óptimo para Whisper.
        
        Args:
            input_path: Ruta al archivo original
            output_name: Nombre opcional para el archivo de salida
        
        Returns:
            Diccionario con ruta al archivo convertido
        """
        self.logger.info(f"Convirtiendo audio para Whisper: {input_path.name}")
        
        # Generar nombre de salida
        if output_name is None:
            output_name = f"whisper_ready_{input_path.stem}.wav"
        
        output_path = self.temp_folder / output_name
        
        try:
            # Usar ffmpeg para conversión optimizada
            await asyncio.to_thread(
                lambda: (
                    ffmpeg
                    .input(str(input_path))
                    .output(
                        str(output_path),
                        ar=self.OUTPUT_SAMPLE_RATE,  # 16kHz
                        ac=1,  # Mono
                        codec=self.OUTPUT_CODEC,  # PCM 16-bit
                        loglevel='error'
                    )
                    .overwrite_output()
                    .run()
                )
            )
            
            # Verificar que se creó correctamente
            if not output_path.exists():
                raise Exception("El archivo convertido no se creó")
            
            output_size = output_path.stat().st_size
            
            self.logger.info(
                f"Conversión exitosa: {output_path.name} "
                f"({output_size/1024:.1f}KB)"
            )
            
            return {
                "success": True,
                "input_path": str(input_path),
                "output_path": str(output_path),
                "output_size_kb": output_size / 1024,
                "format": self.OUTPUT_FORMAT,
                "sample_rate": self.OUTPUT_SAMPLE_RATE
            }
            
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if hasattr(e, 'stderr') else str(e)
            self.logger.error(f"Error FFmpeg: {error_msg}")
            return {
                "success": False,
                "error": f"Error en conversión: {error_msg[:200]}",
                "input_path": str(input_path)
            }
        except Exception as e:
            self.logger.error(f"Error convirtiendo audio: {e}")
            return {
                "success": False,
                "error": f"Error inesperado: {str(e)}",
                "input_path": str(input_path)
            }
    
    async def clean_transcription(self, text: str) -> str:
        """
        Limpia muletillas y ruido de la transcripción.
        
        Args:
            text: Texto transcrito
        
        Returns:
            Texto limpio
        """
        if not self.remove_fillers or not self.filler_words:
            return text
        
        import re
        
        # Crear patrón para muletillas
        # Palabras completas, ignorando case
        pattern = r'\\b(' + '|'.join(re.escape(word) for word in self.filler_words) + r')\\b'
        
        # Reemplazar muletillas
        cleaned = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Limpiar espacios múltiples
        cleaned = re.sub(r'\\s+', ' ', cleaned)
        
        # Limpiar espacios al inicio y final
        cleaned = cleaned.strip()
        
        # Estadísticas
        original_words = len(text.split())
        cleaned_words = len(cleaned.split())
        removed = original_words - cleaned_words
        
        if removed > 0:
            self.logger.debug(f"Eliminadas {removed} muletillas de la transcripción")
        
        return cleaned
    
    async def save_audio_to_idea(self,
                                  source_path: Path,
                                  idea_folder: Path,
                                  filename: str = "audio_original") -> Dict:
        """
        Guarda el audio original en la carpeta de la idea.
        
        Args:
            source_path: Ruta al archivo fuente
            idea_folder: Carpeta de destino
            filename: Nombre base para el archivo
        
        Returns:
            Diccionario con información del archivo guardado
        """
        # Determinar extensión original
        ext = source_path.suffix
        
        # Sanitizar nombre
        safe_name = self.security.sanitize_filename(filename)
        final_name = f"{safe_name}{ext}"
        
        dest_path = idea_folder / final_name
        
        # Evitar colisiones
        counter = 1
        original_dest = dest_path
        while dest_path.exists():
            final_name = f"{safe_name}_{counter}{ext}"
            dest_path = idea_folder / final_name
            counter += 1
        
        try:
            # Copiar archivo
            await asyncio.to_thread(
                shutil.copy2,
                str(source_path),
                str(dest_path)
            )
            
            # Calcular hash para integridad
            file_hash = self.security.hash_file(dest_path)
            
            self.logger.info(f"Audio guardado: {dest_path.name} (hash: {file_hash[:16]}...)")
            
            return {
                "success": True,
                "file_path": str(dest_path),
                "file_name": final_name,
                "file_size_kb": dest_path.stat().st_size / 1024,
                "file_hash": file_hash,
                "original_name": source_path.name
            }
            
        except Exception as e:
            self.logger.error(f"Error guardando audio: {e}")
            return {
                "success": False,
                "error": str(e),
                "file_path": str(dest_path)
            }
    
    async def cleanup_temp_files(self, 
                                  pattern: Optional[str] = None,
                                  max_age_hours: Optional[int] = None):
        """
        Limpia archivos temporales.
        
        Args:
            pattern: Patrón de archivos a limpiar (ej: "whisper_ready_*")
            max_age_hours: Eliminar archivos más antiguos que X horas
        """
        try:
            deleted = 0
            freed_bytes = 0
            
            for file_path in self.temp_folder.iterdir():
                if not file_path.is_file():
                    continue
                
                # Verificar patrón si se especificó
                if pattern and not file_path.match(pattern):
                    continue
                
                # Verificar edad si se especificó
                if max_age_hours:
                    import time
                    file_age = time.time() - file_path.stat().st_mtime
                    if file_age < max_age_hours * 3600:
                        continue
                
                # Eliminar archivo
                file_size = file_path.stat().st_size
                file_path.unlink()
                deleted += 1
                freed_bytes += file_size
            
            if deleted > 0:
                self.logger.info(
                    f"Limpieza temporal: {deleted} archivos eliminados, "
                    f"{freed_bytes/1024/1024:.1f}MB liberados"
                )
            
            return {
                "deleted": deleted,
                "freed_mb": freed_bytes / 1024 / 1024
            }
            
        except Exception as e:
            self.logger.error(f"Error en limpieza temporal: {e}")
            return {
                "deleted": 0,
                "freed_mb": 0,
                "error": str(e)
            }
    
    def get_audio_duration_sync(self, file_path: Path) -> float:
        """
        Versión síncrona para obtener duración (útil para callbacks).
        
        Args:
            file_path: Ruta al archivo
        
        Returns:
            Duración en segundos
        """
        try:
            audio = AudioSegment.from_file(str(file_path))
            return len(audio) / 1000.0  # milisegundos a segundos
        except Exception:
            return 0.0


# Import necesario para shutil
import shutil
