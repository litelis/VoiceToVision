#!/usr/bin/env python3
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
VoiceToVision - Setup Interactivo
Configura el entorno completo del sistema de organización de ideas por voz.
"""

import os
import sys
import json
import shutil
import subprocess
import venv
from pathlib import Path


def print_banner():
    """Muestra el banner de bienvenida."""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║           🎙️  VoiceToVision - Setup Interactivo            ║
    ║                                                              ║
    ║   Sistema de Organización Inteligente de Ideas por Voz      ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """)


def ask_yes_no(question, default=True):
    """Pregunta sí/no con valor por defecto."""
    default_str = "Y/n" if default else "y/N"
    while True:
        response = input(f"{question} [{default_str}]: ").strip().lower()
        if not response:
            return default
        if response in ['y', 'yes', 's', 'si', 'sí']:
            return True
        if response in ['n', 'no']:
            return False
        print("Por favor responde 'y' o 'n'")


def ask_input(question, default="", required=True):
    """Pregunta input con valor por defecto."""
    while True:
        if default:
            response = input(f"{question} [{default}]: ").strip()
        else:
            response = input(f"{question}: ").strip()
        
        if not response:
            if default:
                return default
            if not required:
                return ""
            print("Este campo es obligatorio.")
            continue
        return response


def ask_number(question, default, min_val=None, max_val=None):
    """Pregunta por un número."""
    while True:
        response = input(f"{question} [{default}]: ").strip()
        if not response:
            return default
        
        try:
            num = int(response)
            if min_val is not None and num < min_val:
                print(f"El valor mínimo es {min_val}")
                continue
            if max_val is not None and num > max_val:
                print(f"El valor máximo es {max_val}")
                continue
            return num
        except ValueError:
            print("Por favor introduce un número válido.")


def setup_virtual_environment():
    """Configura el entorno virtual."""
    venv_path = Path(".venv")
    
    print("\n📦 Configuración del Entorno Virtual")
    print("-" * 50)
    
    if venv_path.exists():
        print("⚠️  Ya existe un entorno virtual (.venv)")
        choice = ask_input(
            "¿Qué deseas hacer? [usar/borrar/nuevo]",
            default="usar"
        )
        
        if choice == "borrar":
            print("🗑️  Eliminando entorno virtual existente...")
            shutil.rmtree(venv_path)
            print("✅ Entorno virtual eliminado")
            return create_new_venv(venv_path)
        elif choice == "nuevo":
            new_name = ask_input("Nombre del nuevo entorno:", default=".venv-new")
            return create_new_venv(Path(new_name))
        else:
            print("✅ Usando entorno virtual existente")
            return str(venv_path)
    else:
        if ask_yes_no("¿Crear entorno virtual?", default=True):
            return create_new_venv(venv_path)
        else:
            print("⚠️  Continuando sin entorno virtual")
            return None


def create_new_venv(venv_path):
    """Crea un nuevo entorno virtual."""
    print(f"\n🔧 Creando entorno virtual en {venv_path}...")
    try:
        venv.create(venv_path, with_pip=True)
        print("✅ Entorno virtual creado exitosamente")
        
        # Instalar dependencias
        if ask_yes_no("¿Instalar dependencias ahora?", default=True):
            install_dependencies(venv_path)
        
        return str(venv_path)
    except Exception as e:
        print(f"❌ Error creando entorno virtual: {e}")
        return None


