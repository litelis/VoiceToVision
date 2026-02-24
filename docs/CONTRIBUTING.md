# 🤝 Guía de Contribución

¡Gracias por tu interés en contribuir a VoiceToVision! Este documento te guiará para hacer contribuciones efectivas.

## 📋 Cómo Contribuir

### 1. Reportar Issues

Si encuentras un bug o tienes una sugerencia:

1. **Busca** issues existentes antes de crear uno nuevo
2. **Usa** plantillas de issues cuando estén disponibles
3. **Proporciona** información detallada:
   - Versión de Python
   - Sistema operativo
   - Pasos para reproducir
   - Logs de error (sin información sensible)

### 2. Pull Requests

#### Flujo de Trabajo

1. **Fork** el repositorio
2. **Crea** una rama descriptiva:
   ```bash
   git checkout -b feature/nueva-funcionalidad
   git checkout -b fix/correccion-bug
   git checkout -b docs/mejora-documentacion
   ```
3. **Haz** commits claros y descriptivos
4. **Asegúrate** de que los tests pasen
5. **Actualiza** documentación si es necesario
6. **Envía** el Pull Request

#### Estándares de Código

##### Python (PEP 8)

```python
# ✅ Correcto
def process_audio(file_path: Path, user_id: str) -> Dict:
    """
    Procesa un archivo de audio.
    
    Args:
        file_path: Ruta al archivo
        user_id: ID del usuario
    
    Returns:
        Diccionario con resultados
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
    
    return {"success": True}

# ❌ Incorrecto
def process_audio(file_path, user_id):
    """procesa audio"""
    if not os.path.exists(file_path):
        return None
    return True
```

##### Reglas Específicas

- **Líneas**: Máximo 100 caracteres
- **Imports**: Ordenados (stdlib, terceros, locales)
- **Tipado**: Usar type hints en todas las funciones públicas
- **Docstrings**: Formato Google/NumPy para todas las funciones
- **Nombres**: 
  - `snake_case` para funciones/variables
  - `PascalCase` para clases
  - `SCREAMING_SNAKE_CASE` para constantes

##### Ejemplo Completo

```python
"""
VoiceToVision - Módulo de Ejemplo
Descripción corta del módulo.
"""

import os
from pathlib import Path
from typing import Dict, Optional, List
import aiofiles

from src.core.logger import get_logger


class ExampleProcessor:
    """
    Procesador de ejemplo que demuestra estándares de código.
    
    Attributes:
        config: Configuración del sistema
        logger: Instancia de logger
    """
    
    # Constantes de clase
    MAX_RETRIES = 3
    DEFAULT_TIMEOUT = 30
    
    def __init__(self, config: Dict, logger=None):
        """
        Inicializa el procesador.
        
        Args:
            config: Configuración del sistema
            logger: Logger opcional
        """
        self.config = config
        self.logger = logger or get_logger()
        self._initialized = False
    
    async def process_file(self,
                           file_path: Path,
                           options: Optional[Dict] = None) -> Dict:
        """
        Procesa un archivo con las opciones especificadas.
        
        Args:
            file_path: Ruta al archivo a procesar
            options: Opciones de procesamiento opcionales
        
        Returns:
            Diccionario con:
                - success: bool
                - result: datos procesados
                - error: mensaje de error si falló
        
        Raises:
            FileNotFoundError: Si el archivo no existe
            ValueError: Si las opciones son inválidas
        """
        # Validación de entrada
        if not file_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        
        options = options or {}
        
        try:
            # Lógica principal
            result = await self._internal_process(file_path, options)
            
            self.logger.info(f"Procesado exitoso: {file_path.name}")
            
            return {
                "success": True,
                "result": result,
                "error": None
            }
            
        except Exception as e:
            self.logger.error(f"Error procesando {file_path}: {e}")
            return {
                "success": False,
                "result": None,
                "error": str(e)
            }
    
    async def _internal_process(self,
                                 file_path: Path,
                                 options: Dict) -> List[Dict]:
        """
        Procesamiento interno (privado).
        
        Args:
            file_path: Ruta al archivo
            options: Opciones validadas
        
        Returns:
            Lista de resultados procesados
        """
        # Implementación privada con underscore
        results = []
        
        async with aiofiles.open(file_path, 'r') as f:
            content = await f.read()
            # Procesamiento...
        
        return results
```

### 3. Testing

#### Tests Unitarios

```python
# tests/test_security.py
import pytest
from src.core.security import SecurityManager


@pytest.fixture
def security():
    config = {
        "discord": {
            "authorized_users": ["123", "456"],
            "admins": ["123"]
        },
        "system": {
            "max_audio_size_mb": 25,
            "base_folder": "./test_ideas"
        }
    }
    return SecurityManager(config)


def test_sanitize_filename(security):
    # Arrange
    dirty_name = "Mi Idea: Con Símbolos <raro>!"
    
    # Act
    clean = security.sanitize_filename(dirty_name)
    
    # Assert
    assert clean == "Mi_Idea_Con_Simbolos_raro_"
    assert "<" not in clean
    assert ">" not in clean


def test_is_admin(security):
    assert security.is_admin("123") is True
    assert security.is_admin("456") is False
    assert security.is_admin("789") is False
```

#### Ejecutar Tests

```bash
# Instalar dependencias de test
pip install pytest pytest-asyncio pytest-cov

# Ejecutar todos los tests
pytest

# Con cobertura
pytest --cov=. --cov-report=html

# Tests específicos
pytest tests/test_security.py -v
```

### 4. Documentación

