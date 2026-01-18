#!/usr/bin/env python3
"""
Workflow Sync Tool - Interfaz Interactiva de Terminal

Aplicación de terminal para sincronizar GitHub Actions workflows.
"""

from __future__ import annotations

import getpass
import json
import os
import stat
import sys
from pathlib import Path

# Agregar el directorio actual al path para imports
sys.path.insert(0, str(Path(__file__).parent))

from clients.github_client import GitHubClient
from exceptions import ValidationError, WorkflowSyncError
from models import SyncConfig, SyncStatus
from services.sync_service import WorkflowSyncService
from validators.input_validator import InputValidator


# Archivo de configuración
CONFIG_FILE = Path.home() / ".workflow-sync-config"


# Colores ANSI
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


def clear_screen():
    """Limpia la pantalla."""
    os.system("clear" if os.name != "nt" else "cls")


def print_header():
    """Imprime el header de la aplicación."""
    clear_screen()
    print(f"{Colors.CYAN}{Colors.BOLD}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║                                                          ║")
    print("║              🔄  WORKFLOW SYNC TOOL  🔄                  ║")
    print("║                                                          ║")
    print("║     Sincroniza GitHub Actions workflows entre repos      ║")
    print("║                                                          ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")
    print()


def print_success(msg: str):
    """Imprime mensaje de éxito."""
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")


def print_error(msg: str):
    """Imprime mensaje de error."""
    print(f"{Colors.RED}✗ {msg}{Colors.END}")


def print_warning(msg: str):
    """Imprime mensaje de advertencia."""
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")


def print_info(msg: str):
    """Imprime mensaje informativo."""
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")


def prompt(label: str, default: str = "", required: bool = True, secret: bool = False) -> str:
    """Solicita input al usuario."""
    default_hint = f" [{default}]" if default else ""
    required_hint = " *" if required else ""

    prompt_text = f"{Colors.BOLD}{label}{required_hint}{default_hint}:{Colors.END} "

    if secret:
        value = getpass.getpass(prompt_text)
    else:
        value = input(prompt_text)

    value = value.strip()

    if not value and default:
        return default

    if not value and required:
        print_error("Este campo es requerido")
        return prompt(label, default, required, secret)

    return value


def prompt_yes_no(label: str, default: bool = False) -> bool:
    """Solicita confirmación sí/no."""
    default_hint = "S/n" if default else "s/N"
    prompt_text = f"{Colors.BOLD}{label} [{default_hint}]:{Colors.END} "

    value = input(prompt_text).strip().lower()

    if not value:
        return default

    return value in ("s", "si", "sí", "y", "yes", "1", "true")


def prompt_menu(label: str, options: list[tuple[str, str]]) -> str:
    """Muestra un menú de opciones."""
    print(f"{Colors.BOLD}{label}{Colors.END}")
    print()
    for i, (key, description) in enumerate(options, 1):
        print(f"  {Colors.CYAN}{i}{Colors.END}) {description}")
    print()

    while True:
        choice = input(f"{Colors.BOLD}Selecciona una opción (1-{len(options)}):{Colors.END} ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx][0]
        except ValueError:
            pass
        print_error("Opción inválida")


# ─── Gestión de Token ───────────────────────────────────────────────────────


def load_saved_token() -> str | None:
    """Carga el token guardado del archivo de configuración."""
    if not CONFIG_FILE.exists():
        return None

    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            return config.get("token")
    except (json.JSONDecodeError, IOError):
        return None


def save_token(token: str) -> bool:
    """Guarda el token en el archivo de configuración."""
    try:
        config = {}
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        config["token"] = token

        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)

        # Establecer permisos solo para el usuario (600)
        CONFIG_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)

        return True
    except IOError as e:
        print_error(f"No se pudo guardar el token: {e}")
        return False


