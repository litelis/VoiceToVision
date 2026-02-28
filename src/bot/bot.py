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
VoiceToVision - Bot de Discord
Bot completo con cola de procesamiento, comandos y botones interactivos.
"""


import os
import sys
import json
import asyncio
import discord
from discord.ext import commands
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
import tempfile

# Add project root to Python path to allow imports from src module
# when running the bot from any directory
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Importar módulos del sistema
from src.core.logger import init_logger, get_logger
from src.core.database import get_database, close_database
from src.core.security import init_security, get_security
from src.processing.audio_processor import AudioProcessor
from src.processing.whisper_module import WhisperTranscriber
from src.processing.ollama_module import OllamaAnalyzer
from src.managers.idea_manager import IdeaManager
from src.managers.search_engine import SearchEngine
from src.managers.zip_manager import ZipManager


# Configuración global
CONFIG = None
LOGGER = None
SECURITY = None
DATABASE = None

# Componentes del sistema
AUDIO_PROCESSOR = None
WHISPER = None
OLLAMA = None
IDEA_MANAGER = None
SEARCH_ENGINE = None
ZIP_MANAGER = None

# Cola de procesamiento de audios
processing_queue = asyncio.Queue()
active_jobs = 0
max_concurrent_jobs = 2


class VoiceToVisionBot(commands.Bot):
    """
    Bot de Discord para VoiceToVision.
    Gestiona recepción de audios, comandos y botones interactivos.
    """
    
    def __init__(self):
        # Configurar intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        
        super().__init__(
            command_prefix=commands.when_mentioned_or("/"),
            intents=intents,
            help_command=None
        )
        
        # Cargar configuración
        self._load_config()
        
        # Inicializar sistema
        self._init_system()
    
    def _load_config(self):
        """Carga configuración desde archivos."""
        global CONFIG
        
        # Cargar config.json
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                CONFIG = json.load(f)
        except Exception as e:
            print(f"❌ Error cargando config.json: {e}")
            sys.exit(1)
        
        # Cargar .env si existe
        try:
            from dotenv import load_dotenv
            # Cargar desde la raíz del proyecto donde está el .env
            project_root = Path(__file__).resolve().parent.parent
            env_path = project_root / ".env"
            load_dotenv(dotenv_path=env_path)
        except ImportError:
            pass
    
    def _init_system(self):
        """Inicializa todos los componentes del sistema."""
        global LOGGER, SECURITY, DATABASE
        global AUDIO_PROCESSOR, WHISPER, OLLAMA
        global IDEA_MANAGER, SEARCH_ENGINE, ZIP_MANAGER
        
        # Inicializar logger
        LOGGER = init_logger(CONFIG)
        LOGGER.info("=" * 60)
        LOGGER.info("VoiceToVision Bot Iniciando")
        LOGGER.info("=" * 60)
        
        # Inicializar seguridad
        SECURITY = init_security(CONFIG)
        LOGGER.info("Sistema de seguridad inicializado")
        
        # Inicializar base de datos (async, se conectará después)
        # DATABASE se inicializa en on_ready
        
        # Inicializar procesadores
        AUDIO_PROCESSOR = AudioProcessor(CONFIG, SECURITY, LOGGER)
        WHISPER = WhisperTranscriber(CONFIG, LOGGER)
        OLLAMA = OllamaAnalyzer(CONFIG, LOGGER)
        
        LOGGER.info("Procesadores de audio y análisis inicializados")
    
    async def setup_hook(self):
        """Hook de inicialización asíncrona."""
        global DATABASE, IDEA_MANAGER, SEARCH_ENGINE, ZIP_MANAGER
        
        # Conectar base de datos
        DATABASE = await get_database(
            CONFIG["system"].get("database_path", "./data/ideas.db")
        )
        LOGGER.info("Base de datos conectada")
        
        # Inicializar gestores que dependen de la base de datos
        IDEA_MANAGER = IdeaManager(CONFIG, SECURITY, DATABASE, LOGGER)
        SEARCH_ENGINE = SearchEngine(DATABASE, SECURITY, LOGGER)
        ZIP_MANAGER = ZipManager(CONFIG, SECURITY, LOGGER)
        
        LOGGER.info("Gestores de ideas, búsqueda y ZIP inicializados")
        
        # Iniciar worker de la cola
        for i in range(CONFIG["system"].get("max_concurrent_jobs", 2)):
            self.loop.create_task(self._queue_worker())
            LOGGER.info(f"Worker de cola {i+1} iniciado")
        
        # Sincronizar comandos
        try:
            synced = await self.tree.sync()
            LOGGER.info(f"Comandos sincronizados: {len(synced)} comandos")
        except Exception as e:
            LOGGER.error(f"Error sincronizando comandos: {e}")
    
    async def on_ready(self):
        """Evento cuando el bot está listo."""
        LOGGER.info(f"✅ Bot conectado como {self.user} (ID: {self.user.id})")
        LOGGER.info(f"   Servidores: {len(self.guilds)}")
        
        # Verificar Ollama
        ollama_status = await OLLAMA.check_connection()
        if ollama_status["available"]:
            LOGGER.info(f"✅ Ollama conectado: {ollama_status.get('required_model', 'unknown')}")
        else:
            LOGGER.warning(f"⚠️ Ollama no disponible: {ollama_status.get('error', 'unknown error')}")
    
    async def on_message(self, message: discord.Message):
        """Procesa mensajes recibidos."""
        # Ignorar mensajes del bot
        if message.author == self.user:
            return
        
        # Verificar autorización
        auth = SECURITY.authenticate_user(str(message.author.id), "discord")
        
        if not auth["authenticated"]:
            # No responder a no autorizados (silencioso por seguridad)
            return
        
        # Procesar adjuntos de audio
        if message.attachments:
            for attachment in message.attachments:
                if self._is_audio_file(attachment.filename):
                    await self._handle_audio_attachment(message, attachment, auth)
                    return  # Procesar solo el primer audio
        
        # Procesar comandos de texto
        await self.process_commands(message)
    
    def _is_audio_file(self, filename: str) -> bool:
        """Verifica si un archivo es de audio soportado."""
        ext = Path(filename).suffix.lower()
        supported = CONFIG["system"].get("supported_formats", [".mp3", ".wav", ".ogg", ".m4a"])
        return ext in supported
    
    async def _handle_audio_attachment(self, 
                                        message: discord.Message, 
                                        attachment: discord.Attachment,
                                        auth: Dict):
        """Maneja un archivo de audio adjunto."""
        user_id = str(message.author.id)
        
        LOGGER.info(f"Audio recibido de {message.author.name}: {attachment.filename}")
        
        # Verificar tamaño
        size_mb = attachment.size / (1024 * 1024)
        max_size = CONFIG["system"].get("max_audio_size_mb", 25)
        
        if size_mb > max_size:
            await message.reply(
                f"❌ El archivo es demasiado grande ({size_mb:.1f}MB). "
                f"Límite: {max_size}MB",
                delete_after=30
            )
            return
        
        # Descargar archivo temporalmente
        temp_dir = Path(CONFIG["system"].get("temp_folder", "./temp"))
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        temp_path = temp_dir / f"{user_id}_{attachment.filename}"
        
        try:
            await attachment.save(temp_path)
            LOGGER.info(f"Audio guardado temporalmente: {temp_path}")
            
            # Añadir a la cola de procesamiento
            await processing_queue.put({
                "user_id": user_id,
                "username": message.author.name,
                "message": message,
                "file_path": temp_path,
                "original_filename": attachment.filename
            })
            
            # Notificar al usuario
            position = processing_queue.qsize()
            if position > 1:
                await message.reply(
                    f"🎙️ Audio recibido y en cola (posición {position}). "
                    f"Te notificaré cuando comience el procesamiento...",
                    delete_after=60
                )
            else:
                await message.reply(
                    "🎙️ Audio recibido. Procesando...",
                    delete_after=30
                )
            
        except Exception as e:
            LOGGER.error(f"Error descargando audio: {e}")
            await message.reply(
                "❌ Error al recibir el audio. Intenta de nuevo.",
                delete_after=30
            )
    
    async def _queue_worker(self):
        """Worker que procesa audios de la cola."""
        global active_jobs
        
        while True:
            try:
                # Obtener trabajo de la cola
                job = await processing_queue.get()
                active_jobs += 1
                
                try:
                    await self._process_audio_job(job)
                except Exception as e:
                    LOGGER.error(f"Error procesando trabajo: {e}")
                    try:
                        await job["message"].reply(
                            "❌ Error procesando el audio. Revisa los logs.",
                            delete_after=30
                        )
                    except:
                        pass
                
                finally:
                    active_jobs -= 1
                    processing_queue.task_done()
                    
            except Exception as e:
                LOGGER.error(f"Error en worker: {e}")
                await asyncio.sleep(1)
    
    async def _process_audio_job(self, job: Dict):
        """Procesa un trabajo de audio completo."""
        user_id = job["user_id"]
        message = job["message"]
        file_path = job["file_path"]
        
        LOGGER.info(f"Procesando audio para {job['username']}")
        
        try:
            # 1. Validar audio
            await message.channel.trigger_typing()
            validation = await AUDIO_PROCESSOR.validate_audio(file_path, user_id)
            
            if not validation["valid"]:
                await message.reply(
                    f"❌ {validation.get('error', 'Audio inválido')}",
                    delete_after=30
                )
                return
            
            # 2. Convertir para Whisper
            await message.channel.trigger_typing()
            conversion = await AUDIO_PROCESSOR.convert_for_whisper(file_path)
            
            if not conversion["success"]:
                await message.reply(
                    f"❌ Error convirtiendo audio: {conversion.get('error')}",
                    delete_after=30
                )
                return
            
            # 3. Transcribir
            await message.channel.trigger_typing()
            transcription_result = await WHISPER.transcribe(
                Path(conversion["output_path"])
            )
            
            if not transcription_result["success"]:
                await message.reply(
                    f"❌ Error en transcripción: {transcription_result.get('error')}",
                    delete_after=30
                )
                return
            
            transcription_text = transcription_result["text"]
            language = transcription_result.get("language", "unknown")
            
            # Limpiar transcripción
            cleaned_text = await AUDIO_PROCESSOR.clean_transcription(transcription_text)
            
            # 4. Analizar con Ollama
            await message.channel.trigger_typing()
            analysis_result = await OLLAMA.analyze_idea(cleaned_text, language)
            
            if not analysis_result["success"]:
                await message.reply(
                    f"❌ Error en análisis: {analysis_result.get('error')}",
                    delete_after=30
                )
                # Guardar transcripción aunque falle el análisis
                return
            
            analysis_data = analysis_result["data"]
            idea_name = analysis_data.get("nombre_idea", "unnamed_idea")
            
            # 5. Crear idea en el sistema
            await message.channel.trigger_typing()
            
            # Preparar info del audio
            audio_info = {
                "success": True,
                "file_path": str(file_path),
                "original_name": job["original_filename"],
                "duration": validation.get("duration", 0),
                "size_mb": validation.get("size_mb", 0)
            }
            
            creation_result = await IDEA_MANAGER.create_idea(
                nombre_idea=idea_name,
                analysis_data=analysis_data,
                audio_info=audio_info,
                transcription=cleaned_text,
                user_id=user_id
            )
            
            if not creation_result["success"]:
                await message.reply(
                    f"⚠️ Error guardando idea: {creation_result.get('error')}",
                    delete_after=30
                )
                return
            
            # 6. Enviar resumen al usuario
            await self._send_success_message(
                message, 
                creation_result,
                analysis_data,
                validation.get("duration", 0)
            )
            
            LOGGER.info(
                f"Idea creada exitosamente: {creation_result['nombre_carpeta']} "
                f"por usuario {user_id}"
            )
            
        except Exception as e:
            LOGGER.error(f"Error en procesamiento: {e}")
            raise
        finally:
            # Limpiar archivos temporales
            try:
                if file_path.exists():
                    file_path.unlink()
                # Limpiar archivo convertido si existe
                temp_dir = Path(CONFIG["system"].get("temp_folder", "./temp"))
                for temp_file in temp_dir.glob(f"whisper_ready_{user_id}_*"):
                    temp_file.unlink(missing_ok=True)
            except Exception as e:
                LOGGER.warning(f"Error limpiando temporales: {e}")
    
    async def _send_success_message(self,
                                     message: discord.Message,
                                     creation_result: Dict,
                                     analysis: Dict,
                                     duration: float):
        """Envía mensaje de éxito con botones interactivos."""
        
        # Crear embed
        embed = discord.Embed(
            title=f"✅ Idea Guardada: {analysis.get('nombre_idea', 'Unnamed')}",
            description=analysis.get('resumen', 'Sin resumen')[:500],
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📁 Carpeta",
            value=f"`{creation_result['nombre_carpeta']}`",
            inline=True
        )
        embed.add_field(
            name="🏷️ Tipo",
            value=analysis.get('tipo', 'Otro'),
            inline=True
        )
        embed.add_field(
            name="⭐ Viabilidad",
            value=f"{analysis.get('viabilidad', 0)}/10",
            inline=True
        )
        
        embed.add_field(
            name="🎯 Madurez",
            value=analysis.get('nivel_madurez', 'concepto'),
            inline=True
        )
        embed.add_field(
            name="⏱️ Duración Audio",
            value=f"{duration:.1f}s",
            inline=True
        )
        embed.add_field(
            name="📄 Archivos",
            value=str(creation_result['files_created']),
            inline=True
        )
        
        # Tags
        tags = analysis.get('tags', [])
        if tags:
            embed.add_field(
                name="🏷️ Tags",
                value=", ".join(tags[:5]),
                inline=False
            )
        
        # Crear vista con botones
        view = IdeaActionView(
            creation_result['nombre_carpeta'],
            creation_result['uuid'],
            message.author.id
        )
        
        await message.reply(embed=embed, view=view)
    
    async def close(self):
        """Cierra el bot limpiamente."""
        LOGGER.info("Cerrando bot...")
        
        # Cerrar base de datos
        await close_database()
        
        # Limpiar temporales
        try:
            await ZIP_MANAGER.cleanup_expired_links()
        except:
            pass
        
        LOGGER.info("Bot cerrado correctamente")
        await super().close()


class IdeaActionView(discord.ui.View):
    """
    Vista con botones de acción para una idea.
    """
    
    def __init__(self, idea_name: str, idea_uuid: str, user_id: int):
        super().__init__(timeout=300)  # 5 minutos
        self.idea_name = idea_name
        self.idea_uuid = idea_uuid
        self.user_id = user_id
    
    @discord.ui.button(label="📄 Ver Resumen", style=discord.ButtonStyle.primary)
    async def view_summary(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Muestra el resumen completo."""
        if not await self._check_auth(interaction):
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Obtener info de la idea
        info = await IDEA_MANAGER.get_idea_info(self.idea_name)
        
        if not info:
            await interaction.followup.send("❌ Idea no encontrada", ephemeral=True)
            return
        
        analysis = info.get("metadata", {}).get("analisis", {})
        resumen = analysis.get("explicacion", "No disponible")
        
        # Dividir si es muy largo
        chunks = [resumen[i:i+1900] for i in range(0, len(resumen), 1900)]
        
        for i, chunk in enumerate(chunks):
            title = "📄 Explicación Completa" if i == 0 else "(continuación)"
            await interaction.followup.send(
                f"**{title}**\\n\\n{chunk}",
                ephemeral=True
            )
    
    @discord.ui.button(label="🧠 Ver Análisis", style=discord.ButtonStyle.secondary)
    async def view_analysis(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Muestra el análisis JSON completo."""
        if not await self._check_auth(interaction):
            return
        
        await interaction.response.defer(ephemeral=True)
        
        info = await IDEA_MANAGER.get_idea_info(self.idea_name)
        
        if not info:
            await interaction.followup.send("❌ Idea no encontrada", ephemeral=True)
            return
        
        analysis = info.get("metadata", {}).get("analisis", {})
        
        # Formatear análisis
        embed = discord.Embed(
            title=f"🧠 Análisis: {analysis.get('nombre_idea', 'Unnamed')}",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📋 Resumen",
            value=analysis.get('resumen', 'N/A')[:1000],
            inline=False
        )
        
        embed.add_field(
            name="🎯 Siguientes Pasos",
            value="\\n".join(f"• {paso}" for paso in analysis.get('siguientes_pasos', []))[:1000] or "N/A",
            inline=False
        )
        
        embed.add_field(
            name="⚠️ Riesgos",
            value="\\n".join(f"• {riesgo}" for riesgo in analysis.get('riesgos', []))[:1000] or "N/A",
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="📥 Descargar", style=discord.ButtonStyle.success)
    async def download(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Inicia proceso de descarga."""
        if not await self._check_auth(interaction):
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Crear paquete ZIP
        result = await ZIP_MANAGER.create_download_package(
            self.idea_name,
            str(self.user_id)
        )
        
        if not result["success"]:
            await interaction.followup.send(
                f"❌ Error: {result.get('error')}",
                ephemeral=True
            )
            return
        
        # Crear mensaje con enlace (simulado, en producción sería URL real)
        expiry = result["expires_in_minutes"]
        
        await interaction.followup.send(
            f"📦 **Paquete de descarga creado**\\n\\n"
            f"📁 Archivos: {result['file_count']}\\n"
            f"💾 Tamaño: {result['size_mb']} MB\\n"
            f"⏱️ Expira en: {expiry} minutos\\n\\n"
            f"🔑 Token: `{result['token'][:16]}...`\\n\\n"
            f"Usa el comando `/download {result['token']}` para obtener el archivo.",
            ephemeral=True
        )
    
    async def _check_auth(self, interaction: discord.Interaction) -> bool:
        """Verifica autorización."""
        auth = SECURITY.authenticate_user(str(interaction.user.id), "discord")
        
        if not auth["authenticated"]:
            await interaction.response.send_message(
                "❌ No autorizado",
                ephemeral=True
            )
            return False
        
        return True


# Comandos del bot
@commands.hybrid_command(name="search", description="Busca ideas por nombre")
async def search_command(ctx: commands.Context, query: str):
    """Comando /search para buscar ideas."""
    auth = SECURITY.authenticate_user(str(ctx.author.id), "discord")
    
    if not auth["authenticated"]:
        await ctx.reply("❌ No autorizado", ephemeral=True)
        return
    
    # Realizar búsqueda
    results = await SEARCH_ENGINE.search(
        query=query,
        user_id=str(ctx.author.id),
        limit=10
    )
    
    if not results["success"]:
        await ctx.reply(f"❌ Error: {results.get('error')}", ephemeral=True)
        return
    
    if not results["results"]:
        await ctx.reply(f"🔍 No se encontraron ideas para '{query}'", ephemeral=True)
        return
    
    # Crear embed con resultados
    embed = discord.Embed(
        title=f"🔍 Resultados: '{query}'",
        description=f"Encontradas: {results['total_found']} (mostrando {len(results['results'])})",
        color=discord.Color.blue()
    )
    
    for i, idea in enumerate(results["results"][:5], 1):
        nombre = idea.get("nombre_idea", "Unnamed")
        carpeta = idea.get("nombre_carpeta", "unknown")
        tipo = idea.get("tipo", "Otro")
        viabilidad = idea.get("viabilidad", 0)
        
        resumen_corto = idea.get("resumen", "")[:100]
        if len(idea.get("resumen", "")) > 100:
            resumen_corto += "..."
        
        embed.add_field(
            name=f"{i}. {nombre} ({tipo}) ⭐{viabilidad}/10",
            value=f"📁 `{carpeta}`\\n📝 {resumen_corto or 'Sin resumen'}",
            inline=False
        )
    
    await ctx.reply(embed=embed, ephemeral=True)


@commands.hybrid_command(name="rename", description="Renombra una idea (solo admin)")
async def rename_command(ctx: commands.Context, nombre_actual: str, nuevo_nombre: str):
    """Comando /rename para renombrar ideas."""
    auth = SECURITY.authenticate_user(str(ctx.author.id), "discord")
    
    if not auth["is_admin"]:
        await ctx.reply("❌ Solo administradores pueden renombrar ideas", ephemeral=True)
        return
    
    result = await IDEA_MANAGER.rename_idea(nombre_actual, nuevo_nombre, str(ctx.author.id))
    
    if result["success"]:
        await ctx.reply(
            f"✅ Idea renombrada:\\n"
            f"`{result['nombre_anterior']}` → `{result['nombre_nuevo']}`",
            ephemeral=True
        )
    else:
        await ctx.reply(f"❌ Error: {result.get('error')}", ephemeral=True)


@commands.hybrid_command(name="stats", description="Muestra estadísticas del sistema")
async def stats_command(ctx: commands.Context):
    """Comando /stats para estadísticas."""
    auth = SECURITY.authenticate_user(str(ctx.author.id), "discord")
    
    if not auth["authenticated"]:
        await ctx.reply("❌ No autorizado", ephemeral=True)
        return
    
    # Estadísticas de búsqueda
    search_stats = await SEARCH_ENGINE.get_statistics(str(ctx.author.id))
    
    # Estadísticas de descargas
    zip_stats = await ZIP_MANAGER.get_system_stats()
    
    embed = discord.Embed(
        title="📊 Estadísticas del Sistema",
        color=discord.Color.purple(),
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="💡 Ideas",
        value=f"Total: {search_stats.get('total_ideas', 0)}\\n"
              f"Recientes (7d): {search_stats.get('ideas_recientes', 0)}",
        inline=True
    )
    
    embed.add_field(
        name="📦 Descargas",
        value=f"Activas: {zip_stats['active_links']}\\n"
              f"Total size: {zip_stats['total_size_mb']:.1f} MB",
        inline=True
    )
    
    embed.add_field(
        name="⚙️ Sistema",
        value=f"Cola: {processing_queue.qsize()} pendientes\\n"
              f"Activos: {active_jobs} procesando",
        inline=True
    )
    
    # Por tipo
    por_tipo = search_stats.get('por_tipo', {})
    if por_tipo:
        tipos_str = "\\n".join(f"• {k}: {v}" for k, v in por_tipo.items())
        embed.add_field(name="🏷️ Por Tipo", value=tipos_str, inline=False)
    
    await ctx.reply(embed=embed, ephemeral=True)


@commands.hybrid_command(name="help", description="Muestra ayuda del bot")
async def help_command(ctx: commands.Context):
    """Comando /help."""
    embed = discord.Embed(
        title="🎙️ VoiceToVision - Ayuda",
        description="Sistema de organización inteligente de ideas por voz",
        color=discord.Color.gold()
    )
    
    embed.add_field(
        name="📤 Enviar Audio",
        value="Simplemente adjunta un archivo de audio (.mp3, .wav, .ogg, .m4a)",
        inline=False
    )
    
    embed.add_field(
        name="🔍 /search <query>",
        value="Busca ideas por nombre o contenido",
        inline=False
    )
    
    embed.add_field(
        name="✏️ /rename <actual> <nuevo>",
        value="Renombra una idea (solo administradores)",
        inline=False
    )
    
    embed.add_field(
        name="📊 /stats",
        value="Muestra estadísticas del sistema",
        inline=False
    )
    
    embed.add_field(
        name="❓ /help",
        value="Muestra esta ayuda",
        inline=False
    )
    
    embed.set_footer(text="Procesamiento: Whisper + Ollama | Almacenamiento local seguro")
    
    await ctx.reply(embed=embed, ephemeral=True)


def main():
    """Función principal."""
    # Verificar token
    token = os.getenv("DISCORD_TOKEN")
    
    if not token:
        print("❌ Error: DISCORD_TOKEN no encontrado en variables de entorno")
        print("   Asegúrate de tener un archivo .env con DISCORD_TOKEN=tu_token")
        sys.exit(1)
    
    # Crear bot
    bot = VoiceToVisionBot()
    
    # Añadir comandos
    bot.add_command(search_command)
    bot.add_command(rename_command)
    bot.add_command(stats_command)
    bot.add_command(help_command)
    
    # Ejecutar
    try:
        print("🚀 Iniciando VoiceToVision Bot...")
        bot.run(token)
    except KeyboardInterrupt:
        print("\\n👋 Bot detenido por usuario")
    except Exception as e:
        print(f"\\n❌ Error fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
