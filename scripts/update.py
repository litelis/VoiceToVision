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
VoiceToVision - Script de Actualización
Comprueba si hay nuevas versiones en el repositorio y permite actualizar.
"""

import subprocess
import sys
import os


def run_git_command(command):
    """Ejecuta un comando git y retorna la salida."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            shell=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Error ejecutando git: {e}")
        return None


def get_current_commit():
    """Obtiene el hash del commit actual."""
    return run_git_command("git rev-parse HEAD")


def get_remote_commit():
    """Obtiene el hash del último commit en el remoto."""
    # Primero hacer fetch para obtener la última info del remoto
    print("🔄 Obteniendo información del repositorio remoto...")
    fetch_result = run_git_command("git fetch origin")
    if fetch_result is None:
        return None
    
    # Obtener el commit del remoto
    return run_git_command("git rev-parse origin/master")


def check_for_updates():
    """Comprueba si hay actualizaciones disponibles."""
    print("🔍 Comprobando actualizaciones de VoiceToVision...")
    print("-" * 50)
    
    # Verificar que estamos en un repositorio git
    if not os.path.exists(".git"):
        print("❌ No se encontró repositorio git en el directorio actual.")
        return False
    
    # Obtener commits
    current = get_current_commit()
    remote = get_remote_commit()
    
    if current is None or remote is None:
        print("❌ No se pudo obtener información de commits.")
        return False
    
    print(f"📍 Commit local:  {current[:8]}")
    print(f"🌐 Commit remoto: {remote[:8]}")
    
    # Comparar commits
    if current == remote:
        print("\n✅ El repositorio está actualizado. No hay cambios nuevos.")
        return False
    else:
        print("\n⚠️  Hay nuevos cambios disponibles en el repositorio remoto.")
        return True


def ask_yes_no(question, default=True):
    """Pregunta sí/no con valor por defecto."""
    default_str = "Y/n" if default else "y/N"
    while True:
        try:
            response = input(f"{question} [{default_str}]: ").strip().lower()
            if not response:
                return default
            if response in ['y', 'yes', 's', 'si', 'sí']:
                return True
            if response in ['n', 'no']:
                return False
            print("Por favor responde 'y' o 'n'")
        except KeyboardInterrupt:
            print("\n\n⚠️  Operación cancelada.")
            return False


def update_repository():
    """Actualiza el repositorio con los cambios del remoto."""
    print("\n📥 Actualizando repositorio...")
    print("-" * 50)
    
    # Hacer pull
    result = run_git_command("git pull origin master")
    
    if result is not None:
        print("✅ Repositorio actualizado exitosamente.")
        print(f"\n📋 Cambios aplicados:\n{result}")
        return True
    else:
        print("❌ Error al actualizar el repositorio.")
        print("   Puede haber conflictos. Resuélvelos manualmente con:")
        print("   git status")
        print("   git pull origin master")
        return False


def main():
    """Función principal."""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║           🎙️  VoiceToVision - Actualizador                  ║
    ║                                                              ║
    ║        Comprueba y aplica actualizaciones del repo          ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Comprobar actualizaciones
    has_updates = check_for_updates()
    
    if not has_updates:
        print("\n👋 No hay nada que actualizar.")
        return 0
    
    # Preguntar si actualizar
    if ask_yes_no("\n¿Deseas actualizar a la última versión?", default=True):
        success = update_repository()
        if success:
            print("\n🎉 ¡Actualización completada!")
            print("   Reinicia el bot para aplicar los cambios:")
            print("   python scripts/start.py")
            return 0
        else:
            return 1
    else:
        print("\n👋 Actualización cancelada por el usuario.")
        print("   Puedes actualizar manualmente más tarde con:")
        print("   git pull origin master")
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Operación cancelada por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)
