"""
VoiceToVision - Módulo de Seguridad
Autenticación, autorización y sanitización para Windows.
"""

import os
import re
import unicodedata
from pathlib import Path
from typing import Optional, List, Dict, Set
import json
import hashlib
import secrets


class SecurityManager:
    """
    Gestiona seguridad del sistema: autenticación, autorización,
    sanitización de rutas y protección contra ataques comunes.
    """
    
    # Caracteres inválidos en Windows
    INVALID_CHARS = '<>:"/\\|?*'
    
    # Palabras reservadas en Windows
    RESERVED_NAMES = {
        'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
        'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3',
        'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    def __init__(self, config: Dict):
        """
        Inicializa el gestor de seguridad.
        
        Args:
            config: Configuración del sistema desde config.json
        """
        self.config = config
        self.discord_config = config.get("discord", {})
        
        # Listas de control de acceso
        self.authorized_users: Set[str] = set(
            str(u) for u in self.discord_config.get("authorized_users", [])
        )
        self.admin_users: Set[str] = set(
            str(u) for u in self.discord_config.get("admins", [])
        )
        
        # Configuración de límites
        system_config = config.get("system", {})
        self.max_path_length = system_config.get("max_path_length", 240)
        self.max_filename_length = system_config.get("max_filename_length", 50)
        self.max_audio_size_mb = system_config.get("max_audio_size_mb", 25)
        
        # Base folder para validación de path traversal
        self.base_folder = Path(system_config.get("base_folder", "./ideas")).resolve()
    
    def is_authorized(self, user_id: str) -> bool:
        """
        Verifica si un usuario está autorizado.
        
        Args:
            user_id: ID del usuario a verificar
        
        Returns:
            True si está en la lista de autorizados
        """
        return str(user_id) in self.authorized_users
    
    def is_admin(self, user_id: str) -> bool:
        """
        Verifica si un usuario es administrador.
        
        Args:
            user_id: ID del usuario a verificar
        
        Returns:
            True si es administrador
        """
        return str(user_id) in self.admin_users
    
    def authenticate_user(self, user_id: str, platform: str = "discord") -> Dict:
        """
        Autentica un usuario y retorna información de permisos.
        
        Args:
            user_id: ID del usuario
            platform: Plataforma (discord, whatsapp)
        
        Returns:
            Diccionario con estado de autenticación y permisos
        """
        user_id = str(user_id)
        
        is_auth = self.is_authorized(user_id)
        is_adm = self.is_admin(user_id) if is_auth else False
        
        return {
            "authenticated": is_auth,
            "is_admin": is_adm,
            "user_id": user_id,
            "platform": platform,
            "can_create": is_auth,
            "can_read": is_auth,
            "can_update": is_auth,
            "can_delete": is_adm,  # Solo admins pueden eliminar
            "can_rename": is_adm,   # Solo admins pueden renombrar
            "can_search": is_auth
        }
    
    def sanitize_filename(self, name: str, max_length: Optional[int] = None) -> str:
        """
        Sanitiza un nombre de archivo/carpeta para Windows.
        
        Pasos:
        1. Normalizar unicode (quitar tildes)
        2. Eliminar caracteres inválidos
        3. Reemplazar espacios por guiones bajos
        4. Limitar longitud
        5. Evitar nombres reservados
        
        Args:
            name: Nombre original
            max_length: Longitud máxima (usa config por defecto)
        
        Returns:
            Nombre sanitizado seguro
        """
        if max_length is None:
            max_length = self.max_filename_length
        
        # 1. Normalizar unicode (NFKD separa caracteres base de diacríticos)
        normalized = unicodedata.normalize('NFKD', name)
        
        # 2. Eliminar diacríticos (tildes)
        without_accents = ''.join(
            c for c in normalized 
            if not unicodedata.combining(c)
        )
        
        # 3. Eliminar caracteres inválidos para Windows
        sanitized = ''.join(
            c if c not in self.INVALID_CHARS else '_'
            for c in without_accents
        )
        
        # 4. Reemplazar espacios y caracteres de control
        sanitized = sanitized.replace(' ', '_')
        sanitized = ''.join(c if ord(c) >= 32 else '_' for c in sanitized)
        
        # 5. Eliminar puntos al inicio (archivos ocultos)
        sanitized = sanitized.lstrip('.')
        
        # 6. Limitar longitud preservando extensión si existe
        if len(sanitized) > max_length:
            # Buscar extensión
            if '.' in sanitized:
                name_part, ext = sanitized.rsplit('.', 1)
                available = max_length - len(ext) - 1
                if available > 0:
                    sanitized = name_part[:available] + '.' + ext
                else:
                    sanitized = sanitized[:max_length]
            else:
                sanitized = sanitized[:max_length]
        
        # 7. Evitar nombres reservados de Windows
        upper_name = sanitized.upper()
        if upper_name in self.RESERVED_NAMES:
            sanitized = f"_{sanitized}"
        
        # 8. Si quedó vacío, usar default
        if not sanitized or sanitized == '_':
            sanitized = "unnamed_idea"
        
        return sanitized
    
    def sanitize_path_component(self, component: str) -> str:
        """
        Sanitiza un componente de ruta (carpeta).
        
        Args:
            component: Nombre del componente
        
        Returns:
            Componente sanitizado
        """
        return self.sanitize_filename(component, self.max_filename_length)
    
    def validate_path(self, path: str or Path) -> Optional[Path]:
        """
        Valida que una ruta esté dentro del directorio base.
        Protección contra Path Traversal.
        
        Args:
            path: Ruta a validar
        
        Returns:
            Path resuelto si es válido, None si es inválido
        """
        try:
            # Convertir a Path si es string
            if isinstance(path, str):
                path = Path(path)
            
            # Resolver ruta absoluta
            resolved = path.resolve()
            
            # Verificar que esté dentro de base_folder
            try:
                resolved.relative_to(self.base_folder)
                return resolved
            except ValueError:
                # La ruta está fuera de base_folder
                return None
                
        except (OSError, ValueError) as e:
            return None
    
    def is_safe_path(self, path: str or Path) -> bool:
        """
        Verifica rápidamente si una ruta es segura.
        
        Args:
            path: Ruta a verificar
        
        Returns:
            True si la ruta está dentro del directorio permitido
        """
        return self.validate_path(path) is not None
    
    def check_audio_size(self, size_bytes: int) -> Dict:
        """
        Verifica que el tamaño de audio esté dentro del límite.
        
        Args:
            size_bytes: Tamaño en bytes
        
        Returns:
            Diccionario con resultado de validación
        """
        max_bytes = self.max_audio_size_mb * 1024 * 1024
        
        return {
            "valid": size_bytes <= max_bytes,
            "size_bytes": size_bytes,
            "size_mb": round(size_bytes / (1024 * 1024), 2),
            "max_mb": self.max_audio_size_mb,
            "error": None if size_bytes <= max_bytes else 
                     f"Tamaño {size_bytes/(1024*1024):.1f}MB excede límite de {self.max_audio_size_mb}MB"
        }
    
    def check_file_extension(self, filename: str) -> Dict:
        """
        Verifica que la extensión del archivo sea permitida.
        
        Args:
            filename: Nombre del archivo
        
        Returns:
            Diccionario con resultado de validación
        """
        system_config = self.config.get("system", {})
        allowed = system_config.get("supported_formats", [".mp3", ".wav", ".ogg", ".m4a"])
        
        ext = Path(filename).suffix.lower()
        
        return {
            "valid": ext in allowed,
            "extension": ext,
            "allowed_extensions": allowed,
            "error": None if ext in allowed else f"Extensión {ext} no permitida"
        }
    
    def generate_versioned_name(self, 
                                 base_name: str, 
                                 existing_names: List[str]) -> str:
        """
        Genera un nombre versionado si ya existe.
        
        Ejemplo: Idea -> Idea_v2 -> Idea_v3
        
        Args:
            base_name: Nombre base sanitizado
            existing_names: Lista de nombres que ya existen
        
        Returns:
            Nombre único (posiblemente versionado)
        """
        if base_name not in existing_names:
            return base_name
        
        # Buscar versión disponible
        version = 2
        while True:
            versioned = f"{base_name}_v{version}"
            if versioned not in existing_names:
                return versioned
            version += 1
            
            # Límite de seguridad
            if version > 999:
                # Añadir timestamp para desambiguar
                import time
                return f"{base_name}_{int(time.time())}"
    
    def hash_file(self, file_path: Path) -> str:
        """
        Genera hash SHA-256 de un archivo.
        
        Args:
            file_path: Ruta al archivo
        
        Returns:
            Hash hexadecimal del archivo
        """
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
    
    def generate_secure_token(self, length: int = 32) -> str:
        """
        Genera un token seguro para enlaces temporales.
        
        Args:
            length: Longitud del token
        
        Returns:
            Token seguro en hexadecimal
        """
        return secrets.token_hex(length)
    
    def validate_command_args(self, 
                            command: str, 
                            args: List[str], 
                            user_id: str) -> Dict:
        """
        Valida argumentos de comandos según permisos.
        
        Args:
            command: Nombre del comando
            args: Argumentos proporcionados
            user_id: ID del usuario
        
        Returns:
            Diccionario con resultado de validación
        """
        auth = self.authenticate_user(user_id)
        
        # Comandos que requieren admin
        admin_commands = {'rename', 'delete', 'config'}
        
        if command in admin_commands and not auth["is_admin"]:
            return {
                "valid": False,
                "error": f"Comando '{command}' requiere privilegios de administrador",
                "command": command
            }
        
        # Validar número de argumentos
        required_args = {
            'rename': 2,  # /rename old_name new_name
            'search': 1,  # /search query
            'delete': 1   # /delete idea_name
        }
        
        min_args = required_args.get(command, 0)
        if len(args) < min_args:
            return {
                "valid": False,
                "error": f"Comando '{command}' requiere al menos {min_args} argumento(s)",
                "command": command
            }
        
        # Sanitizar argumentos que son nombres de carpetas
        if command in ['rename', 'delete']:
            sanitized_args = [self.sanitize_filename(arg) for arg in args]
        else:
            sanitized_args = args
        
        return {
            "valid": True,
            "command": command,
            "args": sanitized_args,
            "is_admin": auth["is_admin"]
        }
    
    def create_safe_path(self, *path_components: str) -> Optional[Path]:
        """
        Crea una ruta segura combinando componentes.
        
        Args:
            path_components: Componentes de la ruta
        
        Returns:
            Path seguro resuelto o None si es inválido
        """
        # Sanitizar cada componente
        safe_components = [
            self.sanitize_path_component(comp) 
            for comp in path_components
        ]
        
        # Construir ruta
        full_path = self.base_folder.joinpath(*safe_components)
        
        # Validar que no exceda límite de Windows
        try:
            path_str = str(full_path.resolve())
            if len(path_str) > self.max_path_length:
                # Truncar último componente si es necesario
                available = self.max_path_length - len(str(self.base_folder.resolve())) - 1
                if available > 10:
                    safe_components[-1] = safe_components[-1][:available]
                    full_path = self.base_folder.joinpath(*safe_components)
                else:
                    return None
        except Exception:
            return None
        
        # Validar que esté dentro de base
        return self.validate_path(full_path)
    
    def get_user_info(self, user_id: str) -> Dict:
        """
        Obtiene información de un usuario.
        
        Args:
            user_id: ID del usuario
        
        Returns:
            Diccionario con información del usuario
        """
        user_id = str(user_id)
        
        return {
            "user_id": user_id,
            "authorized": self.is_authorized(user_id),
            "admin": self.is_admin(user_id),
            "role": "admin" if self.is_admin(user_id) else 
                   ("user" if self.is_authorized(user_id) else "none")
        }


# Instancia global
_security_instance: Optional[SecurityManager] = None


def init_security(config: Dict) -> SecurityManager:
    """
    Inicializa el gestor de seguridad global.
    
    Args:
        config: Configuración del sistema
    
    Returns:
        Instancia de SecurityManager
    """
    global _security_instance
    _security_instance = SecurityManager(config)
    return _security_instance


def get_security() -> Optional[SecurityManager]:
    """
    Obtiene instancia global del gestor de seguridad.
    
    Returns:
        Instancia de SecurityManager o None
    """
    return _security_instance