def delete_token() -> bool:
    """Elimina el token guardado."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)

            if "token" in config:
                del config["token"]

            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)

            return True
        except (json.JSONDecodeError, IOError):
            pass
    return False


def get_token() -> str | None:
    """Obtiene el token (guardado, de env, o solicita uno nuevo)."""
    saved_token = load_saved_token()
    env_token = os.environ.get("GITHUB_TOKEN", "")

    if saved_token:
        # Mostrar token parcialmente oculto
        masked = saved_token[:4] + "*" * (len(saved_token) - 8) + saved_token[-4:]
        print_info(f"Token guardado encontrado: {masked}")
        use_saved = prompt_yes_no("¿Usar este token?", default=True)
        if use_saved:
            return saved_token

    if env_token:
        print_info("Token detectado en variable de entorno GITHUB_TOKEN")
        use_env = prompt_yes_no("¿Usar token de la variable de entorno?", default=True)
        if use_env:
            # Preguntar si quiere guardarlo
            if prompt_yes_no("¿Guardar este token para futuras sesiones?", default=True):
                save_token(env_token)
                print_success("Token guardado")
            return env_token

    # Solicitar nuevo token
    print()
    token = prompt("GitHub Token", secret=True)

    try:
        InputValidator.validate_token(token)
    except ValidationError as e:
        print_error(str(e))
        return None

    # Preguntar si quiere guardarlo
    if prompt_yes_no("¿Guardar este token para futuras sesiones?", default=True):
        if save_token(token):
            print_success("Token guardado en ~/.workflow-sync-config")

    return token


def change_token():
    """Permite cambiar/rotar el token."""
    print()
    print(f"{Colors.CYAN}─── Cambiar Token ───{Colors.END}")
    print()

    saved_token = load_saved_token()
    if saved_token:
        masked = saved_token[:4] + "*" * (len(saved_token) - 8) + saved_token[-4:]
        print(f"Token actual: {masked}")
        print()

    choice = prompt_menu("¿Qué deseas hacer?", [
        ("new", "Ingresar nuevo token"),
        ("delete", "Eliminar token guardado"),
        ("cancel", "Cancelar"),
    ])

    if choice == "new":
        token = prompt("Nuevo GitHub Token", secret=True)
        try:
            InputValidator.validate_token(token)
            if save_token(token):
                print_success("Token actualizado correctamente")
            return token
        except ValidationError as e:
            print_error(str(e))
            return None

    elif choice == "delete":
        if delete_token():
            print_success("Token eliminado")
        else:
            print_warning("No había token guardado")
        return None

    return None


# ─── Menú Principal ─────────────────────────────────────────────────────────


def show_main_menu() -> str:
    """Muestra el menú principal."""
    print(f"{Colors.CYAN}─── Menú Principal ───{Colors.END}")
    print()

    return prompt_menu("¿Qué deseas hacer?", [
        ("sync", "🔄 Sincronizar workflows"),
        ("token", "🔑 Cambiar/Rotar token"),
        ("exit", "🚪 Salir"),
    ])


# ─── Configuración de Sincronización ────────────────────────────────────────


def get_sync_config(token: str) -> SyncConfig | None:
    """Solicita la configuración de sincronización al usuario."""
    print()
    print(f"{Colors.CYAN}─── Configuración de Sincronización ───{Colors.END}")
    print()

    # Organización
    org = prompt("Organización de GitHub")
    try:
        InputValidator.validate_organization(org)
    except ValidationError as e:
        print_error(str(e))
        return None

    # Topic
    topic = prompt("Topic para filtrar repositorios")
    try:
        InputValidator.validate_topic(topic)
    except ValidationError as e:
        print_error(str(e))
        return None

    # Repo fuente
    source_repo = prompt("Repositorio fuente (sin org)")
    try:
        InputValidator.validate_repository(source_repo)
    except ValidationError as e:
        print_error(str(e))
        return None

    print()

    # Archivos (opcional)
    files_str = prompt("Archivos específicos (separados por espacio)", required=False)
    files_filter = []
    if files_str:
        files_filter = files_str.split()
        try:
            InputValidator.validate_workflow_files(files_filter)
        except ValidationError as e:
            print_error(str(e))
            return None

    print()

    # Opciones
    print(f"{Colors.CYAN}─── Opciones ───{Colors.END}")
    print()
    dry_run = prompt_yes_no("Modo Dry Run (solo mostrar cambios)", default=False)
    parallel = prompt_yes_no("Ejecución paralela", default=False)

    return SyncConfig(
        token=token,
        org=org,
        topic=topic,
        source_repo=source_repo,
        dry_run=dry_run,
        files_filter=files_filter,
        max_workers=4 if parallel else 1,
        timeout=30,
    )


def show_summary(config: SyncConfig):
    """Muestra el resumen de la configuración."""
    print()
    print(f"{Colors.CYAN}─── Resumen ───{Colors.END}")
    print()
    print(f"  Organización:     {Colors.BOLD}{config.org}{Colors.END}")
    print(f"  Topic:            {Colors.BOLD}{config.topic}{Colors.END}")
    print(f"  Repo fuente:      {Colors.BOLD}{config.source_repo}{Colors.END}")
    print(f"  Archivos:         {Colors.BOLD}{config.files_filter or 'todos'}{Colors.END}")
    print(f"  Dry Run:          {Colors.BOLD}{'Sí' if config.dry_run else 'No'}{Colors.END}")
    print(f"  Paralelo:         {Colors.BOLD}{'Sí' if config.max_workers > 1 else 'No'}{Colors.END}")
    print()


def run_sync(config: SyncConfig) -> bool:
    """Ejecuta la sincronización."""
    print(f"{Colors.CYAN}─── Ejecutando sincronización ───{Colors.END}")
    print()

    try:
        print_info("Conectando a GitHub...")
        client = GitHubClient(token=config.token, timeout=config.timeout)

        print_info(f"Cargando workflows desde {config.org}/{config.source_repo}...")
        service = WorkflowSyncService(client=client, config=config)

        print_info(f"Buscando repos con topic '{config.topic}'...")
        print()

        results = service.run(parallel=config.max_workers > 1)

        # Mostrar resultados
        print()
        print(f"{Colors.CYAN}─── Resultados ───{Colors.END}")
        print()

        success = [r for r in results if r.status == SyncStatus.SUCCESS]
        no_changes = [r for r in results if r.status == SyncStatus.NO_CHANGES]
        skipped = [r for r in results if r.status == SyncStatus.SKIPPED]
        errors = [r for r in results if r.status == SyncStatus.ERROR]

        print(f"  {Colors.GREEN}PRs creados:{Colors.END}     {len(success)}")
        print(f"  {Colors.BLUE}Sin cambios:{Colors.END}      {len(no_changes)}")
        print(f"  {Colors.YELLOW}Saltados:{Colors.END}        {len(skipped)}")
        print(f"  {Colors.RED}Errores:{Colors.END}         {len(errors)}")
        print()

        if success:
            print(f"{Colors.GREEN}PRs creados:{Colors.END}")
            for r in success:
                print(f"  ✓ {r.repo_name}")
                if r.pr_url:
                    print(f"    {Colors.CYAN}{r.pr_url}{Colors.END}")
            print()

        if errors:
            print(f"{Colors.RED}Errores:{Colors.END}")
            for r in errors:
                print(f"  ✗ {r.repo_name}: {r.message}")
            print()

        if skipped:
            print(f"{Colors.YELLOW}Saltados:{Colors.END}")
            for r in skipped:
                print(f"  ⏭ {r.repo_name}: {r.message}")
            print()

        return len(errors) == 0

    except WorkflowSyncError as e:
        print_error(f"Error de sincronización: {e}")
        return False
    except Exception as e:
        print_error(f"Error inesperado: {e}")
        return False


# ─── Main ───────────────────────────────────────────────────────────────────


def main():
    """Punto de entrada principal."""
    current_token = None

    try:
        while True:
            print_header()

            # Verificar si hay token
            if not current_token:
                saved = load_saved_token()
                env = os.environ.get("GITHUB_TOKEN", "")
                if saved or env:
                    print_info("Token disponible" + (" (guardado)" if saved else " (env)"))
                else:
                    print_warning("No hay token configurado")
            else:
                print_success("Token activo")

            print()

            choice = show_main_menu()

            if choice == "exit":
                print()
                print_info("¡Hasta luego!")
                break

            elif choice == "token":
                new_token = change_token()
                if new_token:
                    current_token = new_token
                print()
                input("Presiona Enter para continuar...")

            elif choice == "sync":
                # Obtener token si no lo tenemos
                if not current_token:
                    print()
                    current_token = get_token()
                    if not current_token:
                        print()
                        print_error("Se requiere un token para continuar")
                        input("Presiona Enter para continuar...")
                        continue

                config = get_sync_config(current_token)
                if not config:
                    print()
                    print_error("Configuración inválida")
                    input("Presiona Enter para continuar...")
                    continue

                show_summary(config)

                if not prompt_yes_no("¿Continuar con la sincronización?", default=True):
                    print()
                    print_warning("Operación cancelada")
                    input("Presiona Enter para continuar...")
                    continue

                print()
                success = run_sync(config)

                print()
                if success:
                    print_success("Sincronización completada exitosamente")
                else:
                    print_warning("Sincronización completada con errores")

                print()
                input("Presiona Enter para continuar...")

    except KeyboardInterrupt:
        print()
        print_warning("Operación cancelada")
        sys.exit(130)


if __name__ == "__main__":
    main()
