# 📁 Estructura del Proyecto VoiceToVision

## Resumen de Archivos

### Total: 18 archivos creados

---

## 🚀 Archivos de Inicio

| Archivo | Descripción | Líneas |
|---------|-------------|--------|
| `start.py` | Script de inicio rápido con verificaciones | 280 |
| `setup.py` | Configuración interactiva inicial | 450 |
| `bot.py` | Bot de Discord completo (entry point) | 750 |

---

## ⚙️ Módulos Core (Procesamiento)

| Archivo | Descripción | Funciones Principales |
|---------|-------------|----------------------|
| `logger.py` | Sistema de logs centralizado | SystemLogger, get_logger |
| `database.py` | Base de datos SQLite async | IdeasDatabase, get_database |
| `security.py` | Autenticación y seguridad | SecurityManager, sanitización Windows |
| `audio_processor.py` | Procesamiento de audio | AudioProcessor, FFmpeg |
| `whisper_module.py` | Transcripción con Whisper | WhisperTranscriber |
| `ollama_module.py` | Análisis con Ollama | OllamaAnalyzer |

---

## 📦 Módulos de Gestión

| Archivo | Descripción | Funciones Principales |
|---------|-------------|----------------------|
| `idea_manager.py` | Gestión de carpetas de ideas | IdeaManager, CRUD |
| `search_engine.py` | Motor de búsqueda | SearchEngine, scoring |
| `zip_manager.py` | Descargas ZIP temporales | ZipManager, tokens seguros |

---

## 📋 Configuración y Documentación

| Archivo | Descripción | Propósito |
|---------|-------------|-----------|
| `requirements.txt` | Dependencias Python | pip install -r requirements.txt |
| `.env.example` | Plantilla de variables de entorno | Copiar a .env y configurar |
| `config.json.example` | Plantilla de configuración | Copiar a config.json y ajustar |
| `.gitignore` | Archivos ignorados por git | Evitar subir datos sensibles |
| `LICENSE` | Licencia MIT | Uso libre del código |
| `README.md` | Documentación principal | Guía completa de uso |
| `CONTRIBUTING.md` | Guía de contribución | Cómo contribuir al proyecto |
| `CHANGELOG.md` | Historial de cambios | Versionado y cambios |
| `TODO.md` | Plan de desarrollo | Seguimiento de tareas |
| `PROJECT_STRUCTURE.md` | Este archivo | Estructura del proyecto |

---

## 🗺️ Mapa de Dependencias

```
start.py
    ├── Verifica: FFmpeg, Ollama, Python, Config
    └── Ejecuta: bot.py

setup.py
    ├── Genera: .env, config.json
    ├── Crea: directorios (ideas/, temp/, logs/, data/)
    └── Instala: dependencias

bot.py (Entry Point)
    ├── logger.py (logging global)
    ├── database.py (SQLite)
    ├── security.py (auth)
    ├── audio_processor.py (FFmpeg)
    ├── whisper_module.py (transcripción)
    ├── ollama_module.py (análisis IA)
    ├── idea_manager.py (gestión carpetas)
    ├── search_engine.py (búsqueda)
    └── zip_manager.py (descargas)
```

---

## 📊 Estadísticas del Código

### Por Tipo de Archivo

| Extensión | Cantidad | Líneas Totales Aprox. |
|-----------|----------|----------------------|
| `.py` | 13 | ~4,500 |
| `.md` | 5 | ~2,000 |
| `.txt` | 1 | 20 |
| `.json` | 1 (example) | 100 |
| Sin extensión | 2 | 50 |

### Por Categoría

| Categoría | Archivos | Descripción |
|-----------|----------|-------------|
| **Core** | 6 | Módulos esenciales del sistema |
| **Bot** | 1 | Interfaz Discord |
| **Config** | 4 | Setup, ejemplos, requirements |
| **Docs** | 5 | README, guías, changelog |
| **Utils** | 2 | Start, estructura |

---

## 🎯 Funcionalidades por Módulo

### 🔐 Seguridad (`security.py`)
- ✅ Autenticación por lista blanca
- ✅ Roles (admin/usuario)
- ✅ Sanitización Windows estricta
- ✅ Protección path traversal
- ✅ Validación de archivos
- ✅ Generación de tokens seguros

### 📝 Logging (`logger.py`)
- ✅ Logs de sistema con rotación
- ✅ Logs de seguridad separados
- ✅ Auditoría de operaciones
- ✅ Niveles: DEBUG, INFO, WARNING, ERROR, CRITICAL

### 💾 Base de Datos (`database.py`)
- ✅ SQLite async con aiosqlite
- ✅ Indexación de ideas
- ✅ Búsqueda con filtros
- ✅ Versionado automático
- ✅ Estadísticas del sistema

