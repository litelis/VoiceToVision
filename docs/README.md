# 🎙️ VoiceToVision

**Sistema de Organización Inteligente de Ideas por Voz**

Transforma tus audios de Discord y WhatsApp en ideas estructuradas, analizadas y organizadas automáticamente usando IA local.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Discord](https://img.shields.io/badge/Discord-Bot-7289DA.svg)](https://discord.com)
[![Ollama](https://img.shields.io/badge/Ollama-Local_AI-green.svg)](https://ollama.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Tabla de Contenidos

- [🎯 Características](#-características)
- [🏗️ Arquitectura](#️-arquitectura)
- [📦 Instalación](#-instalación)
- [⚙️ Configuración](#️-configuración)
- [🚀 Uso](#-uso)
- [🔧 Comandos](#-comandos)
- [🔐 Seguridad](#-seguridad)
- [📁 Estructura](#-estructura)
- [🛠️ Solución de Problemas](#️-solución-de-problemas)
- [🗺️ Roadmap](#️-roadmap)

---

## 🎯 Características

### ✨ Core
- 🎙️ **Transcripción automática** con OpenAI Whisper (local)
- 🧠 **Análisis inteligente** con modelos locales via Ollama
- 📁 **Organización automática** en carpetas estructuradas
- 🔍 **Búsqueda rápida** con SQLite y coincidencia parcial
- 📦 **Descargas ZIP** con enlaces temporales seguros
- 🔄 **Versionado automático** de ideas duplicadas

### 🤖 Integraciones
- 💬 **Discord Bot** completo con comandos slash
- 📱 **WhatsApp** (preparado para futura implementación)
- 🖥️ **Windows nativo** con sanitización estricta de rutas

### 🔐 Seguridad
- ✅ **Autenticación** por lista blanca de usuarios
- 👑 **Roles** (admin/usuario) con permisos diferenciados
- 🛡️ **Protección** contra path traversal
- 🔒 **Sanitización** de nombres de archivo Windows-compliant
- 📝 **Logs** de seguridad y auditoría

### ⚡ Rendimiento
- 🔄 **Cola de procesamiento** async con límite de concurrencia
- 💾 **Base de datos** SQLite para indexación rápida
- 🧹 **Limpieza automática** de archivos temporales
- 📊 **Estadísticas** del sistema en tiempo real

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    VoiceToVision                             │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Discord   │  │  WhatsApp   │  │   Comandos CLI    │  │
│  │    Bot      │  │  (Futuro)   │  │                     │  │
│  └──────┬──────┘  └──────┬──────┘  └─────────────────────┘  │
│         │                │                                   │
│         └────────────────┼─────────────────┐                │
│                          ▼                 │                │
│                   ┌─────────────┐          │                │
│                   │  Seguridad  │          │                │
│                   │   (ACL)     │          │                │
│                   └──────┬──────┘          │                │
│                          │                 │                │
│         ┌────────────────┼─────────────────┘                │
│         ▼                ▼                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Cola de   │  │  Procesador │  │    Base de Datos   │  │
│  │  Trabajos   │──│   de Audio  │──│     (SQLite)       │  │
│  │   (Async)   │  │             │  │                     │  │
│  └─────────────┘  └──────┬──────┘  └─────────────────────┘  │
│                          │                                   │
│         ┌────────────────┼─────────────────┐                │
│         ▼                ▼                 ▼                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Whisper   │  │   Ollama    │  │   Gestor    │        │
│  │Transcripción│  │   Análisis  │  │   de Ideas  │        │
│  │   (Local)   │  │   (Local)   │  │             │        │
│  └─────────────┘  └─────────────┘  └──────┬──────┘        │
│                                            │                │
│                              ┌─────────────┼─────────────┐  │
│                              ▼             ▼             ▼  │
│                       ┌──────────┐  ┌──────────┐  ┌──────┐ │
│                       │  Audio   │  │   JSON   │  │  ZIP │ │
│                       │ Original │  │ Análisis │  │ Temp │ │
│                       └──────────┘  └──────────┘  └──────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Instalación

### Requisitos Previos

- **Python 3.8+**
- **FFmpeg** (instalado y en PATH)
- **Ollama** (instalado y ejecutándose)
- **Git** (opcional, para clonar)

### 1. Clonar o Descargar

```bash
git clone https://github.com/litee/VoiceToVision.git
cd VoiceToVision

```

O descarga y extrae el ZIP.

### 2. Ejecutar Setup Interactivo

```bash
python scripts/setup.py
```


El setup te guiará por:
- ✅ Creación de entorno virtual (opcional)
- ✅ Instalación de dependencias
- ✅ Configuración de tokens Discord
- ✅ Lista de usuarios autorizados y admins
- ✅ Configuración de carpetas y límites
- ✅ Generación de `.env` y `config.json`

### 3. Instalar Ollama y Modelo

```bash
# Descarga Ollama desde https://ollama.com
# Luego instala el modelo:
ollama pull llama3.2
```

### 4. Verificar FFmpeg

```bash
ffmpeg -version
```

Si no está instalado:
- **Windows**: Descarga desde [ffmpeg.org](https://ffmpeg.org/download.html) y añade a PATH
- **Chocolatey**: `choco install ffmpeg`
- **Scoop**: `scoop install ffmpeg`

---

## ⚙️ Configuración

### Archivos Generados

#### `.env`
```env
DISCORD_TOKEN=tu_token_aqui
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2
SECRET_KEY=clave_secreta_generada
```

#### `config.json`
```json
{
  "discord": {
    "authorized_users": ["123456789", "987654321"],
    "admins": ["123456789"],
    "command_prefix": "/"
  },
  "system": {
    "base_folder": "./ideas",
    "max_audio_size_mb": 25,
    "link_expiry_minutes": 30,
    "max_concurrent_jobs": 2
  },
  "ollama": {
    "model": "llama3.2",
    "temperature": 0.7
  },
  "whisper": {
    "model": "base",
    "remove_filler_words": true
  }
}
```

### Variables Importantes

| Variable | Descripción | Default |
|----------|-------------|---------|
| `max_audio_size_mb` | Tamaño máximo de audio | 25 MB |
| `link_expiry_minutes` | Expiración de enlaces ZIP | 30 min |
| `max_concurrent_jobs` | Procesos simultáneos | 2 |
| `max_filename_length` | Longitud máxima nombre | 50 chars |
| `auto_delete_enabled` | Eliminación automática | false |

---

## 🚀 Uso

### Iniciar el Bot

```bash
# Con entorno virtual activado:
python src/bot/bot.py
```


Verás:
```
🚀 Iniciando VoiceToVision Bot...
✅ Bot conectado como VoiceToVision#1234
✅ Ollama conectado: llama3.2
```

### Enviar un Audio

1. **Adjunta** un archivo de audio (.mp3, .wav, .ogg, .m4a) en Discord
2. El bot **valida** el archivo automáticamente
3. Se **encola** para procesamiento
4. Recibirás notificación cuando termine

### Flujo de Procesamiento

```
🎙️ Audio recibido → ⏳ En cola → 🔄 Transcribiendo → 
🧠 Analizando → 📁 Creando carpeta → ✅ ¡Listo!
```

---

## 🔧 Comandos

### `/search <query>`
Busca ideas por nombre o contenido.

```
/search app delivery
```

**Resultado**: Lista de ideas coincidentes con scores de relevancia.

### `/rename <actual> <nuevo>` (Admin)
Renombra una idea existente.

```
/rename AppDelivery App_Delivery_Local
```

### `/stats`
Muestra estadísticas del sistema.

```
📊 Estadísticas:
💡 Ideas: 45 total, 3 recientes
📦 Descargas: 2 activas, 15.5 MB
⚙️ Sistema: 0 pendientes, 1 procesando
```

### `/help`
Muestra ayuda completa.

---

## 🔐 Seguridad

### Autenticación

- **Lista blanca**: Solo usuarios en `authorized_users` pueden usar el bot
- **Roles**:
  - `usuario`: Crear ideas, buscar, descargar
  - `admin`: Todo lo anterior + renombrar, eliminar, configurar

### Sanitización Windows

Nombres de carpetas procesados para eliminar:
- ❌ Caracteres inválidos: `< > : " / \\ | ? *`
- ❌ Tildes y diacríticos
- ❌ Nombres reservados: `CON`, `PRN`, `AUX`, `NUL`, etc.
- ❌ Espacios (convertidos a `_`)
- ❌ Longitud > 50 caracteres

### Protección Path Traversal

Todas las rutas validadas contra:
```python
if not path.resolve().startswith(base_folder.resolve()):
    raise SecurityError("Path traversal detectado")
```

---

## 📁 Estructura de Ideas

Cada idea crea una carpeta estructurada:

```
/ideas/
└── App_Delivery_Local/
    ├── audio_original.mp3      # Audio original
    ├── transcripcion.txt       # Texto transcrito
    ├── analisis.json           # Análisis completo de Ollama
    ├── resumen.txt             # Resumen legible
    └── metadata.json           # Metadatos del sistema
```

### `analisis.json`
```json
{
  "nombre_idea": "App Delivery Local",
  "resumen": "Aplicación móvil para conectar comercios locales...",
  "explicacion": "El proyecto consiste en...",
  "tipo": "App",
  "tags": ["delivery", "local", "mobile"],
  "nivel_madurez": "concepto",
  "viabilidad": 8,
  "siguientes_pasos": [
    "Investigar competencia",
    "Validar con comercios",
    "Crear MVP"
  ],
  "riesgos": [
    "Competencia establecida",
    "Adopción lenta"
  ]
}
```

### `metadata.json`
```json
{
  "sistema": {
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "fecha_creacion": "2026-01-15T10:30:00",
    "creado_por": "123456789",
    "version": 1,
    "nombre_carpeta": "App_Delivery_Local"
  },

  "analisis": { ... },
  "estadisticas": {
    "longitud_transcripcion": 1250,
    "numero_archivos": 5
  }
}
```

---

## 🛠️ Solución de Problemas

### Error: "Ollama no disponible"

```bash
# Verificar que Ollama está ejecutándose
curl http://localhost:11434/api/tags

# Si no responde, iniciar Ollama:
ollama serve
```

### Error: "FFmpeg no encontrado"

```bash
# Verificar instalación
ffmpeg -version

# Si no está en PATH, especificar en config.json:
"ffmpeg_path": "C:/ffmpeg/bin/ffmpeg.exe"
```

### Error: "Modelo no disponible"

```bash
# Listar modelos disponibles
ollama list

# Descargar modelo requerido
ollama pull llama3.2
```

### Error: "Discord Token inválido"

- Verificar que el token en `.env` es correcto
- Asegurar que el bot tiene permisos `message_content` en el portal de Discord

### Procesamiento lento

- Reduce `max_concurrent_jobs` a 1 en `config.json`
- Usa un modelo Whisper más ligero: `"model": "tiny"`
- Verifica uso de GPU: `python -c "import torch; print(torch.cuda.is_available())"`

---

## 🗺️ Roadmap

### ✅ Implementado
- [x] Bot Discord completo
- [x] Transcripción Whisper local
- [x] Análisis Ollama local
- [x] Sistema de carpetas estructurado
- [x] Búsqueda con SQLite
- [x] Descargas ZIP temporales
- [x] Seguridad y autenticación
- [x] Cola de procesamiento async
- [x] Logs centralizados

### 🚧 En Desarrollo
- [ ] Comando `/update` para añadir audios a ideas existentes
- [ ] Dashboard web de administración
- [ ] Exportación a CSV
- [ ] Sistema de puntuación de potencial

### 📅 Futuro
- [ ] Integración WhatsApp completa
- [ ] Base de datos PostgreSQL opcional
- [ ] API REST para integraciones
- [ ] Sistema de plugins
- [ ] Análisis de sentimiento
- [ ] Modo "inversor crítico"

---

## 🤝 Contribuir

1. Fork el repositorio
2. Crea una rama: `git checkout -b feature/nueva-funcionalidad`
3. Commit tus cambios: `git commit -am 'Añade nueva funcionalidad'`
4. Push a la rama: `git push origin feature/nueva-funcionalidad`
5. Abre un Pull Request

### Guías de Código

- Seguir PEP 8
- Documentar funciones con docstrings
- Añadir logs para operaciones importantes
- Mantener compatibilidad Windows
- Incluir tests para nuevas funcionalidades

---

## 📄 Licencia

MIT License - ver [LICENSE](LICENSE) para detalles.

---

## 🙏 Agradecimientos

- [OpenAI Whisper](https://github.com/openai/whisper) - Transcripción de audio
- [Ollama](https://ollama.com) - Ejecución de modelos locales
- [Discord.py](https://discordpy.readthedocs.io/) - Framework del bot
- [FFmpeg](https://ffmpeg.org/) - Procesamiento de audio

---

## 📞 Soporte

- **Issues**: [GitHub Issues](https://github.com/litee/VoiceToVision/issues)
- **Discord**: [Servidor de Soporte](https://discord.gg/voicetovision)
- **Email**: soporte@voicetovision.dev


---

<p align="center">
  <strong>🎙️ Convierte tu voz en visión. Organiza tus ideas automáticamente.</strong>
</p>
