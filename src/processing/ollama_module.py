"""
VoiceToVision - Módulo Ollama
Análisis de ideas usando modelos locales vía Ollama.
"""

import json
import asyncio
import aiohttp
from typing import Dict, Optional, Any
from datetime import datetime


class OllamaAnalyzer:
    """
    Analiza transcripciones usando modelos locales ejecutados con Ollama.
    Genera estructuras JSON completas de análisis de ideas.
    """
    
    # Prompt base estricto para el modelo
    SYSTEM_PROMPT = """Eres un analizador experto de ideas de negocio y proyectos.
Tu tarea es analizar transcripciones de audio y generar un JSON estructurado.

REGLAS ESTRICTAS:
1. Responde ÚNICAMENTE con un objeto JSON válido
2. NO añadas texto antes o después del JSON
3. NO uses markdown (no ```json ni ```)
4. El nombre debe ser corto, profesional, sin símbolos ni emojis
5. Máximo 5 palabras en el nombre
6. El nombre se usará como nombre de carpeta en Windows
    
ESTRUCTURA JSON REQUERIDA:
{
  "nombre_idea": "Nombre corto profesional sin símbolos",
  "resumen": "Resumen claro en 5-8 líneas explicando la idea principal",
  "explicacion": "Explicación estructurada y detallada de la idea, cómo funciona, beneficios, etc.",
  "tipo": "App / Negocio / Automatización / Contenido / Otro",
  "tags": ["tag1", "tag2", "tag3"],
  "nivel_madurez": "concepto / desarrollado / avanzado",
  "viabilidad": 7,
  "siguientes_pasos": ["paso concreto 1", "paso concreto 2", "paso concreto 3"],
  "riesgos": ["riesgo 1", "riesgo 2"]
}

RESTRICCIONES:
- nombre_idea: máximo 5 palabras, sin caracteres especiales, profesional
- resumen: 5-8 líneas de texto claro
- explicacion: párrafos bien estructurados
- tipo: exactamente uno de los valores permitidos
- tags: array de 2-5 strings, cortos y descriptivos
- nivel_madurez: exactamente uno de los valores permitidos
- viabilidad: número entero del 1 al 10
- siguientes_pasos: array de 3-5 pasos concretos y accionables
- riesgos: array de 2-4 riesgos potenciales

Ejemplo de respuesta válida:
{"nombre_idea": "App Delivery Local", "resumen": "Aplicación móvil para conectar pequeños comercios locales con clientes cercanos...", "explicacion": "El proyecto consiste en...", "tipo": "App", "tags": ["delivery", "local", "mobile"], "nivel_madurez": "concepto", "viabilidad": 8, "siguientes_pasos": ["Investigar competencia", "Validar con comercios", "Crear MVP"], "riesgos": ["Competencia establecida", "Adopción lenta"]}"""
    
    def __init__(self, config: Dict, logger):
        """
        Inicializa el analizador Ollama.
        
        Args:
            config: Configuración del sistema
            logger: Instancia de SystemLogger
        """
        self.config = config
        self.ollama_config = config.get("ollama", {})
        self.logger = logger
        
        # Configuración de conexión
        self.host = self.ollama_config.get("host", "http://localhost:11434")
        self.model = self.ollama_config.get("model", "llama3.2")
        self.timeout = self.ollama_config.get("timeout", 120)
        self.temperature = self.ollama_config.get("temperature", 0.7)
        self.max_tokens = self.ollama_config.get("max_tokens", 2000)
        
        # Campos requeridos en la respuesta
        self.required_fields = config.get("analysis", {}).get(
            "required_fields",
            [
                "nombre_idea",
                "resumen",
                "explicacion",
                "tipo",
                "tags",
                "nivel_madurez",
                "viabilidad",
                "siguientes_pasos",
                "riesgos"
            ]
        )
        
        # Valores permitidos
        self.idea_types = config.get("analysis", {}).get(
            "idea_types",
            ["App", "Negocio", "Automatización", "Contenido", "Otro"]
        )
        self.madurez_levels = config.get("analysis", {}).get(
            "madurez_levels",
            ["concepto", "desarrollado", "avanzado"]
        )
        
        self.logger.info(f"Ollama configurado: {self.host}, modelo={self.model}")
    
    async def check_connection(self) -> Dict:
        """
        Verifica que Ollama esté disponible y el modelo cargado.
        
        Returns:
            Estado de la conexión
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Verificar que Ollama responde
                async with session.get(
                    f"{self.host}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        return {
                            "available": False,
                            "error": f"Ollama respondió con status {response.status}"
                        }
                    
                    data = await response.json()
                    models = [m.get("name") for m in data.get("models", [])]
                    
                    # Verificar que el modelo requerido está disponible
                    model_available = any(
                        self.model in m or m in self.model 
                        for m in models
                    )
                    
                    return {
                        "available": True,
                        "model_available": model_available,
                        "available_models": models,
                        "required_model": self.model,
                        "host": self.host
                    }
                    
        except aiohttp.ClientError as e:
            return {
                "available": False,
                "error": f"No se pudo conectar a Ollama: {str(e)}",
                "host": self.host
            }
        except Exception as e:
            return {
                "available": False,
                "error": f"Error inesperado: {str(e)}",
                "host": self.host
            }
    
    async def analyze_idea(self, 
                           transcription: str,
                           language: str = "es") -> Dict:
        """
        Analiza una transcripción y genera estructura JSON completa.
        
        Args:
            transcription: Texto transcrito del audio
            language: Idioma de la transcripción (es/en/etc.)
        
        Returns:
            Diccionario con análisis estructurado
        """
        self.logger.info(f"Iniciando análisis con Ollama: {len(transcription)} caracteres")
        
        # Verificar conexión primero
        conn_check = await self.check_connection()
        if not conn_check["available"]:
            return {
                "success": False,
                "error": conn_check["error"],
                "stage": "connection_check"
            }
        
        if not conn_check["model_available"]:
            return {
                "success": False,
                "error": f"Modelo '{self.model}' no disponible. "
                        f"Modelos disponibles: {conn_check['available_models']}",
                "stage": "model_check"
            }
        
        # Construir prompt
        user_prompt = self._build_analysis_prompt(transcription, language)
        
        # Llamar a Ollama
        try:
            result = await self._call_ollama(user_prompt)
            
            if not result["success"]:
                return result
            
            # Parsear y validar JSON
            analysis = self._parse_and_validate_json(result["raw_response"])
            
            if analysis["success"]:
                self.logger.info(
                    f"Análisis completado: '{analysis['data'].get('nombre_idea', 'unnamed')}' "
                    f"({analysis['data'].get('tipo', 'unknown')})"
                )
            
            return analysis
            
        except asyncio.TimeoutError:
            self.logger.error("Timeout en llamada a Ollama")
            return {
                "success": False,
                "error": f"El modelo tardó más de {self.timeout} segundos en responder. "
                        "Intenta con un modelo más ligero o aumenta el timeout.",
                "stage": "timeout"
            }
        except Exception as e:
            self.logger.error(f"Error en análisis Ollama: {e}")
            return {
                "success": False,
                "error": f"Error durante el análisis: {str(e)}",
                "stage": "analysis"
            }
    
    def _build_analysis_prompt(self, 
                               transcription: str, 
                               language: str) -> str:
        """
        Construye el prompt para el análisis.
        
        Args:
            transcription: Texto transcrito
            language: Idioma
        
        Returns:
            Prompt completo
        """
        lang_instruction = {
            "es": "Responde en español.",
            "en": "Respond in English.",
            "fr": "Répondez en français.",
            "de": "Antworten Sie auf Deutsch.",
            "pt": "Responda em português."
        }.get(language, "Responde en español.")
        
        return f"""{lang_instruction}