### 🎙️ Audio (`audio_processor.py`)
- ✅ Validación de formatos
- ✅ Conversión FFmpeg
- ✅ Limpieza de muletillas
- ✅ Detección de duración
- ✅ Limpieza de temporales

### 🧠 IA (`whisper_module.py` + `ollama_module.py`)
- ✅ Transcripción Whisper local
- ✅ Detección de idioma
- ✅ Análisis estructurado con Ollama
- ✅ Validación de JSON
- ✅ Prompts estrictos

### 📁 Gestión (`idea_manager.py`)
- ✅ Creación de carpetas
- ✅ UUID único por idea
- ✅ Versionado automático
- ✅ Metadata completa
- ✅ Renombrado (admin)
- ✅ Eliminación (admin)

### 🔍 Búsqueda (`search_engine.py`)
- ✅ Búsqueda por nombre
- ✅ Scoring de relevancia
- ✅ Filtros avanzados
- ✅ Sugerencias de autocompletado
- ✅ Ideas recientes

### 📦 Descargas (`zip_manager.py`)
- ✅ Compresión ZIP
- ✅ Enlaces temporales
- ✅ Tokens seguros
- ✅ Expiración configurable
- ✅ Limpieza automática

### 🤖 Bot (`bot.py`)
- ✅ Comandos slash
- ✅ Cola de procesamiento async
- ✅ Botones interactivos
- ✅ Embeds informativos
- ✅ Sistema de ayuda

---

## 🚀 Flujo de Datos

```
Usuario envía audio (Discord)
    ↓
bot.py recibe y valida
    ↓
audio_processor.py valida y convierte
    ↓
whisper_module.py transcribe
    ↓
ollama_module.py analiza
    ↓
idea_manager.py crea carpeta y archivos
    ↓
database.py indexa la idea
    ↓
bot.py envía confirmación con botones
    ↓
Usuario puede: buscar, descargar, renombrar
```

---

## 📁 Estructura de Carpetas Generada

```
VoiceToVision/
├── .venv/                    # Entorno virtual (creado por setup)
├── .env                      # Variables de entorno (sensible)
├── config.json               # Configuración del sistema
│
├── ideas/                    # Carpetas de ideas generadas
│   ├── App_Delivery_v1/
│   │   ├── audio_original.mp3
│   │   ├── transcripcion.txt
│   │   ├── analisis.json
│   │   ├── resumen.txt
│   │   └── metadata.json
│   └── Negocio_SaaS_v1/
│       └── ...
│
├── temp/                     # Archivos temporales
│   ├── downloads/           # ZIPs temporales
│   └── whisper_ready_*.wav  # Audios convertidos
│
├── logs/                     # Logs del sistema
│   ├── system.log
│   └── security.log
│
└── data/                     # Base de datos
    └── ideas.db              # SQLite
```

---

## 🔧 Configuración Clave

### Variables de Entorno (`.env`)
```env
DISCORD_TOKEN=token_aqui
OLLAMA_HOST=http://localhost:11434
SECRET_KEY=clave_secreta
```

### Configuración del Sistema (`config.json`)
```json
{
  "discord": {
    "authorized_users": ["id1", "id2"],
    "admins": ["id1"]
  },
  "system": {
    "max_audio_size_mb": 25,
    "link_expiry_minutes": 30,
    "max_concurrent_jobs": 2
  }
}
```

---

## 📝 Notas de Desarrollo

### Compatibilidad
- ✅ Python 3.8+
- ✅ Windows 10/11 (principal)
- ✅ Linux/Mac (con ajustes menores)

### Dependencias Externas
- FFmpeg (sistema)
- Ollama (sistema)
- Discord Bot Token

### Optimizaciones Implementadas
- Async/await en toda la base de código
- SQLite con índices para búsqueda rápida
- Cola de procesamiento con workers
- Rotación de logs automática
- Limpieza de temporales programada

### Seguridad Implementada
- Sanitización estricta de nombres de archivo
- Validación de rutas contra path traversal
- Tokens criptográficamente seguros
- Separación de logs de seguridad
- Autenticación obligatoria

---

## 🎉 Estado del Proyecto

**Versión**: 1.0.0  
**Estado**: ✅ COMPLETO Y FUNCIONAL  
**Fecha**: 2024-01-15  

### Funcionalidades Completas
- [x] Recepción de audios Discord
- [x] Transcripción con Whisper
- [x] Análisis con Ollama
- [x] Organización en carpetas
- [x] Búsqueda de ideas
- [x] Descargas ZIP
- [x] Sistema de seguridad
- [x] Logs centralizados
- [x] Configuración interactiva
- [x] Documentación completa

### Listo para Usar
1. ✅ Ejecutar `python setup.py`
2. ✅ Configurar `.env` y `config.json`
3. ✅ Iniciar con `python start.py` o `python bot.py`
4. ✅ Enviar audios a Discord

---

**Proyecto creado con ❤️ para organizar ideas de voz de forma inteligente**