#### Docstrings

Todas las funciones públicas deben tener docstrings:

```python
def function_name(param1: type, param2: type) -> return_type:
    """
    Breve descripción de una línea.
    
    Descripción más detallada si es necesario.
    Puede incluir múltiples párrafos.
    
    Args:
        param1: Descripción del parámetro
        param2: Descripción del parámetro
    
    Returns:
        Descripción del valor retornado
    
    Raises:
        ExceptionType: Cuándo se lanza esta excepción
    
    Example:
        >>> result = function_name("valor1", "valor2")
        >>> print(result)
        'resultado esperado'
    """
```

#### README y Guías

- Mantener README.md actualizado
- Añadir ejemplos de uso
- Documentar cambios en CHANGELOG.md

### 5. Commits

#### Formato de Mensajes

```
tipo(ámbito): descripción corta (máx 50 chars)

Descripción más detallada si es necesario.
Puede incluir múltiples párrafos explicando
el porqué del cambio, no solo el qué.

- Lista de cambios específicos
- Otro cambio relevante

Closes #123, Relates to #456
```

#### Tipos de Commit

- **feat**: Nueva funcionalidad
- **fix**: Corrección de bug
- **docs**: Cambios en documentación
- **style**: Formato (sin cambios de código)
- **refactor**: Refactorización
- **test**: Tests
- **chore**: Mantenimiento

#### Ejemplos

```bash
# ✅ Buenos commits
git commit -m "feat(bot): añade comando /stats para estadísticas"
git commit -m "fix(security): corrige validación de rutas en Windows"
git commit -m "docs(readme): actualiza instrucciones de instalación"

# ❌ Evitar
git commit -m "cambios"
git commit -m "fix"
git commit -m "actualización"
```

## 🏗️ Arquitectura del Proyecto

### Estructura de Módulos

```
VoiceToVision/
├── bot.py              # Entry point, bot Discord
├── setup.py            # Configuración inicial
├── requirements.txt    # Dependencias
├── config.json         # Configuración
├── .env               # Variables de entorno
│
├── Core Modules:
│   ├── logger.py      # Logging centralizado
│   ├── database.py    # SQLite async
│   └── security.py    # Autenticación y seguridad
│
├── Processing:
│   ├── audio_processor.py   # FFmpeg, validación
│   ├── whisper_module.py    # Transcripción
│   └── ollama_module.py     # Análisis IA
│
├── Management:
│   ├── idea_manager.py      # CRUD de ideas
│   ├── search_engine.py     # Búsqueda
│   └── zip_manager.py       # Descargas
│
└── tests/             # Tests unitarios
```

### Dependencias entre Módulos

```
bot.py
  ├── security.py (autenticación)
  ├── logger.py (logging)
  ├── database.py (datos)
  ├── audio_processor.py
  │   └── security.py
  ├── whisper_module.py
  ├── ollama_module.py
  ├── idea_manager.py
  │   ├── database.py
  │   └── security.py
  ├── search_engine.py
  │   └── database.py
  └── zip_manager.py
      └── security.py
```

## 🔒 Seguridad

### Reportar Vulnerabilidades

**NO** abras un issue público para vulnerabilidades de seguridad.

En su lugar:
1. Envía un email a: security@voicetovision.dev
2. Incluye descripción detallada
3. Proporciona pasos de reproducción
4. Espera respuesta antes de divulgar públicamente

### Buenas Prácticas de Seguridad

- Nunca commitear archivos `.env`
- Sanitizar todas las entradas de usuario
- Validar rutas contra path traversal
- Usar parámetros en queries SQL (no concatenación)
- Hashear datos sensibles
- Validar tipos y rangos de datos

## 📝 Checklist de Pull Request

Antes de enviar tu PR:

- [ ] Código sigue PEP 8
- [ ] Todos los tests pasan
- [ ] Nueva funcionalidad tiene tests
- [ ] Documentación actualizada
- [ ] Commits siguen formato convencional
- [ ] No hay secrets/token expuestos
- [ ] CHANGELOG.md actualizado (si aplica)

## 🎯 Áreas de Contribución Prioritarias

### Alto Impacto
- 🐛 Bug fixes críticos
- 🧪 Tests de cobertura
- 📚 Mejoras de documentación
- ♿ Accesibilidad

### Nuevas Funcionalidades
- 📱 Integración WhatsApp completa
- 🌐 Dashboard web
- 📊 Visualizaciones de datos
- 🔌 Sistema de plugins

### Optimización
- ⚡ Mejoras de rendimiento
- 💾 Reducción de uso de memoria
- 🚀 Caching inteligente

## 💬 Comunicación

- **Discord**: [Servidor de desarrollo](https://discord.gg/voicetovision)
- **Discussions**: Usa GitHub Discussions para preguntas
- **Issues**: Reporta bugs y solicita features

## 🙏 Código de Conducta

### Nuestros Valores

- **Respeto**: Trata a todos con respeto y profesionalismo
- **Inclusión**: Bienvenidas contribuciones de todos los niveles
- **Colaboración**: Construimos juntos, no competimos
- **Calidad**: Preferimos calidad sobre cantidad

### Comportamiento Inaceptable

- Acoso o discriminación
- Trolling o comentarios despectivos
- Spam o publicidad no solicitada
- Violación de privacidad de otros

---

## 📚 Recursos

- [PEP 8 - Guía de Estilo Python](https://pep8.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Discord.py Docs](https://discordpy.readthedocs.io/)

---

¡Gracias por contribuir a VoiceToVision! 🎙️✨
