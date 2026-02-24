"""
VoiceToVision - Gestor de Ideas
Crea y maneja la estructura de carpetas y archivos de cada idea.
"""

import json
import uuid
import shutil
from pathlib import Path
from typing import Dict, Optional, List, Any
from datetime import datetime
import aiofiles


class IdeaManager:
    """
    Gestiona la creación, organización y mantenimiento de ideas.
    Cada idea tiene su propia carpeta con archivos estructurados.
    """
    
    def __init__(self, config: Dict, security_manager, database, logger):
        """
        Inicializa el gestor de ideas.
        
        Args:
            config: Configuración del sistema
            security_manager: Instancia de SecurityManager
            database: Instancia de IdeasDatabase
            logger: Instancia de SystemLogger
        """
        self.config = config
        self.system_config = config.get("system", {})
        self.security = security_manager
        self.db = database
        self.logger = logger
        
        # Rutas base
        self.base_folder = Path(self.system_config.get("base_folder", "./ideas"))
        self.base_folder.mkdir(parents=True, exist_ok=True)
        
        # Configuración
        self.max_filename_length = self.system_config.get("max_filename_length", 50)
    
    async def create_idea(self,
                         nombre_idea: str,
                         analysis_data: Dict,
                         audio_info: Dict,
                         transcription: str,
                         user_id: str) -> Dict:
        """
        Crea una nueva idea completa con su estructura de carpetas.
        
        Args:
            nombre_idea: Nombre generado por IA
            analysis_data: Datos del análisis de Ollama
            audio_info: Información del audio original
            transcription: Texto transcrito
            user_id: ID del usuario creador
        
        Returns:
            Diccionario con información de la idea creada
        """
        self.logger.info(f"Creando idea: '{nombre_idea}' por usuario {user_id}")
        
        # Sanitizar nombre para carpeta
        nombre_carpeta = self.security.sanitize_filename(
            nombre_idea,
            self.max_filename_length
        )
        
        # Verificar si ya existe y versionar
        existing_folders = [
            f.name for f in self.base_folder.iterdir() 
            if f.is_dir()
        ]
        nombre_carpeta = self.security.generate_versioned_name(
            nombre_carpeta,
            existing_folders
        )
        
        # Crear carpeta de la idea
        idea_folder = self.base_folder / nombre_carpeta
        idea_folder.mkdir(parents=True, exist_ok=True)
        
        # Generar UUID único
        idea_uuid = str(uuid.uuid4())
        
        # Preparar metadata
        now = datetime.now().isoformat()
        metadata = {
            "uuid": idea_uuid,
            "fecha_creacion": now,
            "creado_por": str(user_id),
            "version": 1,
            "nombre_original": nombre_idea,
            "nombre_carpeta": nombre_carpeta,
            "ruta_completa": str(idea_folder.resolve())
        }
        
        # Guardar archivos
        files_created = []
        
        # 1. Guardar transcripción
        trans_path = await self._save_transcription(idea_folder, transcription)
        files_created.append(trans_path)
        
        # 2. Guardar análisis JSON
        analysis_path = await self._save_analysis_json(idea_folder, analysis_data)
        files_created.append(analysis_path)
        
        # 3. Guardar resumen
        resumen = analysis_data.get("resumen", "")
        resumen_path = await self._save_resumen(idea_folder, resumen)
        files_created.append(resumen_path)
        
        # 4. Guardar metadata
        meta_path = await self._save_metadata(idea_folder, metadata, analysis_data)
        files_created.append(meta_path)
        
        # 5. Mover audio original (si existe)
        if audio_info.get("success"):
            audio_dest = await self._move_audio(idea_folder, audio_info)
            if audio_dest:
                files_created.append(audio_dest)
        
        # Registrar en base de datos
        try:
            db_uuid = await self.db.create_idea(
                nombre_idea=nombre_idea,
                nombre_carpeta=nombre_carpeta,
                ruta_completa=str(idea_folder.resolve()),
                creado_por=user_id,
                tipo=analysis_data.get("tipo", "Otro"),
                nivel_madurez=analysis_data.get("nivel_madurez", "concepto"),
                viabilidad=analysis_data.get("viabilidad", 5),
                tags=analysis_data.get("tags", []),
                resumen=resumen,
                metadata_completa={**metadata, **analysis_data}
            )
            
            # Registrar archivos en DB
            for file_path in files_created:
                if file_path:
                    await self.db.add_file_to_idea(
                        idea_uuid=db_uuid,
                        nombre_archivo=file_path.name,
                        tipo_archivo=file_path.suffix[1:] if file_path.suffix else "unknown",
                        ruta_relativa=file_path.name,
                        tamanio_kb=file_path.stat().st_size / 1024
                    )
            
            self.logger.log_idea_operation(
                user_id=user_id,
                operation="create",
                idea_name=nombre_carpeta,
                details={"uuid": db_uuid, "files": len(files_created)}
            )
            
            return {
                "success": True,
                "uuid": db_uuid,
                "nombre_carpeta": nombre_carpeta,
                "ruta": str(idea_folder),
                "files_created": len(files_created),
                "tipo": analysis_data.get("tipo"),
                "viabilidad": analysis_data.get("viabilidad")
            }
            
        except Exception as e:
            self.logger.error(f"Error registrando en base de datos: {e}")
            # No eliminamos archivos, pueden recuperarse manualmente
            return {
                "success": False,
                "error": f"Idea creada en disco pero error en base de datos: {str(e)}",
                "ruta": str(idea_folder)
            }
    
    async def _save_transcription(self, 
                                   idea_folder: Path, 
                                   transcription: str) -> Path:
        """Guarda la transcripción en archivo de texto."""
        file_path = idea_folder / "transcripcion.txt"
        
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write("TRANSCRIPCIÓN DEL AUDIO\\n")
            await f.write("=" * 50 + "\\n\\n")
            await f.write(transcription)
            await f.write("\\n\\n")
            await f.write(f"\\nGenerado: {datetime.now().isoformat()}\\n")
        
        return file_path
    
    async def _save_analysis_json(self,
                                   idea_folder: Path,
                                   analysis: Dict) -> Path:
        """Guarda el análisis completo en JSON."""
        file_path = idea_folder / "analisis.json"
        
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(analysis, indent=2, ensure_ascii=False))
        
        return file_path
    
    async def _save_resumen(self,
                             idea_folder: Path,
                             resumen: str) -> Path:
        """Guarda el resumen en archivo de texto."""
        file_path = idea_folder / "resumen.txt"
        
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write("RESUMEN DE LA IDEA\\n")
            await f.write("=" * 50 + "\\n\\n")
            await f.write(resumen)
            await f.write("\\n\\n")
            await f.write(f"\\nGenerado: {datetime.now().isoformat()}\\n")
        
        return file_path
    
    async def _save_metadata(self,
                              idea_folder: Path,
                              metadata: Dict,
                              analysis: Dict) -> Path:
        """Guarda metadata completa."""
        file_path = idea_folder / "metadata.json"
        
        full_metadata = {
            "sistema": metadata,
            "analisis": analysis,
            "estadisticas": {
                "longitud_transcripcion": 0,  # Se actualizará después
                "numero_archivos": 4,  # Inicial
                "fecha_ultima_modificacion": datetime.now().isoformat()
            }
        }
        
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(full_metadata, indent=2, ensure_ascii=False))
        
        return file_path
    
    async def _move_audio(self,
                          idea_folder: Path,
                          audio_info: Dict) -> Optional[Path]:
        """Mueve el audio original a la carpeta de la idea."""
        source_path = Path(audio_info.get("file_path", ""))
        if not source_path.exists():
            return None
        
        # Determinar extensión
        ext = source_path.suffix
        
        # Nombre seguro
        dest_name = f"audio_original{ext}"
        dest_path = idea_folder / dest_name
        
        # Evitar colisiones
        counter = 1
        while dest_path.exists():
            dest_name = f"audio_original_{counter}{ext}"
            dest_path = idea_folder / dest_name
            counter += 1
        
        try:
            # Copiar (no mover, para mantener original en temp hasta confirmar)
            await asyncio.to_thread(
                shutil.copy2,
                str(source_path),
                str(dest_path)
            )
            return dest_path
        except Exception as e:
            self.logger.error(f"Error copiando audio: {e}")
            return None
    
    async def rename_idea(self,
                          nombre_actual: str,
                          nuevo_nombre: str,
                          user_id: str) -> Dict:
        """
        Renombra una idea existente.
        
        Args:
            nombre_actual: Nombre actual de la carpeta
            nuevo_nombre: Nuevo nombre deseado
            user_id: ID del usuario (debe ser admin)
        
        Returns:
            Resultado de la operación
        """
        self.logger.info(f"Renombrando idea: '{nombre_actual}' -> '{nuevo_nombre}'")
        
        # Verificar permisos
        if not self.security.is_admin(user_id):
            return {
                "success": False,
                "error": "Solo administradores pueden renombrar ideas"
            }
        
        # Sanitizar nombres
        nombre_actual_seguro = self.security.sanitize_filename(nombre_actual)
        nuevo_nombre_seguro = self.security.sanitize_filename(
            nuevo_nombre,
            self.max_filename_length
        )
        
        # Verificar que existe la carpeta actual
        carpeta_actual = self.base_folder / nombre_actual_seguro
        if not carpeta_actual.exists():
            return {
                "success": False,
                "error": f"No existe la idea '{nombre_actual_seguro}'"
            }
        
        # Verificar que no existe el nuevo nombre
        carpeta_nueva = self.base_folder / nuevo_nombre_seguro
        if carpeta_nueva.exists():
            # Generar nombre versionado
            existing = [f.name for f in self.base_folder.iterdir() if f.is_dir()]
            nuevo_nombre_seguro = self.security.generate_versioned_name(
                nuevo_nombre_seguro,
                existing
            )
            carpeta_nueva = self.base_folder / nuevo_nombre_seguro
        
        try:
            # Renombrar carpeta física
            await asyncio.to_thread(
                shutil.move,
                str(carpeta_actual),
                str(carpeta_nueva)
            )
            
            # Actualizar base de datos
            idea_db = await self.db.get_idea_by_folder_name(nombre_actual_seguro)
            if idea_db:
                await self.db.rename_idea(
                    uuid=idea_db["uuid"],
                    nuevo_nombre_carpeta=nuevo_nombre_seguro,
                    nueva_ruta=str(carpeta_nueva.resolve()),
                    nuevo_nombre_idea=nuevo_nombre
                )
            
            # Actualizar metadata.json
            await self._update_metadata_after_rename(
                carpeta_nueva,
                nuevo_nombre_seguro,
                nuevo_nombre
            )
            
            self.logger.log_idea_operation(
                user_id=user_id,
                operation="rename",
                idea_name=nuevo_nombre_seguro,
                details={"anterior": nombre_actual_seguro}
            )
            
            return {
                "success": True,
                "nombre_anterior": nombre_actual_seguro,
                "nombre_nuevo": nuevo_nombre_seguro,
                "ruta": str(carpeta_nueva)
            }
            
        except Exception as e:
            self.logger.error(f"Error renombrando idea: {e}")
            return {
                "success": False,
                "error": f"Error al renombrar: {str(e)}"
            }
    
    async def _update_metadata_after_rename(self,
                                             idea_folder: Path,
                                             nuevo_nombre_carpeta: str,
                                             nuevo_nombre_idea: str):
        """Actualiza el archivo metadata.json después de renombrar."""
        meta_path = idea_folder / "metadata.json"
        if not meta_path.exists():
            return
        
        try:
            async with aiofiles.open(meta_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)
            
            # Actualizar campos
            data["sistema"]["nombre_carpeta"] = nuevo_nombre_carpeta
            data["sistema"]["nombre_original"] = nuevo_nombre_idea
            data["sistema"]["ruta_completa"] = str(idea_folder.resolve())
            data["sistema"]["fecha_ultima_modificacion"] = datetime.now().isoformat()
            data["estadisticas"]["fecha_ultima_modificacion"] = datetime.now().isoformat()
            
            async with aiofiles.open(meta_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=2, ensure_ascii=False))
                
        except Exception as e:
            self.logger.error(f"Error actualizando metadata: {e}")
    
    async def delete_idea(self,
                          nombre_carpeta: str,
                          user_id: str) -> Dict:
        """
        Elimina una idea completamente.
        
        Args:
            nombre_carpeta: Nombre de la carpeta a eliminar
            user_id: ID del usuario (debe ser admin)
        
        Returns:
            Resultado de la operación
        """
        self.logger.info(f"Eliminando idea: '{nombre_carpeta}' por usuario {user_id}")
        
        # Verificar permisos
        if not self.security.is_admin(user_id):
            return {
                "success": False,
                "error": "Solo administradores pueden eliminar ideas"
            }
        
        # Sanitizar nombre
        nombre_seguro = self.security.sanitize_filename(nombre_carpeta)
        
        # Verificar que existe
        carpeta = self.base_folder / nombre_seguro
        if not carpeta.exists():
            return {
                "success": False,
                "error": f"No existe la idea '{nombre_seguro}'"
            }
        
        # Verificar que está dentro de base_folder (seguridad)
        if not self.security.is_safe_path(carpeta):
            return {
                "success": False,
                "error": "Ruta no segura detectada"
            }
        
        try:
            # Obtener UUID antes de eliminar
            idea_db = await self.db.get_idea_by_folder_name(nombre_seguro)
            idea_uuid = idea_db.get("uuid") if idea_db else None
            
            # Eliminar carpeta física
            await asyncio.to_thread(
                shutil.rmtree,
                str(carpeta)
            )
            
            # Eliminar de base de datos
            if idea_uuid:
                await self.db.delete_idea(idea_uuid)
            
            self.logger.log_idea_operation(
                user_id=user_id,
                operation="delete",
                idea_name=nombre_seguro,
                details={"uuid": idea_uuid}
            )
            
            return {
                "success": True,
                "nombre_eliminado": nombre_seguro,
                "uuid": idea_uuid
            }
            
        except Exception as e:
            self.logger.error(f"Error eliminando idea: {e}")
            return {
                "success": False,
                "error": f"Error al eliminar: {str(e)}"
            }
    
    async def get_idea_info(self, nombre_carpeta: str) -> Optional[Dict]:
        """
        Obtiene información completa de una idea.
        
        Args:
            nombre_carpeta: Nombre de la carpeta
        
        Returns:
            Diccionario con información o None
        """
        nombre_seguro = self.security.sanitize_filename(nombre_carpeta)
        carpeta = self.base_folder / nombre_seguro
        
        if not carpeta.exists():
            return None
        
        # Leer metadata
        meta_path = carpeta / "metadata.json"
        metadata = {}
        if meta_path.exists():
            try:
                async with aiofiles.open(meta_path, 'r', encoding='utf-8') as f:
                    metadata = json.loads(await f.read())
            except Exception:
                pass
        
        # Listar archivos
        archivos = []
        for f in carpeta.iterdir():
            if f.is_file():
                archivos.append({
                    "nombre": f.name,
                    "tamanio_kb": f.stat().st_size / 1024,
                    "modificado": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                })
        
        # Info de base de datos
        db_info = await self.db.get_idea_by_folder_name(nombre_seguro)
        
        return {
            "nombre_carpeta": nombre_seguro,
            "ruta": str(carpeta),
            "existe": True,
            "metadata": metadata,
            "archivos": archivos,
            "database": db_info
        }
    
    async def list_all_ideas(self) -> List[Dict]:
        """
        Lista todas las ideas existentes.
        
        Returns:
            Lista de ideas con información básica
        """
        ideas = []
        
        for carpeta in self.base_folder.iterdir():
            if carpeta.is_dir():
                info = await self.get_idea_info(carpeta.name)
                if info:
                    ideas.append({
                        "nombre": carpeta.name,
                        "creado": info["metadata"].get("sistema", {}).get("fecha_creacion", "unknown"),
                        "tipo": info["metadata"].get("analisis", {}).get("tipo", "Otro"),
                        "archivos": len(info["archivos"])
                    })
        
        return sorted(ideas, key=lambda x: x["creado"], reverse=True)


# Import necesario
import asyncio
