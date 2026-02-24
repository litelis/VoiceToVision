"""
VoiceToVision - Gestor de ZIP
Crea archivos ZIP temporales con enlaces de descarga expirables.
"""

import os
import zipfile
import asyncio
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
import secrets
import aiofiles
import json


class ZipManager:
    """
    Gestiona la creación de archivos ZIP para descarga
    con enlaces temporales seguros y expirables.
    """
    
    def __init__(self, config: Dict, security_manager, logger):
        """
        Inicializa el gestor de ZIP.
        
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
        self.base_folder = Path(self.system_config.get("base_folder", "./ideas"))
        self.temp_folder = Path(self.system_config.get("temp_folder", "./temp"))
        self.downloads_folder = self.temp_folder / "downloads"
        self.downloads_folder.mkdir(parents=True, exist_ok=True)
        
        # Tiempo de expiración (minutos)
        self.expiry_minutes = self.system_config.get("link_expiry_minutes", 30)
        
        # Registro de enlaces activos
        self.active_links: Dict[str, Dict] = {}
        
        # Cargar enlaces existentes si hay
        self._load_links_registry()
    
    def _get_registry_path(self) -> Path:
        """Ruta al registro de enlaces."""
        return self.downloads_folder / ".links_registry.json"
    
    def _load_links_registry(self):
        """Carga el registro de enlaces desde disco."""
        registry_path = self._get_registry_path()
        if registry_path.exists():
            try:
                with open(registry_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Filtrar solo enlaces no expirados
                    now = datetime.now().isoformat()
                    self.active_links = {
                        k: v for k, v in data.items()
                        if v.get("expires", "") > now
                    }
            except Exception as e:
                self.logger.error(f"Error cargando registro de enlaces: {e}")
                self.active_links = {}
    
    def _save_links_registry(self):
        """Guarda el registro de enlaces a disco."""
        try:
            registry_path = self._get_registry_path()
            with open(registry_path, 'w', encoding='utf-8') as f:
                json.dump(self.active_links, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error guardando registro de enlaces: {e}")
    
    async def create_download_package(self,
                                       idea_name: str,
                                       user_id: str,
                                       selected_files: Optional[List[str]] = None) -> Dict:
        """
        Crea un paquete ZIP para descarga de una idea.
        
        Args:
            idea_name: Nombre de la carpeta de la idea
            user_id: ID del usuario que solicita
            selected_files: Lista específica de archivos (None = todos)
        
        Returns:
            Información del enlace de descarga
        """
        self.logger.info(f"Creando paquete ZIP para '{idea_name}' por usuario {user_id}")
        
        # Verificar autorización
        if not self.security.is_authorized(user_id):
            return {
                "success": False,
                "error": "Usuario no autorizado"
            }
        
        # Sanitizar y validar nombre
        nombre_seguro = self.security.sanitize_filename(idea_name)
        idea_folder = self.base_folder / nombre_seguro
        
        if not idea_folder.exists():
            return {
                "success": False,
                "error": f"No existe la idea '{nombre_seguro}'"
            }
        
        if not self.security.is_safe_path(idea_folder):
            return {
                "success": False,
                "error": "Ruta no segura"
            }
        
        # Determinar archivos a incluir
        files_to_include = []
        
        if selected_files:
            # Verificar cada archivo solicitado
            for filename in selected_files:
                safe_name = self.security.sanitize_filename(filename)
                file_path = idea_folder / safe_name
                if file_path.exists() and self.security.is_safe_path(file_path):
                    files_to_include.append(file_path)
        else:
            # Incluir todos los archivos
            files_to_include = [
                f for f in idea_folder.iterdir()
                if f.is_file() and not f.name.startswith('.')
            ]
        
        if not files_to_include:
            return {
                "success": False,
                "error": "No hay archivos disponibles para descargar"
            }
        
        # Generar token único
        token = secrets.token_urlsafe(32)
        
        # Nombre del ZIP
        zip_name = f"{nombre_seguro}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = self.downloads_folder / zip_name
        
        try:
            # Crear ZIP
            await self._create_zip_file(zip_path, files_to_include, nombre_seguro)
            
            # Calcular expiración
            expires = datetime.now() + timedelta(minutes=self.expiry_minutes)
            
            # Registrar enlace
            link_info = {
                "token": token,
                "zip_path": str(zip_path),
                "zip_name": zip_name,
                "idea_name": nombre_seguro,
                "created_by": str(user_id),
                "created_at": datetime.now().isoformat(),
                "expires": expires.isoformat(),
                "files_included": [f.name for f in files_to_include],
                "file_count": len(files_to_include),
                "size_mb": zip_path.stat().st_size / (1024 * 1024),
                "downloaded": False,
                "download_count": 0
            }
            
            self.active_links[token] = link_info
            self._save_links_registry()
            
            # Generar URL de descarga (relativa, se construye según el bot)
            download_url = f"/download/{token}"
            
            self.logger.log_file_access(
                user_id=user_id,
                file_path=str(zip_path),
                action="create_zip",
                success=True
            )
            
            return {
                "success": True,
                "token": token,
                "download_url": download_url,
                "expires_at": expires.isoformat(),
                "expires_in_minutes": self.expiry_minutes,
                "file_count": len(files_to_include),
                "size_mb": round(link_info["size_mb"], 2),
                "files": link_info["files_included"]
            }
            
        except Exception as e:
            self.logger.error(f"Error creando ZIP: {e}")
            # Limpiar si falló
            if zip_path.exists():
                zip_path.unlink()
            
            return {
                "success": False,
                "error": f"Error creando archivo ZIP: {str(e)}"
            }
    
    async def _create_zip_file(self,
                                zip_path: Path,
                                files: List[Path],
                                base_folder_name: str):
        """
        Crea el archivo ZIP físico.
        
        Args:
            zip_path: Ruta destino del ZIP
            files: Lista de archivos a incluir
            base_folder_name: Nombre de la carpeta base dentro del ZIP
        """
        # Crear ZIP en thread separado para no bloquear
        def create_zip():
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in files:
                    # Ruta dentro del ZIP
                    arcname = f"{base_folder_name}/{file_path.name}"
                    zf.write(file_path, arcname)
        
        await asyncio.to_thread(create_zip)
    
    async def validate_download_token(self, token: str) -> Dict:
        """
        Valida un token de descarga.
        
        Args:
            token: Token a validar
        
        Returns:
            Información del enlace si es válido
        """
        # Limpiar enlaces expirados primero
        await self.cleanup_expired_links()
        
        if token not in self.active_links:
            return {
                "valid": False,
                "error": "Enlace no encontrado o expirado"
            }
        
        link_info = self.active_links[token]
        
        # Verificar expiración
        expires = datetime.fromisoformat(link_info["expires"])
        if datetime.now() > expires:
            # Eliminar archivo si existe
            await self._delete_zip_file(link_info["zip_path"])
            del self.active_links[token]
            self._save_links_registry()
            
            return {
                "valid": False,
                "error": "Enlace expirado"
            }
        
        # Verificar que el archivo existe
        zip_path = Path(link_info["zip_path"])
        if not zip_path.exists():
            del self.active_links[token]
            self._save_links_registry()
            
            return {
                "valid": False,
                "error": "Archivo no encontrado"
            }
        
        return {
            "valid": True,
            "link_info": link_info,
            "zip_path": str(zip_path)
        }
    
    async def record_download(self, token: str):
        """
        Registra una descarga exitosa.
        
        Args:
            token: Token del enlace
        """
        if token in self.active_links:
            self.active_links[token]["downloaded"] = True
            self.active_links[token]["download_count"] += 1
            self.active_links[token]["last_download"] = datetime.now().isoformat()
            self._save_links_registry()
    
    async def get_download_file_path(self, token: str) -> Optional[Path]:
        """
        Obtiene la ruta al archivo ZIP para descarga.
        
        Args:
            token: Token de descarga
        
        Returns:
            Path al archivo o None si no es válido
        """
        validation = await self.validate_download_token(token)
        
        if not validation["valid"]:
            return None
        
        return Path(validation["zip_path"])
    
    async def cleanup_expired_links(self):
        """
        Elimina enlaces y archivos expirados.
        """
        now = datetime.now()
        expired = []
        
        for token, info in list(self.active_links.items()):
            expires = datetime.fromisoformat(info["expires"])
            
            # Eliminar si expiró o si ya fue descargado hace tiempo
            if now > expires:
                expired.append(token)
            elif info.get("downloaded") and info.get("download_count", 0) > 0:
                # Opcional: eliminar después de primera descarga
                # Por ahora mantenemos hasta expiración
                pass
        
        for token in expired:
            link_info = self.active_links[token]
            await self._delete_zip_file(link_info["zip_path"])
            del self.active_links[token]
            self.logger.info(f"Enlace expirado eliminado: {token[:16]}...")
        
        if expired:
            self._save_links_registry()
        
        return len(expired)
    
    async def _delete_zip_file(self, zip_path: str):
        """
        Elimina un archivo ZIP de forma segura.
        
        Args:
            zip_path: Ruta al archivo
        """
        try:
            path = Path(zip_path)
            if path.exists() and self.security.is_safe_path(path):
                await asyncio.to_thread(path.unlink)
        except Exception as e:
            self.logger.error(f"Error eliminando ZIP: {e}")
    
    async def get_user_downloads(self, user_id: str) -> List[Dict]:
        """
        Obtiene enlaces de descarga activos de un usuario.
        
        Args:
            user_id: ID del usuario
        
        Returns:
            Lista de enlaces activos del usuario
        """
        user_links = []
        
        for token, info in self.active_links.items():
            if info.get("created_by") == str(user_id):
                # Calcular tiempo restante
                expires = datetime.fromisoformat(info["expires"])
                remaining = expires - datetime.now()
                remaining_minutes = max(0, int(remaining.total_seconds() / 60))
                
                user_links.append({
                    "token": token[:16] + "...",  # Parcial por seguridad
                    "idea_name": info["idea_name"],
                    "created_at": info["created_at"],
                    "expires_in_minutes": remaining_minutes,
                    "file_count": info["file_count"],
                    "size_mb": round(info["size_mb"], 2),
                    "downloaded": info.get("downloaded", False)
                })
        
        return sorted(user_links, key=lambda x: x["created_at"], reverse=True)
    
    async def revoke_link(self, token: str, user_id: str) -> Dict:
        """
        Revoca un enlace de descarga.
        
        Args:
            token: Token a revocar
            user_id: ID del usuario (debe ser creador o admin)
        
        Returns:
            Resultado de la operación
        """
        if token not in self.active_links:
            return {
                "success": False,
                "error": "Enlace no encontrado"
            }
        
        link_info = self.active_links[token]
        
        # Verificar permisos
        is_creator = link_info.get("created_by") == str(user_id)
        is_admin = self.security.is_admin(user_id)
        
        if not (is_creator or is_admin):
            return {
                "success": False,
                "error": "No tienes permiso para revocar este enlace"
            }
        
        # Eliminar archivo y registro
        await self._delete_zip_file(link_info["zip_path"])
        del self.active_links[token]
        self._save_links_registry()
        
        self.logger.log_security_event(
            "LINK_REVOKED",
            user_id,
            {"token": token[:16], "idea": link_info["idea_name"]}
        )
        
        return {
            "success": True,
            "message": "Enlace revocado correctamente"
        }
    
    async def get_system_stats(self) -> Dict:
        """
        Obtiene estadísticas del sistema de descargas.
        
        Returns:
            Estadísticas
        """
        total_links = len(self.active_links)
        total_size = sum(
            info.get("size_mb", 0) 
            for info in self.active_links.values()
        )
        
        downloaded = sum(
            1 for info in self.active_links.values()
            if info.get("downloaded", False)
        )
        
        return {
            "active_links": total_links,
            "total_size_mb": round(total_size, 2),
            "downloaded_count": downloaded,
            "pending_count": total_links - downloaded,
            "expiry_minutes": self.expiry_minutes
        }