TRANSCRIPCIÓN DEL AUDIO:
\"\"\"
{transcription}
\"\"\"

Analiza esta idea y genera el JSON estructurado según las instrucciones del sistema.
Recuerda: SOLO el JSON, sin texto adicional, sin markdown."""
    
    async def _call_ollama(self, user_prompt: str) -> Dict:
        """
        Realiza la llamada HTTP a la API de Ollama.
        
        Args:
            user_prompt: Prompt del usuario
        
        Returns:
            Respuesta cruda del modelo
        """
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": self.SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.host}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"Ollama error {response.status}: {error_text[:200]}",
                        "stage": "api_call"
                    }
                
                data = await response.json()
                
                # Extraer respuesta
                message = data.get("message", {})
                raw_response = message.get("content", "")
                
                if not raw_response:
                    return {
                        "success": False,
                        "error": "Respuesta vacía de Ollama",
                        "stage": "empty_response"
                    }
                
                return {
                    "success": True,
                    "raw_response": raw_response,
                    "model": self.model,
                    "eval_count": data.get("eval_count", 0),
                    "eval_duration": data.get("eval_duration", 0)
                }
    
    def _parse_and_validate_json(self, raw_response: str) -> Dict:
        """
        Parsea y valida la respuesta JSON del modelo.
        
        Args:
            raw_response: Texto crudo de respuesta
        
        Returns:
            Diccionario validado o error
        """
        # Limpiar respuesta (quitar markdown si existe)
        cleaned = raw_response.strip()
        
        # Quitar bloques de código markdown
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        
        cleaned = cleaned.strip()
        
        # Intentar parsear JSON
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON inválido: {e}\\nRespuesta: {raw_response[:200]}...")
            return {
                "success": False,
                "error": f"El modelo no generó JSON válido: {str(e)}",
                "raw_response": raw_response[:500],
                "stage": "json_parse"
            }
        
        # Validar campos requeridos
        missing_fields = [
            field for field in self.required_fields 
            if field not in data
        ]
        
        if missing_fields:
            return {
                "success": False,
                "error": f"Campos faltantes en respuesta: {missing_fields}",
                "data": data,
                "stage": "validation"
            }
        
        # Validar tipos y rangos
        validation_errors = []
        
        # nombre_idea: string, max 5 palabras
        nombre = data.get("nombre_idea", "")
        if len(nombre.split()) > 5:
            # Truncar a 5 palabras
            data["nombre_idea"] = " ".join(nombre.split()[:5])
            validation_errors.append("nombre_idea truncado a 5 palabras")
        
        # tipo: valor permitido
        tipo = data.get("tipo", "")
        if tipo not in self.idea_types:
            data["tipo"] = "Otro"
            validation_errors.append(f"tipo '{tipo}' no válido, usando 'Otro'")
        
        # nivel_madurez: valor permitido
        madurez = data.get("nivel_madurez", "")
        if madurez not in self.madurez_levels:
            data["nivel_madurez"] = "concepto"
            validation_errors.append(f"nivel_madurez '{madurez}' no válido, usando 'concepto'")
        
        # viabilidad: número 1-10
        viabilidad = data.get("viabilidad", 5)
        try:
            viabilidad = int(viabilidad)
            if viabilidad < 1 or viabilidad > 10:
                viabilidad = max(1, min(10, viabilidad))
                data["viabilidad"] = viabilidad
                validation_errors.append(f"viabilidad ajustada a rango 1-10: {viabilidad}")
        except (ValueError, TypeError):
            data["viabilidad"] = 5
            validation_errors.append("viabilidad no numérica, usando 5")
        
        # tags: debe ser lista
        tags = data.get("tags", [])
        if not isinstance(tags, list):
            data["tags"] = [str(tags)] if tags else []
            validation_errors.append("tags convertido a lista")
        
        # siguientes_pasos: debe ser lista
        pasos = data.get("siguientes_pasos", [])
        if not isinstance(pasos, list):
            data["siguientes_pasos"] = [str(pasos)] if pasos else []
            validation_errors.append("siguientes_pasos convertido a lista")
        
        # riesgos: debe ser lista
        riesgos = data.get("riesgos", [])
        if not isinstance(riesgos, list):
            data["riesgos"] = [str(riesgos)] if riesgos else []
            validation_errors.append("riesgos convertido a lista")
        
        if validation_errors:
            self.logger.warning(f"Validación con correcciones: {validation_errors}")
        
        return {
            "success": True,
            "data": data,
            "validation_warnings": validation_errors if validation_errors else None,
            "raw_response": raw_response[:200]
        }
    
    async def regenerate_field(self,
                                transcription: str,
                                field_name: str,
                                current_data: Dict,
                                feedback: str) -> Dict:
        """
        Regenera un campo específico del análisis.
        
        Args:
            transcription: Transcripción original
            field_name: Campo a regenerar
            current_data: Datos actuales
            feedback: Feedback para mejorar
        
        Returns:
            Nuevo valor para el campo
        """
        prompt = f"""Basado en esta transcripción:
\"\"\"
{transcription}
\"\"\"

Y estos datos actuales: {json.dumps(current_data, ensure_ascii=False)}

Por favor, regenera ÚNICAMENTE el campo '{field_name}' con esta mejora: {feedback}

Responde SOLO con el nuevo valor para '{field_name}', en formato JSON:
{{"{field_name}": "nuevo valor"}}"""
        
        result = await self._call_ollama(prompt)
        
        if not result["success"]:
            return result
        
        try:
            # Limpiar y parsear
            cleaned = result["raw_response"].strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            cleaned = cleaned.strip()
            
            new_data = json.loads(cleaned)
            
            if field_name in new_data:
                return {
                    "success": True,
                    "field": field_name,
                    "new_value": new_data[field_name]
                }
            else:
                return {
                    "success": False,
                    "error": f"Campo '{field_name}' no encontrado en respuesta"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error regenerando campo: {str(e)}"
            }
    
    def get_config(self) -> Dict:
        """
        Retorna configuración actual del analizador.
        
        Returns:
            Configuración
        """
        return {
            "host": self.host,
            "model": self.model,
            "timeout": self.timeout,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "required_fields": self.required_fields,
            "idea_types": self.idea_types,
            "madurez_levels": self.madurez_levels
        }