def install_dependencies(venv_path):
    """Instala las dependencias del proyecto."""
    print("\n📥 Instalando dependencias...")
    
    # Detectar el ejecutable de Python del venv
    if os.name == 'nt':  # Windows
        python_exe = venv_path / "Scripts" / "python.exe"
        pip_exe = venv_path / "Scripts" / "pip.exe"
    else:
        python_exe = venv_path / "bin" / "python"
        pip_exe = venv_path / "bin" / "pip"
    
    try:
        # Actualizar pip primero
        subprocess.run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"], 
                      check=True, capture_output=True)
        
        # Instalar dependencias
        result = subprocess.run([str(pip_exe), "install", "-r", "requirements.txt"],
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Dependencias instaladas correctamente")
        else:
            print(f"⚠️  Algunas dependencias no se instalaron:\n{result.stderr}")
            
        # Instalar ffmpeg si es posible
        print("\n🔧 Nota: Asegúrate de tener FFmpeg instalado en tu sistema.")
        print("   Descarga desde: https://ffmpeg.org/download.html")
        
    except Exception as e:
        print(f"❌ Error instalando dependencias: {e}")


def configure_discord():
    """Configura el bot de Discord."""
    print("\n🤖 Configuración de Discord")
    print("-" * 50)
    
    token = ask_input("Token del bot de Discord:", required=True)
    
    print("\n👥 Usuarios Autorizados (IDs de Discord)")
    print("   Puedes obtener tu ID activando modo desarrollador en Discord")
    
    authorized_users = []
    admins = []
    
    while True:
        user_id = ask_input("ID de usuario autorizado (o 'listo' para terminar):", 
                          required=False)
        if user_id.lower() in ['listo', 'done', '']:
            break
        
        if user_id.isdigit():
            authorized_users.append(user_id)
            is_admin = ask_yes_no(f"¿Es {user_id} administrador?", default=False)
            if is_admin:
                admins.append(user_id)
            print(f"✅ Usuario {user_id} agregado" + (" (admin)" if is_admin else ""))
        else:
            print("❌ ID inválido, debe ser numérico")
    
    return {
        "token": token,
        "authorized_users": authorized_users,
        "admins": admins
    }


def configure_whatsapp():
    """Configura WhatsApp (placeholder para futura implementación)."""
    print("\n📱 Configuración de WhatsApp (Opcional)")
    print("-" * 50)
    print("ℹ️  La integración con WhatsApp está preparada para futuras versiones")
    
    if ask_yes_no("¿Deseas configurar WhatsApp ahora?", default=False):
        print("⚠️  Por ahora solo se soporta Discord. WhatsApp vendrá en v2.0")
    
    return {
        "enabled": False,
        "token": "",
        "phone_number": ""
    }


def configure_system():
    """Configuración general del sistema."""
    print("\n⚙️  Configuración del Sistema")
    print("-" * 50)
    
    # Carpeta base
    base_folder = ask_input("Carpeta base para almacenar ideas:", 
                          default="./ideas")
    
    # Tamaño máximo de audio
    max_size = ask_number("Tamaño máximo de audio (MB):", 
                         default=25, min_val=1, max_val=100)
    
    # Logs
    enable_logs = ask_yes_no("¿Activar logs del sistema?", default=True)
    
    # Expiración de enlaces
    link_expiry = ask_number("Minutos de expiración para enlaces de descarga:", 
                            default=30, min_val=5, max_val=1440)
    
    # Eliminación automática
    auto_delete = ask_yes_no("¿Activar eliminación automática de ideas antiguas?", 
                            default=False)
    delete_days = 0
    if auto_delete:
        delete_days = ask_number("Días antes de eliminar ideas:", 
                                  default=90, min_val=7)
    
    # Cifrado
    encryption = ask_yes_no("¿Activar cifrado de audios?", default=False)
    
    # Concurrencia
    max_concurrent = ask_number("Máximo de procesos concurrentes:", 
                                 default=2, min_val=1, max_val=5)
    
    return {
        "base_folder": base_folder,
        "max_audio_size_mb": max_size,
        "enable_logs": enable_logs,
        "link_expiry_minutes": link_expiry,
        "auto_delete_enabled": auto_delete,
        "auto_delete_days": delete_days,
        "encryption_enabled": encryption,
        "max_concurrent_jobs": max_concurrent
    }


def create_env_file(config):
    """Crea el archivo .env"""
    print("\n📝 Creando archivo .env...")
    
    discord_config = config["discord"]
    system_config = config["system"]
    
    env_content = f"""# VoiceToVision - Variables de Entorno
# Generado automáticamente por setup.py

# Discord Bot
DISCORD_TOKEN={discord_config['token']}

# Ollama (asume localhost por defecto)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2

# OpenAI (para Whisper - usa API key si no es local)
# OPENAI_API_KEY=your_key_here

# Configuración de seguridad
SECRET_KEY={os.urandom(32).hex()}

# Rutas
BASE_FOLDER={system_config['base_folder']}

# Flags
DEBUG=false
"""
    
    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)
    
    print("✅ Archivo .env creado")


