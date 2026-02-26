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
VoiceToVision - Base de Datos SQLite
Sistema de indexación rápida para ideas con SQLite.
"""


import aiosqlite
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import asyncio


class IdeasDatabase:
    """
    Base de datos SQLite para indexación rápida de ideas.
    Mantiene metadatos indexados mientras los archivos completos 
    permanecen en el sistema de carpetas.
    """
    
    def __init__(self, db_path: str = "./data/ideas.db"):
        """
        Inicializa la conexión a la base de datos.
        
        Args:
            db_path: Ruta al archivo de base de datos SQLite
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: Optional[aiosqlite.Connection] = None
    
    async def connect(self):
        """Establece conexión asíncrona con la base de datos."""
        self._connection = await aiosqlite.connect(self.db_path)
        await self._create_tables()
        return self
    
    async def close(self):
        """Cierra la conexión a la base de datos."""
        if self._connection:
            await self._connection.close()
            self._connection = None
    
    async def _create_tables(self):
        """Crea las tablas necesarias si no existen."""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS ideas (
                id TEXT PRIMARY KEY,
                uuid TEXT UNIQUE NOT NULL,
                nombre_carpeta TEXT UNIQUE NOT NULL,
                nombre_idea TEXT NOT NULL,
                ruta_completa TEXT NOT NULL,
                fecha_creacion TEXT NOT NULL,
                fecha_modificacion TEXT NOT NULL,
                creado_por TEXT NOT NULL,
                version INTEGER DEFAULT 1,
                tipo TEXT,
                nivel_madurez TEXT,
                viabilidad INTEGER,
                tags TEXT,  -- JSON array
                resumen TEXT,
                tamanio_total_kb INTEGER,
                num_archivos INTEGER DEFAULT 0,
                metadata_completa TEXT  -- JSON completo
            )
        """)
        
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS versiones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idea_uuid TEXT NOT NULL,
                version_num INTEGER NOT NULL,
                nombre_carpeta TEXT NOT NULL,
                ruta_completa TEXT NOT NULL,
                fecha_creacion TEXT NOT NULL,
                motivo TEXT,
                FOREIGN KEY (idea_uuid) REFERENCES ideas(uuid)
            )
        """)
        
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS archivos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idea_uuid TEXT NOT NULL,
                nombre_archivo TEXT NOT NULL,
                tipo_archivo TEXT NOT NULL,
                ruta_relativa TEXT NOT NULL,
                tamanio_kb INTEGER,
                fecha_creacion TEXT,
                FOREIGN KEY (idea_uuid) REFERENCES ideas(uuid)
            )
        """)
        
        # Índices para búsquedas rápidas
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_ideas_nombre 
            ON ideas(nombre_idea)
        """)
        
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_ideas_carpeta 
            ON ideas(nombre_carpeta)
        """)
        
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_ideas_tags 
            ON ideas(tags)
        """)
        
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_ideas_tipo 
            ON ideas(tipo)
        """)
        
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_ideas_fecha 
            ON ideas(fecha_creacion)
        """)
        
        await self._connection.commit()
    
    async def create_idea(self, 
                         nombre_idea: str,
                         nombre_carpeta: str,
                         ruta_completa: str,
                         creado_por: str,
                         tipo: str = "Otro",
                         nivel_madurez: str = "concepto",
                         viabilidad: int = 5,
                         tags: List[str] = None,
                         resumen: str = "",
                         metadata_completa: Dict = None) -> str:
        """
        Crea un nuevo registro de idea en la base de datos.
        
        Args:
            nombre_idea: Nombre legible de la idea
            nombre_carpeta: Nombre sanitizado de la carpeta
            ruta_completa: Ruta completa al directorio
            creado_por: ID del usuario creador
            tipo: Tipo de idea (App, Negocio, etc.)
            nivel_madurez: Nivel de madurez
            viabilidad: Puntuación 1-10
            tags: Lista de tags
            resumen: Resumen corto
            metadata_completa: Diccionario completo de metadatos
        
        Returns:
            UUID generado para la idea
        """
        idea_uuid = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        await self._connection.execute("""
            INSERT INTO ideas (
                id, uuid, nombre_carpeta, nombre_idea, ruta_completa,
                fecha_creacion, fecha_modificacion, creado_por, version,
                tipo, nivel_madurez, viabilidad, tags, resumen,
                tamanio_total_kb, num_archivos, metadata_completa
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            idea_uuid[:8],  # ID corto para referencia
            idea_uuid,
            nombre_carpeta,
            nombre_idea,
            str(ruta_completa),
            now,
            now,
            str(creado_por),
            1,  # Versión inicial
            tipo,
            nivel_madurez,
            viabilidad,
            json.dumps(tags or [], ensure_ascii=False),
            resumen,
            0,  # Tamaño inicial
            0,  # Número de archivos inicial
            json.dumps(metadata_completa or {}, ensure_ascii=False)
        ))
        
        await self._connection.commit()
        return idea_uuid
    
    async def get_idea_by_uuid(self, uuid: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene una idea por su UUID.
        
        Args:
            uuid: UUID de la idea
        
        Returns:
            Diccionario con los datos de la idea o None
        """
        async with self._connection.execute(
            "SELECT * FROM ideas WHERE uuid = ?", (uuid,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return self._row_to_dict(row, cursor)
            return None
    
    async def get_idea_by_folder_name(self, nombre_carpeta: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene una idea por nombre de carpeta.
        
        Args:
            nombre_carpeta: Nombre de la carpeta
        
        Returns:
            Diccionario con los datos de la idea o None
        """
        async with self._connection.execute(
            "SELECT * FROM ideas WHERE nombre_carpeta = ?", (nombre_carpeta,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return self._row_to_dict(row, cursor)
            return None
    
    async def search_ideas(self, 
                          query: str = "",
                          tipo: Optional[str] = None,
                          tags: Optional[List[str]] = None,
                          nivel_madurez: Optional[str] = None,
                          creado_por: Optional[str] = None,
                          limit: int = 50) -> List[Dict[str, Any]]:
        """
        Busca ideas con filtros opcionales.
        
        Args:
            query: Texto a buscar en nombre o resumen
            tipo: Filtrar por tipo
            tags: Filtrar por tags (coincide cualquiera)
            nivel_madurez: Filtrar por madurez
            creado_por: Filtrar por creador
            limit: Límite de resultados
        
        Returns:
            Lista de ideas que coinciden
        """
        conditions = []
        params = []
        
        if query:
            conditions.append(
                "(nombre_idea LIKE ? OR resumen LIKE ? OR nombre_carpeta LIKE ?)"
            )
            like_query = f"%{query}%"
            params.extend([like_query, like_query, like_query])
        
        if tipo:
            conditions.append("tipo = ?")
            params.append(tipo)
        
        if nivel_madurez:
            conditions.append("nivel_madurez = ?")
            params.append(nivel_madurez)
        
        if creado_por:
            conditions.append("creado_por = ?")
            params.append(str(creado_por))
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        sql = f"""
            SELECT * FROM ideas 
            WHERE {where_clause}
            ORDER BY fecha_creacion DESC
            LIMIT ?
        """
        params.append(limit)
        
        async with self._connection.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_dict(row, cursor) for row in rows]
    
    async def update_idea(self, uuid: str, updates: Dict[str, Any]) -> bool:
        """
        Actualiza campos de una idea.
        
        Args:
            uuid: UUID de la idea
            updates: Diccionario con campos a actualizar
        
        Returns:
            True si se actualizó, False si no existe
        """
        # No permitir actualizar uuid, id, fecha_creacion
        forbidden = {'uuid', 'id', 'fecha_creacion', 'creado_por'}
        updates = {k: v for k, v in updates.items() if k not in forbidden}
        
        if not updates:
            return False
        
        # Añadir fecha de modificación
        updates['fecha_modificacion'] = datetime.now().isoformat()
        
        # Convertir listas/dict a JSON
        if 'tags' in updates and isinstance(updates['tags'], list):
            updates['tags'] = json.dumps(updates['tags'], ensure_ascii=False)
        if 'metadata_completa' in updates and isinstance(updates['metadata_completa'], dict):
            updates['metadata_completa'] = json.dumps(
                updates['metadata_completa'], 
                ensure_ascii=False
            )
        
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [uuid]
        
        await self._connection.execute(
            f"UPDATE ideas SET {set_clause} WHERE uuid = ?",
            values
        )
        await self._connection.commit()
        
        return True
    
    async def rename_idea(self, 
                         uuid: str, 
                         nuevo_nombre_carpeta: str,
                         nueva_ruta: str,
                         nuevo_nombre_idea: Optional[str] = None) -> bool:
        """
        Renombra una idea, creando una nueva versión.
        
        Args:
            uuid: UUID de la idea
            nuevo_nombre_carpeta: Nuevo nombre de carpeta
            nueva_ruta: Nueva ruta completa
            nuevo_nombre_idea: Nuevo nombre de idea (opcional)
        
        Returns:
            True si se renombró exitosamente
        """
        # Obtener idea actual
        idea = await self.get_idea_by_uuid(uuid)
        if not idea:
            return False
        
        # Guardar versión anterior
        await self._connection.execute("""
            INSERT INTO versiones (
                idea_uuid, version_num, nombre_carpeta, 
                ruta_completa, fecha_creacion, motivo
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            uuid,
            idea['version'],
            idea['nombre_carpeta'],
            idea['ruta_completa'],
            idea['fecha_modificacion'],
            "Renombrado por usuario"
        ))
        
        # Actualizar idea
        updates = {
            'nombre_carpeta': nuevo_nombre_carpeta,
            'ruta_completa': nueva_ruta,
            'version': idea['version'] + 1
        }
        if nuevo_nombre_idea:
            updates['nombre_idea'] = nuevo_nombre_idea
        
        return await self.update_idea(uuid, updates)
    
    async def delete_idea(self, uuid: str) -> bool:
        """
        Elimina una idea de la base de datos.
        
        Args:
            uuid: UUID de la idea
        
        Returns:
            True si se eliminó, False si no existía
        """
        # Primero eliminar archivos relacionados
        await self._connection.execute(
            "DELETE FROM archivos WHERE idea_uuid = ?",
            (uuid,)
        )
        
        # Eliminar versiones
        await self._connection.execute(
            "DELETE FROM versiones WHERE idea_uuid = ?",
            (uuid,)
        )
        
        # Eliminar idea
        cursor = await self._connection.execute(
            "DELETE FROM ideas WHERE uuid = ?",
            (uuid,)
        )
        await self._connection.commit()
        
        return cursor.rowcount > 0
    
    async def add_file_to_idea(self,
                                idea_uuid: str,
                                nombre_archivo: str,
                                tipo_archivo: str,
                                ruta_relativa: str,
                                tamanio_kb: int = 0) -> bool:
        """
        Registra un archivo asociado a una idea.
        
        Args:
            idea_uuid: UUID de la idea
            nombre_archivo: Nombre del archivo
            tipo_archivo: Tipo (audio, texto, json, etc.)
            ruta_relativa: Ruta relativa dentro de la carpeta
            tamanio_kb: Tamaño en KB
        
        Returns:
            True si se agregó correctamente
        """
        now = datetime.now().isoformat()
        
        await self._connection.execute("""
            INSERT INTO archivos (
                idea_uuid, nombre_archivo, tipo_archivo,
                ruta_relativa, tamanio_kb, fecha_creacion
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            idea_uuid,
            nombre_archivo,
            tipo_archivo,
            ruta_relativa,
            tamanio_kb,
            now
        ))
        
        # Actualizar contador de archivos
        await self._connection.execute("""
            UPDATE ideas 
            SET num_archivos = num_archivos + 1,
                tamanio_total_kb = tamanio_total_kb + ?
            WHERE uuid = ?
        """, (tamanio_kb, idea_uuid))
        
        await self._connection.commit()
        return True
    
    async def get_idea_files(self, idea_uuid: str) -> List[Dict[str, Any]]:
        """
        Obtiene todos los archivos de una idea.
        
        Args:
            idea_uuid: UUID de la idea
        
        Returns:
            Lista de archivos
        """
        async with self._connection.execute(
            "SELECT * FROM archivos WHERE idea_uuid = ?",
            (idea_uuid,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_dict(row, cursor) for row in rows]
    
    async def get_all_ideas(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Obtiene todas las ideas ordenadas por fecha.
        
        Args:
            limit: Límite de resultados
        
        Returns:
            Lista de todas las ideas
        """
        async with self._connection.execute(
            "SELECT * FROM ideas ORDER BY fecha_creacion DESC LIMIT ?",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_dict(row, cursor) for row in rows]
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del sistema.
        
        Returns:
            Diccionario con estadísticas
        """
        stats = {}
        
        # Total de ideas
        async with self._connection.execute(
            "SELECT COUNT(*) FROM ideas"
        ) as cursor:
            stats['total_ideas'] = (await cursor.fetchone())[0]
        
        # Por tipo
        async with self._connection.execute(
            "SELECT tipo, COUNT(*) FROM ideas GROUP BY tipo"
        ) as cursor:
            stats['por_tipo'] = {
                row[0]: row[1] async for row in cursor
            }
        
        # Por nivel de madurez
        async with self._connection.execute(
            "SELECT nivel_madurez, COUNT(*) FROM ideas GROUP BY nivel_madurez"
        ) as cursor:
            stats['por_madurez'] = {
                row[0]: row[1] async for row in cursor
            }
        
        # Tamaño total
        async with self._connection.execute(
            "SELECT SUM(tamanio_total_kb) FROM ideas"
        ) as cursor:
            result = await cursor.fetchone()
            stats['tamanio_total_mb'] = (result[0] or 0) / 1024
        
        # Ideas recientes (últimos 7 días)
        from datetime import timedelta
        hace_7_dias = (datetime.now() - timedelta(days=7)).isoformat()
        async with self._connection.execute(
            "SELECT COUNT(*) FROM ideas WHERE fecha_creacion > ?",
            (hace_7_dias,)
        ) as cursor:
            stats['ideas_recientes'] = (await cursor.fetchone())[0]
        
        return stats
    
    def _row_to_dict(self, row, cursor) -> Dict[str, Any]:
        """Convierte una fila de SQLite a diccionario."""
        result = {}
        for idx, col in enumerate(cursor.description):
            value = row[idx]
            col_name = col[0]
            
            # Parsear JSON
            if col_name in ['tags', 'metadata_completa'] and value:
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    pass
            
            result[col_name] = value
        
        return result


# Instancia global de la base de datos
_db_instance: Optional[IdeasDatabase] = None


async def get_database(db_path: str = "./data/ideas.db") -> IdeasDatabase:
    """
    Obtiene instancia de la base de datos (singleton).
    
    Args:
        db_path: Ruta a la base de datos
    
    Returns:
        Instancia conectada de IdeasDatabase
    """
    global _db_instance
    
    if _db_instance is None:
        _db_instance = IdeasDatabase(db_path)
        await _db_instance.connect()
    
    return _db_instance


async def close_database():
    """Cierra la conexión global de la base de datos."""
    global _db_instance
    if _db_instance:
        await _db_instance.close()
        _db_instance = None
