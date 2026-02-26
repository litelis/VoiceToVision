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
VoiceToVision - Motor de Búsqueda
Búsqueda rápida de ideas usando SQLite y filtros avanzados.
"""


import re
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher


class SearchEngine:
    """
    Motor de búsqueda para ideas con múltiples criterios
    y coincidencia parcial difusa.
    """
    
    def __init__(self, database, security_manager, logger):
        """
        Inicializa el motor de búsqueda.
        
        Args:
            database: Instancia de IdeasDatabase
            security_manager: Instancia de SecurityManager
            logger: Instancia de SystemLogger
        """
        self.db = database
        self.security = security_manager
        self.logger = logger
        
        # Umbral de similitud para búsqueda difusa (0.0 - 1.0)
        self.similarity_threshold = 0.6
    
    async def search(self,
                     query: str,
                     user_id: str,
                     filters: Optional[Dict] = None,
                     limit: int = 20) -> Dict:
        """
        Busca ideas con coincidencia parcial en nombre.
        
        Args:
            query: Texto a buscar
            user_id: ID del usuario que busca
            filters: Filtros adicionales (tipo, madurez, etc.)
            limit: Máximo de resultados
        
        Returns:
            Resultados de búsqueda con scoring
        """
        self.logger.info(f"Búsqueda por '{query}' por usuario {user_id}")
        
        # Verificar autorización
        if not self.security.is_authorized(user_id):
            return {
                "success": False,
                "error": "Usuario no autorizado",
                "results": []
            }
        
        filters = filters or {}
        
        # Buscar en base de datos
        db_results = await self.db.search_ideas(
            query=query,
            tipo=filters.get("tipo"),
            tags=filters.get("tags"),
            nivel_madurez=filters.get("nivel_madurez"),
            creado_por=filters.get("creado_por"),
            limit=limit * 2  # Pedir más para filtrar por similitud
        )
        
        # Calcular scores de similitud
        scored_results = []
        query_lower = query.lower()
        
        for idea in db_results:
            scores = self._calculate_match_scores(idea, query_lower)
            
            # Solo incluir si hay coincidencia significativa
            if scores["total"] > 0.3:
                scored_results.append({
                    **idea,
                    "match_scores": scores,
                    "match_total": scores["total"]
                })
        
        # Ordenar por score total
        scored_results.sort(key=lambda x: x["match_total"], reverse=True)
        
        # Limitar resultados finales
        final_results = scored_results[:limit]
        
        self.logger.log_idea_operation(
            user_id=user_id,
            operation="search",
            idea_name=query,
            details={"results_found": len(final_results), "query": query}
        )
        
        return {
            "success": True,
            "query": query,
            "total_found": len(scored_results),
            "results_returned": len(final_results),
            "results": final_results
        }
    
    def _calculate_match_scores(self, idea: Dict, query: str) -> Dict:
        """
        Calcula scores de coincidencia para una idea.
        
        Args:
            idea: Datos de la idea
            query: Query en minúsculas
        
        Returns:
            Diccionario con scores individuales y total
        """
        scores = {
            "nombre_exacto": 0.0,
            "nombre_parcial": 0.0,
            "nombre_fuzzy": 0.0,
            "resumen": 0.0,
            "tags": 0.0,
            "total": 0.0
        }
        
        # Nombre de carpeta
        nombre_carpeta = idea.get("nombre_carpeta", "").lower()
        if query == nombre_carpeta:
            scores["nombre_exacto"] = 1.0
        elif query in nombre_carpeta:
            scores["nombre_parcial"] = 0.8
        else:
            # Similitud difusa
            scores["nombre_fuzzy"] = SequenceMatcher(
                None, query, nombre_carpeta
            ).ratio()
        
        # Nombre de idea
        nombre_idea = idea.get("nombre_idea", "").lower()
        if query in nombre_idea:
            scores["nombre_parcial"] = max(scores["nombre_parcial"], 0.7)
        
        # Resumen
        resumen = idea.get("resumen", "").lower()
        if query in resumen:
            # Score basado en posición (más alto si aparece al inicio)
            position = resumen.find(query)
            scores["resumen"] = max(0.0, 0.5 - (position / 1000))
        
        # Tags
        tags = idea.get("tags", [])
        if isinstance(tags, str):
            try:
                import json
                tags = json.loads(tags)
            except:
                tags = []
        
        query_words = query.split()
        matching_tags = sum(1 for tag in tags if any(
            qw in tag.lower() for qw in query_words
        ))
        if matching_tags > 0:
            scores["tags"] = min(0.6, matching_tags * 0.3)
        
        # Calcular total ponderado
        scores["total"] = max(
            scores["nombre_exacto"],
            scores["nombre_parcial"],
            scores["nombre_fuzzy"] * 0.7,
            scores["resumen"],
            scores["tags"]
        )
        
        return scores
    
    async def quick_search_by_name(self,
                                    name_prefix: str,
                                    user_id: str,
                                    limit: int = 10) -> List[Dict]:
        """
        Búsqueda rápida por prefijo de nombre.
        
        Args:
            name_prefix: Prefijo a buscar
            user_id: ID del usuario
            limit: Límite de resultados
        
        Returns:
            Lista de ideas que coinciden
        """
        if not self.security.is_authorized(user_id):
            return []
        
        # Sanitizar input
        safe_prefix = self.security.sanitize_filename(name_prefix).lower()
        
        # Buscar en base de datos
        all_ideas = await self.db.get_all_ideas(limit=1000)
        
        matches = []
        for idea in all_ideas:
            nombre = idea.get("nombre_carpeta", "").lower()
            if nombre.startswith(safe_prefix) or safe_prefix in nombre:
                matches.append(idea)
        
        return matches[:limit]
    
    async def advanced_search(self,
                             user_id: str,
                             criteria: Dict,
                             limit: int = 50) -> Dict:
        """
        Búsqueda avanzada con múltiples criterios.
        
        Args:
            user_id: ID del usuario
            criteria: Diccionario de criterios
            limit: Límite de resultados
        
        Returns:
            Resultados filtrados
        """
        if not self.security.is_authorized(user_id):
            return {
                "success": False,
                "error": "No autorizado",
                "results": []
            }
        
        # Extraer criterios
        query = criteria.get("query", "")
        tipo = criteria.get("tipo")
        madurez = criteria.get("nivel_madurez")
        viabilidad_min = criteria.get("viabilidad_min")
        viabilidad_max = criteria.get("viabilidad_max")
        tags = criteria.get("tags", [])
        fecha_desde = criteria.get("fecha_desde")
        fecha_hasta = criteria.get("fecha_hasta")
        creado_por = criteria.get("creado_por")
        
        # Buscar en base de datos
        results = await self.db.search_ideas(
            query=query,
            tipo=tipo,
            tags=tags if tags else None,
            nivel_madurez=madurez,
            creado_por=creado_por,
            limit=limit * 2
        )
        
        # Filtrar por viabilidad
        if viabilidad_min is not None or viabilidad_max is not None:
            filtered = []
            for idea in results:
                viab = idea.get("viabilidad", 5)
                if viabilidad_min is not None and viab < viabilidad_min:
                    continue
                if viabilidad_max is not None and viab > viabilidad_max:
                    continue
                filtered.append(idea)
            results = filtered
        
        # Filtrar por fecha
        if fecha_desde or fecha_hasta:
            filtered = []
            for idea in results:
                fecha = idea.get("fecha_creacion", "")
                if fecha_desde and fecha < fecha_desde:
                    continue
                if fecha_hasta and fecha > fecha_hasta:
                    continue
                filtered.append(idea)
            results = filtered
        
        # Ordenar por relevancia o fecha
        sort_by = criteria.get("sort_by", "relevance")
        if sort_by == "fecha":
            results.sort(key=lambda x: x.get("fecha_creacion", ""), reverse=True)
        elif sort_by == "viabilidad":
            results.sort(key=lambda x: x.get("viabilidad", 0), reverse=True)
        elif sort_by == "nombre":
            results.sort(key=lambda x: x.get("nombre_idea", "").lower())
        
        return {
            "success": True,
            "criteria": criteria,
            "total_found": len(results),
            "results": results[:limit]
        }
    
    async def get_suggestions(self,
                               partial: str,
                               user_id: str,
                               limit: int = 5) -> List[str]:
        """
        Genera sugerencias de autocompletado.
        
        Args:
            partial: Texto parcial ingresado
            user_id: ID del usuario
            limit: Número de sugerencias
        
        Returns:
            Lista de sugerencias
        """
        if not self.security.is_authorized(user_id) or len(partial) < 2:
            return []
        
        partial_lower = partial.lower()
        
        # Buscar ideas que coincidan
        all_ideas = await self.db.get_all_ideas(limit=200)
        
        suggestions = []
        for idea in all_ideas:
            nombre = idea.get("nombre_carpeta", "")
            if partial_lower in nombre.lower():
                suggestions.append(nombre)
        
        # Ordenar por relevancia (coincidencia al inicio primero)
        suggestions.sort(key=lambda x: (
            0 if x.lower().startswith(partial_lower) else 1,
            x.lower()
        ))
        
        return suggestions[:limit]
    
    async def get_recent_ideas(self,
                                user_id: str,
                                days: int = 7,
                                limit: int = 10) -> List[Dict]:
        """
        Obtiene ideas recientes.
        
        Args:
            user_id: ID del usuario
            days: Días hacia atrás
            limit: Límite de resultados
        
        Returns:
            Lista de ideas recientes
        """
        if not self.security.is_authorized(user_id):
            return []
        
        from datetime import datetime, timedelta
        
        fecha_limite = (datetime.now() - timedelta(days=days)).isoformat()
        
        all_ideas = await self.db.get_all_ideas(limit=1000)
        
        recent = [
            idea for idea in all_ideas
            if idea.get("fecha_creacion", "") > fecha_limite
        ]
        
        # Ordenar por fecha descendente
        recent.sort(key=lambda x: x.get("fecha_creacion", ""), reverse=True)
        
        return recent[:limit]
    
    async def get_statistics(self, user_id: str) -> Dict:
        """
        Obtiene estadísticas de búsqueda y sistema.
        
        Args:
            user_id: ID del usuario
        
        Returns:
            Estadísticas del sistema
        """
        if not self.security.is_authorized(user_id):
            return {"error": "No autorizado"}
        
        stats = await self.db.get_statistics()
        
        # Añadir info de búsqueda
        all_ideas = await self.db.get_all_ideas(limit=1)
        
        return {
            **stats,
            "search_available": True,
            "total_indexed": stats.get("total_ideas", 0)
        }
