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
VoiceToVision - Script de Inicio Rápido
Facilita el inicio del sistema verificando dependencias y configuración.
"""

import os
import sys
import json
import subprocess
import asyncio
from pathlib import Path


def print_banner():
    """Muestra banner de inicio."""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║              🎙️  VoiceToVision - Inicio Rápido              ║
    ║                                                              ║
    ║         Sistema de Organización de Ideas por Voz          ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """)


def check_python_version():
    """Verifica versión de Python."""
    print("🔍 Verificando Python...")
    
    version = sys.version_info
    if version < (3, 8):
        print(f"❌ Python {version.major}.{version.minor} no soportado")
        print("   Se requiere Python 3.8 o superior")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_ffmpeg():
    """Verifica instalación de FFmpeg."""
    print("🔍 Verificando FFmpeg...")
    
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ {version_line}")
            return True
        else:
            print("❌ FFmpeg no encontrado o no funcional")
            return False
            
    except FileNotFoundError:
        print("❌ FFmpeg no está instalado o no está en PATH")
        print("   Descarga: https://ffmpeg.org/download.html")
        return False
    except Exception as e:
        print(f"⚠️  Error verificando FFmpeg: {e}")
        return False


def check_ollama():
    """Verifica que Ollama esté ejecutándose."""
    print("🔍 Verificando Ollama...")
    
    try:
        import urllib.request
        import json
        
        req = urllib.request.Request(
            "http://localhost:11434/api/tags",
            method='GET'
        )
        
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                models = [m.get("name") for m in data.get("models", [])]
                
                print(f"✅ Ollama ejecutándose")
                print(f"   Modelos disponibles: {len(models)}")
                
                # Verificar si hay modelos
                if not models:
                    print("⚠️  No hay modelos descargados")
                    print("   Ejecuta: ollama pull llama3.2")
                    return False
                
                # Verificar llama3.2
                has_llama = any("llama3.2" in m for m in models)
                if has_llama:
                    print("✅ Modelo llama3.2 disponible")
                else:
                    print(f"⚠️  llama3.2 no encontrado, disponibles: {', '.join(models[:3])}")
                
                return True
            else:
                print(f"❌ Ollama respondió con status {response.status}")
                return False
                
    except Exception as e:
        print(f"❌ No se pudo conectar a Ollama: {e}")
        print("   Asegúrate de que Ollama esté ejecutándose:")
        print("   ollama serve")
        return False


def check_config_files():
    """Verifica archivos de configuración."""
    print("🔍 Verificando configuración...")
    
    files_ok = True
    
    # .env
    env_path = Path("config/.env")
    if not env_path.exists():
        env_path = Path(".env")  # Fallback a raíz
    
    if not env_path.exists():
        print("❌ Archivo .env no encontrado")
        print("   Ejecuta: python scripts/setup.py")
        files_ok = False
    else:
        print(f"✅ .env encontrado ({env_path})")
        
        # Verificar DISCORD_TOKEN
        with open(env_path, "r") as f:
            content = f.read()
            if "DISCORD_TOKEN=tu_token" in content or "DISCORD_TOKEN=" not in content:
                print("⚠️  DISCORD_TOKEN no configurado en .env")
                files_ok = False
            else:
                print("✅ DISCORD_TOKEN configurado")
    
    # config.json
    config_path = Path("config/config.json")
    if not config_path.exists():
        config_path = Path("config.json")  # Fallback a raíz
    
    if not config_path.exists():
        print("❌ Archivo config.json no encontrado")
        print("   Ejecuta: python scripts/setup.py")
        files_ok = False
    else:
        print(f"✅ config.json encontrado ({config_path})")
        
        # Validar JSON
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
                
            # Verificar campos esenciales
            required = ["discord", "system", "ollama", "whisper"]
            missing = [r for r in required if r not in config]
            
            if missing:
                print(f"⚠️  Campos faltantes en config.json: {missing}")
                files_ok = False
            else:
                print("✅ Estructura de config.json válida")
                
        except json.JSONDecodeError as e:
            print(f"❌ config.json inválido: {e}")
            files_ok = False
    
    return files_ok


def check_dependencies():
    """Verifica dependencias de Python."""
    print("🔍 Verificando dependencias...")
    
    required = [
        "discord",
        "whisper",
        "aiohttp",
        "aiosqlite",
        "aiofiles",
        "ffmpeg",
        "pydub"
    ]
    
    missing = []
    
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Paquetes faltantes: {', '.join(missing)}")
        print("   Instala con: pip install -r requirements.txt")
        return False
    
    print(f"✅ Todas las dependencias instaladas ({len(required)} paquetes)")
    return True


def create_directories():
    """Crea directorios necesarios."""
    print("🔍 Verificando directorios...")
    
    dirs = ["./ideas", "./temp", "./logs", "./data"]
    
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
        print(f"✅ {d}/")
    
    return True


def start_bot():
    """Inicia el bot."""
    print("\n🚀 Iniciando VoiceToVision Bot...\n")
    
    try:
        # Usar subprocess para mantener el control
        bot_path = Path("src/bot/bot.py")
        if not bot_path.exists():
            bot_path = Path("bot.py")  # Fallback
        
        result = subprocess.run(
            [sys.executable, str(bot_path)],
            cwd=os.getcwd()
        )
        
        return result.returncode == 0
        
    except KeyboardInterrupt:
        print("\n\n👋 Bot detenido por usuario")
        return True
    except Exception as e:
        print(f"\n❌ Error iniciando bot: {e}")
        return False


def main():
    """Función principal."""
    print_banner()
    
    print("Realizando verificaciones pre-inicio...\n")
    
    checks = [
        ("Python", check_python_version),
        ("FFmpeg", check_ffmpeg),
        ("Ollama", check_ollama),
        ("Configuración", check_config_files),
        ("Dependencias", check_dependencies),
        ("Directorios", create_directories)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
            print()
        except Exception as e:
            print(f"❌ Error en verificación {name}: {e}\n")
            results.append((name, False))
    
    # Resumen
    print("=" * 60)
    print("📋 RESUMEN DE VERIFICACIONES")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✅ OK" if result else "❌ FALLÓ"
        print(f"  {status} - {name}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    
    if not all_passed:
        print("\n⚠️  Algunas verificaciones fallaron.")
        print("   Corrige los problemas antes de iniciar el bot.")
        print("\n   Para configuración inicial, ejecuta: python scripts/setup.py")
        return 1
    
    # Preguntar antes de iniciar
    print("\n✅ Todas las verificaciones pasaron.")
    
    try:
        response = input("\n¿Deseas iniciar el bot ahora? (Y/n): ").strip().lower()
        if response in ['n', 'no']:
            print("\n👋 Inicio cancelado.")
            print("   Para iniciar manualmente: python src/bot/bot.py")
            return 0
    except KeyboardInterrupt:
        print("\n\n👋 Cancelado.")
        return 0
    
    # Iniciar bot
    success = start_bot()
    
    return 0 if success else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n👋 Programa interrumpido")
        sys.exit(0)
