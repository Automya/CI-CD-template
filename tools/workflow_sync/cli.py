"""
Interfaz de línea de comandos para el sincronizador de workflows.

Principio SOLID: Single Responsibility
- Solo se encarga de la interfaz CLI, delegando la lógica al servicio.

Principio SOLID: Dependency Inversion
- Crea e inyecta las dependencias necesarias al servicio.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Agregar directorio actual al path para imports
sys.path.insert(0, str(Path(__file__).parent))

from clients.github_client import GitHubClient
from exceptions import ValidationError, WorkflowSyncError
from models import SyncConfig, SyncResult, SyncStatus
from services.sync_service import WorkflowSyncService
from validators.input_validator import InputValidator

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configura el sistema de logging.

    Args:
        verbose: Si es True, usa nivel DEBUG.
    """
    level = logging.DEBUG if verbose else logging.INFO

    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def parse_args() -> argparse.Namespace:
    """Parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Sincroniza workflows de GitHub Actions entre repositorios",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Sincronizar todos los workflows a repos con topic 'microservice'
  export GITHUB_TOKEN=ghp_xxxx
  python -m workflow_sync --org Automya --topic microservice --source-repo api-gateway

  # Sincronizar solo archivos específicos
  python -m workflow_sync --org Automya --topic microservice --source-repo api-gateway \\
      --files build.yml deploy.yml

  # Modo dry-run (ver qué cambiaría sin hacer cambios)
  python -m workflow_sync --org Automya --topic microservice --source-repo api-gateway --dry-run

  # Ejecución en paralelo para muchos repos
  python -m workflow_sync --org Automya --topic microservice --source-repo api-gateway --parallel

Variables de entorno (REQUERIDAS):
  GITHUB_TOKEN    Token de GitHub con permisos repo y read:org
        """,
    )

    parser.add_argument(
        "--org",
        required=True,
        help="Nombre de la organización de GitHub",
    )
    parser.add_argument(
        "--topic",
        required=True,
        help="Topic para filtrar repositorios destino",
    )
    parser.add_argument(
        "--source-repo",
        required=True,
        help="Nombre del repositorio fuente (sin org)",
    )
    parser.add_argument(
        "--files",
        nargs="+",
        default=[],
        help="Lista de archivos específicos a sincronizar",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostrar qué cambiaría sin hacer modificaciones",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Habilitar salida detallada (debug)",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Ejecutar sincronización en paralelo",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Número máximo de workers para ejecución paralela (default: 4)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout para llamadas API en segundos (default: 30)",
    )
    parser.add_argument(
        "--auto-merge",
        action="store_true",
        help="Mergear PRs automáticamente después de crearlos",
    )

    return parser.parse_args()


def print_summary(results: list[SyncResult]) -> None:
    """Imprime el resumen de la sincronización."""
    success = [r for r in results if r.status == SyncStatus.SUCCESS]
    no_changes = [r for r in results if r.status == SyncStatus.NO_CHANGES]
    errors = [r for r in results if r.status == SyncStatus.ERROR]
    skipped = [r for r in results if r.status == SyncStatus.SKIPPED]

    total_duration = sum(r.duration_seconds for r in results)

    logger.info("=" * 60)
    logger.info("RESUMEN")
    logger.info("=" * 60)
    logger.info("PRs creados:     %d", len(success))
    logger.info("Sin cambios:     %d", len(no_changes))
    logger.info("Saltados:        %d", len(skipped))
    logger.info("Errores:         %d", len(errors))
    logger.info("Duración total:  %.1fs", total_duration)

    if success:
        logger.info("")
        logger.info("PRs creados:")
        for r in success:
            logger.info("  - %s: %s", r.repo_name, r.pr_url)
            if r.files_failed:
                logger.warning(
                    "    (parcial: %d archivos fallaron)", len(r.files_failed)
                )

    if errors:
        logger.warning("")
        logger.warning("Errores encontrados:")
        for r in errors:
            logger.warning("  - %s: %s", r.repo_name, r.message)

    if skipped:
        logger.info("")
        logger.info("Repositorios saltados:")
        for r in skipped:
            logger.info("  - %s: %s", r.repo_name, r.message)


def create_config(args: argparse.Namespace, token: str) -> SyncConfig:
    """Crea y valida la configuración.

    Args:
        args: Argumentos parseados.
        token: Token de GitHub.

    Returns:
        Configuración validada.

    Raises:
        ValidationError: Si algún input es inválido.
    """
    # Validar inputs
    InputValidator.validate_token(token)
    InputValidator.validate_organization(args.org)
    InputValidator.validate_repository(args.source_repo)
    InputValidator.validate_topic(args.topic)
    validated_files = InputValidator.validate_workflow_files(args.files)

    return SyncConfig(
        token=token,
        org=args.org,
        topic=args.topic,
        source_repo=args.source_repo,
        dry_run=args.dry_run,
        files_filter=validated_files,
        max_workers=args.max_workers,
        timeout=args.timeout,
        auto_merge=args.auto_merge,
    )


def main() -> int:
    """Punto de entrada principal.

    Returns:
        Código de salida (0=éxito, 1=error, 2=validación, 130=interrumpido).
    """
    args = parse_args()
    setup_logging(verbose=args.verbose)

    # Obtener token de variable de entorno
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        logger.error("GITHUB_TOKEN environment variable is required")
        logger.error(
            "Security note: Tokens must be provided via environment variable, "
            "not command line arguments"
        )
        return 1

    try:
        # Crear configuración validada
        config = create_config(args, token)

        # Mostrar configuración
        logger.info("=" * 60)
        logger.info("WORKFLOW SYNC TOOL")
        logger.info("=" * 60)
        logger.info("Organización:  %s", config.org)
        logger.info("Topic:         %s", config.topic)
        logger.info("Repo fuente:   %s", config.source_repo)
        logger.info("Archivos:      %s", config.files_filter or "todos")
        logger.info("Dry run:       %s", config.dry_run)
        logger.info("Paralelo:      %s", args.parallel)
        logger.info("Timeout:       %ds", config.timeout)

        # Crear dependencias e inyectarlas
        client = GitHubClient(token=config.token, timeout=config.timeout)
        service = WorkflowSyncService(client=client, config=config)

        # Ejecutar sincronización
        results = service.run(parallel=args.parallel)

        # Mostrar resumen
        print_summary(results)

        has_errors = any(r.status == SyncStatus.ERROR for r in results)
        return 1 if has_errors else 0

    except ValidationError as e:
        logger.error("Error de validación: %s", e)
        return 2
    except WorkflowSyncError as e:
        logger.error("Error de sincronización: %s", e)
        return 1
    except KeyboardInterrupt:
        logger.warning("Operación cancelada por el usuario")
        return 130
    except Exception as e:
        logger.exception("Error inesperado: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
