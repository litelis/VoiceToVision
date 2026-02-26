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
VoiceToVision - Sistema de Logs Centralizado
Maneja logging del sistema y seguridad en archivos separados.
"""


import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import json


class SystemLogger:
    """
    Logger centralizado para el sistema VoiceToVision.
    Mantiene logs separados para sistema y seguridad.
    """
    
    def __init__(self, config: dict):
        """
        Inicializa el sistema de logging.
        
        Args:
            config: Configuración del sistema desde config.json
        """
        self.config = config
        self.system_config = config.get("system", {})
        
        # Rutas de logs
        self.logs_folder = Path(self.system_config.get("logs_folder", "./logs"))
        self.logs_folder.mkdir(parents=True, exist_ok=True)
        
        # Niveles de log
        self.log_level = getattr(
            logging, 
            self.system_config.get("log_level", "INFO").upper(),
            logging.INFO
        )
        
        # Flags
        self.enable_logs = self.system_config.get("enable_logs", True)
        
        # Inicializar loggers
        self.system_logger = None
        self.security_logger = None
        
        if self.enable_logs:
            self._setup_system_logger()
            self._setup_security_logger()
    
    def _setup_system_logger(self):
        """Configura el logger del sistema."""
        self.system_logger = logging.getLogger("voicetovision.system")
        self.system_logger.setLevel(self.log_level)
        self.system_logger.handlers = []  # Limpiar handlers previos
        
        # Formato detallado
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler para archivo con rotación
        log_file = self.logs_folder / "system.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        self.system_logger.addHandler(file_handler)
        
        # Handler para consola
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.system_logger.addHandler(console_handler)
        
        self.info("Sistema de logs inicializado")
    
    def _setup_security_logger(self):
        """Configura el logger de seguridad."""
        self.security_logger = logging.getLogger("voicetovision.security")
        self.security_logger.setLevel(logging.INFO)
        self.security_logger.handlers = []  # Limpiar handlers previos
        
        # Formato específico para seguridad
        formatter = logging.Formatter(
            '%(asctime)s | SECURITY | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler para archivo de seguridad
        log_file = self.logs_folder / "security.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=10,  # Más backups para seguridad
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        self.security_logger.addHandler(file_handler)
    
    def debug(self, message: str, extra: Optional[dict] = None):
        """Log de nivel DEBUG."""
        if self.system_logger:
            self.system_logger.debug(message, extra=extra or {})
    
    def info(self, message: str, extra: Optional[dict] = None):
        """Log de nivel INFO."""
        if self.system_logger:
            self.system_logger.info(message, extra=extra or {})
    
    def warning(self, message: str, extra: Optional[dict] = None):
        """Log de nivel WARNING."""
        if self.system_logger:
            self.system_logger.warning(message, extra=extra or {})
    
    def error(self, message: str, extra: Optional[dict] = None):
        """Log de nivel ERROR."""
        if self.system_logger:
            self.system_logger.error(message, extra=extra or {})
    
    def critical(self, message: str, extra: Optional[dict] = None):
        """Log de nivel CRITICAL."""
        if self.system_logger:
            self.system_logger.critical(message, extra=extra or {})
    
    def log_security_event(self, event_type: str, user_id: str, 
                          details: dict, success: bool = True):
        """
        Registra evento de seguridad.
        
        Args:
            event_type: Tipo de evento (auth, access, modify, etc.)
            user_id: ID del usuario
            details: Detalles adicionales
            success: Si la operación fue exitosa
        """
        if not self.security_logger:
            return
        
        event_data = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "user_id": str(user_id),
            "success": success,
            "details": details
        }
        
        status = "SUCCESS" if success else "FAILED"
        message = f"{status} | {event_type} | User: {user_id} | {json.dumps(details)}"
        
        self.security_logger.info(message)
    
    def log_auth_attempt(self, user_id: str, platform: str, 
                        success: bool, reason: Optional[str] = None):
        """
        Registra intento de autenticación.
        
        Args:
            user_id: ID del usuario
            platform: Plataforma (discord, whatsapp)
            success: Si fue exitoso
            reason: Razón del fallo (opcional)
        """
        details = {
            "platform": platform,
            "reason": reason
        }
        self.log_security_event("AUTHENTICATION", user_id, details, success)
    
    def log_file_access(self, user_id: str, file_path: str, 
                       action: str, success: bool = True):
        """
        Registra acceso a archivos.
        
        Args:
            user_id: ID del usuario
            file_path: Ruta del archivo
            action: Acción realizada (read, write, delete)
            success: Si fue exitoso
        """
        details = {
            "file_path": file_path,
            "action": action
        }
        self.log_security_event("FILE_ACCESS", user_id, details, success)
    
    def log_idea_operation(self, user_id: str, operation: str, 
                          idea_name: str, details: Optional[dict] = None):
        """
        Registra operación sobre una idea.
        
        Args:
            user_id: ID del usuario
            operation: Tipo de operación (create, rename, delete, search)
            idea_name: Nombre de la idea
            details: Detalles adicionales
        """
        event_details = {
            "idea_name": idea_name,
            **(details or {})
        }
        self.log_security_event(f"IDEA_{operation.upper()}", user_id, event_details)
    
    def log_error_with_context(self, error: Exception, context: dict):
        """
        Registra error con contexto adicional.
        
        Args:
            error: Excepción ocurrida
            context: Contexto del error
        """
        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context
        }
        self.error(f"Error: {error}", extra=error_data)


# Instancia global del logger
_logger_instance: Optional[SystemLogger] = None


def get_logger(config: Optional[dict] = None) -> SystemLogger:
    """
    Obtiene instancia del logger (singleton).
    
    Args:
        config: Configuración opcional para inicializar
    
    Returns:
        Instancia de SystemLogger
    """
    global _logger_instance
    
    if _logger_instance is None and config is not None:
        _logger_instance = SystemLogger(config)
    
    return _logger_instance


def init_logger(config: dict) -> SystemLogger:
    """
    Inicializa el logger global.
    
    Args:
        config: Configuración del sistema
    
    Returns:
        Instancia de SystemLogger
    """
    global _logger_instance
    _logger_instance = SystemLogger(config)
    return _logger_instance