def create_config_json(config):
    """Crea el archivo config.json"""
    print("\n🔧 Creando archivo config.json...")
    
    discord_config = config["discord"]
    system_config = config["system"]
    
    config_data = {
        "discord": {
            "authorized_users": discord_config["authorized_users"],
            "admins": discord_config["admins"],
            "command_prefix": "/",
            "max_message_length": 2000
        },
        "whatsapp": config["whatsapp"],
        "system": {
            "base_folder": system_config["base_folder"],
            "temp_folder": "./temp",
            "logs_folder": "./logs",
            "database_path": "./data/ideas.db",
            "max_audio_size_mb": system_config["max_audio_size_mb"],
            "supported_formats": [".mp3", ".wav", ".ogg", ".m4a", ".webm"],
            "enable_logs": system_config["enable_logs"],
            "log_level": "INFO",
            "link_expiry_minutes": system_config["link_expiry_minutes"],
            "auto_delete_enabled": system_config["auto_delete_enabled"],
            "auto_delete_days": system_config["auto_delete_days"],
            "encryption_enabled": system_config["encryption_enabled"],
            "max_concurrent_jobs": system_config["max_concurrent_jobs"],
            "max_filename_length": 50,
            "max_path_length": 240
        },
        "ollama": {
            "host": "http://localhost:11434",
            "model": "llama3.2",
            "timeout": 120,
            "temperature": 0.7,
            "max_tokens": 2000
        },
        "whisper": {
            "model": "base",
            "language": "auto",
            "remove_filler_words": True,
            "filler_words": ["eh", "ah", "um", "mmm", "este", "o sea", "bueno"]
        },
        "analysis": {
            "required_fields": [
                "nombre_idea",
                "resumen",
                "explicacion",
                "tipo",
                "tags",
                "nivel_madurez",
                "viabilidad",
                "siguientes_pasos",
                "riesgos"
            ],
            "idea_types": [
                "App",
                "Negocio",
                "Automatización",
                "Contenido",
                "Otro"
            ],
            "madurez_levels": [
                "concepto",
                "desarrollado",
                "avanzado"
            ]
        }
    }
    
    # Crear carpetas necesarias
    Path(system_config["base_folder"]).mkdir(parents=True, exist_ok=True)
    Path("./temp").mkdir(parents=True, exist_ok=True)
    Path("./logs").mkdir(parents=True, exist_ok=True)
    Path("./data").mkdir(parents=True, exist_ok=True)
    
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)
    
    print("✅ Archivo config.json creado")
    print("✅ Carpetas del sistema creadas")


def create_gitignore():
    """Crea archivo .gitignore"""
    print("\n🌿 Creando .gitignore...")
    
    gitignore_content = """# VoiceToVision - Git Ignore

# Entornos virtuales
.venv/
venv/
env/
ENV/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Variables de entorno
.env
.env.local
.env.*.local

# Datos del sistema
/ideas/
/temp/
/data/
/logs/*.log

# Descargas temporales
/downloads/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# FFmpeg
ffmpeg.exe
ffprobe.exe
"""
    
    with open(".gitignore", "w", encoding="utf-8") as f:
        f.write(gitignore_content)
    
    print("✅ Archivo .gitignore creado")


def main():
    """Función principal del setup."""
    print_banner()
    
    print("\n🚀 Este asistente te guiará en la configuración de VoiceToVision")
    print("   Asegúrate de tener Python 3.8+ instalado y FFmpeg en tu sistema.\n")
    
    # Verificar Python
    if sys.version_info < (3, 8):
        print("❌ Error: Se requiere Python 3.8 o superior")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detectado")
    
    # Recopilar configuración
    config = {
        "discord": configure_discord(),
        "whatsapp": configure_whatsapp(),
        "system": configure_system()
    }
    
    # Crear archivos
    create_env_file(config)
    create_config_json(config)
    create_gitignore()
    
    # Setup del entorno virtual
    venv_path = setup_virtual_environment()
    
    # Preparar comando de activación
    activate_cmd = "pip install -r requirements.txt"
    if venv_path:
        if os.name == 'nt':
            activate_cmd = str(venv_path) + "\\Scripts\\activate"
        else:
            activate_cmd = "source " + str(venv_path) + "/bin/activate"
    
    # Resumen final
    print("\n" + "=" * 60)
    print("🎉 ¡CONFIGURACIÓN COMPLETADA!")
    print("=" * 60)
    print(f"""
📁 Estructura creada:
   - .env (variables de entorno)
   - config.json (configuración del sistema)
   - .gitignore (archivos ignorados por git)
   {f"- {venv_path}/ (entorno virtual)" if venv_path else ""}

🚀 Próximos pasos:
   1. Asegúrate de tener Ollama instalado y ejecutándose
      Descarga: https://ollama.com
   
   2. Descarga un modelo para Ollama:
      ollama pull llama3.2
   
   3. {"Activa el entorno virtual:" if venv_path else "Instala dependencias:"}
      {activate_cmd}

   
   4. Inicia el bot:
      python src/bot/bot.py


📖 Documentación completa en README.md

⚠️  IMPORTANTE: Mantén seguro tu archivo .env, nunca lo compartas.
""")
    
    if ask_yes_no("¿Deseas crear un README.md ahora?", default=True):
        print("\n📝 El README.md se creará automáticamente al finalizar el setup.")
    
    print("\n✨ VoiceToVision está listo para usar. ¡Suerte con tus ideas! 🧠")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelado por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error durante el setup: {e}")
        sys.exit(1)
