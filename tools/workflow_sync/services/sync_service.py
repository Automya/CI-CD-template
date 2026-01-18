"""
Servicio principal de sincronización de workflows.

Principio SOLID: Single Responsibility
- Solo se encarga de orquestar la sincronización.

Principio SOLID: Dependency Inversion
- Depende de abstracciones (IGitHubClient), no de implementaciones concretas.

Principio SOLID: Open/Closed
- La estrategia de sincronización puede extenderse sin modificar código.
"""

from __future__ import annotations

import logging
import random
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING

import sys
from pathlib import Path

# Agregar directorio padre al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from exceptions import SourceRepoError
from models import FileChange, SyncConfig, SyncResult, SyncStatus

if TYPE_CHECKING:
    from github.Repository import Repository

    from clients.github_client import IGitHubClient

logger = logging.getLogger(__name__)


class ISyncStrategy(ABC):
    """Interfaz para estrategias de sincronización.

    Principio SOLID: Open/Closed
    - Permite agregar nuevas estrategias sin modificar código existente.
    """

    @abstractmethod
    def sync(
        self,
        service: "WorkflowSyncService",
        repos: list[Repository],
    ) -> list[SyncResult]:
        """Ejecuta la sincronización con la estrategia definida."""
        pass


class SequentialSyncStrategy(ISyncStrategy):
    """Estrategia de sincronización secuencial."""

    def sync(
        self,
        service: "WorkflowSyncService",
        repos: list[Repository],
    ) -> list[SyncResult]:
        """Sincroniza repositorios secuencialmente."""
        results: list[SyncResult] = []

        for idx, repo in enumerate(repos):
            if idx > 0 and idx % 5 == 0:
                service.client.check_rate_limit()

            logger.info(
                "Sincronizando (%d/%d): %s", idx + 1, len(repos), repo.name
            )
            repo_start = time.time()
            result = service.sync_single_repo(repo)
            result.duration_seconds = time.time() - repo_start
            results.append(result)
            service._log_result(result)
            service.client.handle_post_operation_rate_limit()

        return results


class ParallelSyncStrategy(ISyncStrategy):
    """Estrategia de sincronización paralela."""

    def __init__(self, max_workers: int = 4) -> None:
        self._max_workers = max_workers

    def sync(
        self,
        service: "WorkflowSyncService",
        repos: list[Repository],
    ) -> list[SyncResult]:
        """Sincroniza repositorios en paralelo."""
        results: list[SyncResult] = []

        logger.info(
            "Procesando %d repositorios con %d workers",
            len(repos),
            self._max_workers,
        )

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            future_to_repo = {
                executor.submit(service.sync_single_repo, repo): repo
                for repo in repos
            }

            for future in as_completed(future_to_repo):
                repo = future_to_repo[future]
                try:
                    result = future.result()
                    results.append(result)
                    service._log_result(result)
                except Exception as exc:
                    logger.error("Error procesando %s: %s", repo.name, exc)
                    results.append(
                        SyncResult(
                            repo_name=repo.name,
                            status=SyncStatus.ERROR,
                            message=str(exc),
                        )
                    )

        return results


class PRBodyGenerator:
    """Generador de cuerpos de PR.

    Principio SOLID: Single Responsibility
    - Solo se encarga de generar el texto del PR.
    """

    @staticmethod
    def generate(
        org: str,
        source_repo: str,
        files_updated: list[str],
        files_failed: list[str],
    ) -> str:
        """Genera el cuerpo del PR."""
        files_list = "\n".join([f"- `{f}`" for f in files_updated])

        partial_warning = ""
        if files_failed:
            failed_list = ", ".join([f"`{f}`" for f in files_failed])
            partial_warning = (
                f"\n\n> **Warning**: Algunos archivos no se pudieron "
                f"sincronizar: {failed_list}\n"
            )

        return f"""## Sincronización de Workflows

Este PR sincroniza los GitHub Actions workflows desde el repositorio fuente.

### Archivos actualizados
{files_list}
{partial_warning}
### Repositorio fuente
`{org}/{source_repo}`

---
*PR generado automáticamente por workflow-sync*
"""


class WorkflowSyncService:
    """Servicio principal de sincronización.

    Principio SOLID: Single Responsibility
    - Orquesta la sincronización, delegando responsabilidades específicas.

    Principio SOLID: Dependency Inversion
    - Recibe el cliente por inyección de dependencias.

    Attributes:
        WORKFLOWS_PATH: Ruta donde se almacenan los workflows.
        BRANCH_PREFIX: Prefijo para las ramas de sincronización.
    """

    WORKFLOWS_PATH = ".github/workflows"
    BRANCH_PREFIX = "sync/workflows-update"

    def __init__(
        self,
        client: "IGitHubClient",
        config: SyncConfig,
    ) -> None:
        """Inicializa el servicio.

        Args:
            client: Cliente de GitHub (inyección de dependencias).
            config: Configuración de sincronización.
        """
        self._client = client
        self._config = config
        self._source_workflows: dict[str, str] = {}
        self._start_time: float | None = None

    @property
    def client(self) -> "IGitHubClient":
        """Retorna el cliente de GitHub."""
        return self._client

    @property
    def config(self) -> SyncConfig:
        """Retorna la configuración."""
        return self._config

    def run(self, parallel: bool = False) -> list[SyncResult]:
        """Ejecuta la sincronización completa.

        Args:
            parallel: Si es True, usa sincronización paralela.

        Returns:
            Lista de resultados de sincronización.

        Raises:
            SourceRepoError: Si no se pueden cargar los workflows fuente.
        """
        self._start_time = time.time()

        # Check rate limit
        self._client.check_rate_limit()

        # Cargar workflows fuente
        logger.info(
            "Cargando workflows desde: %s/%s",
            self._config.org,
            self._config.source_repo,
        )
        self._load_source_workflows()

        logger.info(
            "Encontrados %d archivo(s): %s",
            len(self._source_workflows),
            ", ".join(self._source_workflows.keys()),
        )

        # Buscar repos destino
        self._client.check_rate_limit(is_search=True)

        logger.info(
            "Buscando repos con topic '%s' en %s...",
            self._config.topic,
            self._config.org,
        )

        target_repos = self._client.search_repositories_by_topic(
            self._config.org, self._config.topic
        )

        if not target_repos:
            logger.warning(
                "No se encontraron repos con topic '%s'", self._config.topic
            )
            return []

        logger.info("Encontrados %d repositorio(s)", len(target_repos))

        # Filtrar repo fuente y obtener objetos Repository
        source_full_name = f"{self._config.org}/{self._config.source_repo}"
        repos_to_sync = []

        for repo_info in target_repos:
            if repo_info.full_name == source_full_name:
                continue
            repo = self._client.get_repository(repo_info.full_name)
            repos_to_sync.append(repo)

        # Seleccionar estrategia
        strategy: ISyncStrategy
        if parallel:
            strategy = ParallelSyncStrategy(self._config.max_workers)
        else:
            strategy = SequentialSyncStrategy()

        # Ejecutar sincronización
        results = strategy.sync(self, repos_to_sync)

        total_duration = time.time() - self._start_time
        logger.info("Duración total: %.1f segundos", total_duration)

        return results

    def sync_single_repo(self, repo: Repository) -> SyncResult:
        """Sincroniza workflows a un repositorio específico.

        Args:
            repo: Repositorio destino.

        Returns:
            Resultado de la sincronización.
        """
        branch_created = None

        try:
            # Verificaciones previas
            skip_result = self._check_skip_conditions(repo)
            if skip_result:
                return skip_result

            # Obtener cambios necesarios
            changes = self._get_required_changes(repo)

            if not changes:
                return SyncResult(
                    repo_name=repo.name,
                    status=SyncStatus.NO_CHANGES,
                    message="Todos los workflows están actualizados",
                )

            if self._config.dry_run:
                return SyncResult(
                    repo_name=repo.name,
                    status=SyncStatus.SKIPPED,
                    message=f"Dry run - {len(changes)} archivo(s) cambiarían",
                    files_updated=[c.filename for c in changes],
                )

            # Crear PR con cambios
            return self._create_sync_pr(repo, changes)

        except Exception as e:
            if branch_created:
                self._client.delete_branch(repo, branch_created)

            logger.exception("Error sincronizando %s", repo.name)
            return SyncResult(
                repo_name=repo.name,
                status=SyncStatus.ERROR,
                message=f"Error: {str(e)}",
                branch_created=branch_created,
            )

    def _load_source_workflows(self) -> None:
        """Carga los workflows del repositorio fuente."""
        source_repo = self._client.get_repository(
            f"{self._config.org}/{self._config.source_repo}"
        )
        workflows = self._client.get_workflow_files(source_repo, self.WORKFLOWS_PATH)

        # Aplicar filtro si existe
        if self._config.files_filter:
            workflows = {
                k: v for k, v in workflows.items() if k in self._config.files_filter
            }

        if not workflows:
            raise SourceRepoError(
                f"No se encontraron workflows en {self.WORKFLOWS_PATH}"
            )

        self._source_workflows = workflows

    def _check_skip_conditions(self, repo: Repository) -> SyncResult | None:
        """Verifica condiciones para saltar el repo.

        Returns:
            SyncResult si debe saltarse, None si debe procesarse.
        """
        # Repo archivado
        if repo.archived:
            return SyncResult(
                repo_name=repo.name,
                status=SyncStatus.SKIPPED,
                message="Repositorio archivado",
            )

        # Repo vacío
        try:
            if not repo.default_branch:
                return SyncResult(
                    repo_name=repo.name,
                    status=SyncStatus.SKIPPED,
                    message="Repositorio sin branch por defecto",
                )
        except Exception:
            return SyncResult(
                repo_name=repo.name,
                status=SyncStatus.SKIPPED,
                message="Repositorio vacío (sin commits)",
            )

        # PR existente (idempotencia)
        existing_prs = self._client.get_open_prs_with_prefix(repo, self.BRANCH_PREFIX)
        if existing_prs:
            return SyncResult(
                repo_name=repo.name,
                status=SyncStatus.SKIPPED,
                message=f"PR de sync existente: {existing_prs[0]}",
            )

        return None

    def _get_required_changes(self, repo: Repository) -> list[FileChange]:
        """Obtiene los cambios necesarios para el repo."""
        changes: list[FileChange] = []

        for filename, new_content in self._source_workflows.items():
            file_path = f"{self.WORKFLOWS_PATH}/{filename}"

            result = self._client.get_file_content(repo, file_path)

            if result is None:
                # Archivo no existe, crear
                changes.append(FileChange(filename=filename, content=new_content))
                logger.debug("Archivo %s será creado en %s", filename, repo.name)
            else:
                existing_content, sha = result
                if existing_content.strip() != new_content.strip():
                    changes.append(
                        FileChange(
                            filename=filename, content=new_content, existing_sha=sha
                        )
                    )
                    logger.debug(
                        "Archivo %s necesita actualización en %s", filename, repo.name
                    )

        return changes

    def _create_sync_pr(
        self, repo: Repository, changes: list[FileChange]
    ) -> SyncResult:
        """Crea un PR con los cambios de workflows."""
        branch_name = None
        files_updated: list[str] = []
        files_failed: list[str] = []

        try:
            # Crear branch único
            base_sha = self._client.get_base_sha(repo, repo.default_branch)
            branch_name = self._generate_unique_branch_name(repo)
            self._client.create_branch(repo, branch_name, base_sha)

            # Aplicar cambios
            for change in changes:
                try:
                    file_path = f"{self.WORKFLOWS_PATH}/{change.filename}"
                    message = (
                        f"chore: {'sync' if change.existing_sha else 'add'} "
                        f"workflow {change.filename}"
                    )

                    self._client.create_or_update_file(
                        repo=repo,
                        path=file_path,
                        content=change.content,
                        message=message,
                        branch=branch_name,
                        sha=change.existing_sha,
                    )
                    files_updated.append(change.filename)
                    logger.debug(
                        "Archivo %s actualizado en %s", change.filename, repo.name
                    )

                except Exception as e:
                    logger.error(
                        "Error actualizando %s en %s: %s",
                        change.filename,
                        repo.name,
                        str(e),
                    )
                    files_failed.append(change.filename)

            # Si ningún archivo se actualizó, cleanup y error
            if not files_updated:
                self._client.delete_branch(repo, branch_name)
                return SyncResult(
                    repo_name=repo.name,
                    status=SyncStatus.ERROR,
                    message="Todas las actualizaciones fallaron",
                    files_failed=files_failed,
                    branch_created=branch_name,
                )

            # Crear PR
            pr_body = PRBodyGenerator.generate(
                org=self._config.org,
                source_repo=self._config.source_repo,
                files_updated=files_updated,
                files_failed=files_failed,
            )

            pr_url = self._client.create_pull_request(
                repo=repo,
                title="chore: sync GitHub Actions workflows",
                body=pr_body,
                head=branch_name,
                base=repo.default_branch,
            )

            return SyncResult(
                repo_name=repo.name,
                status=SyncStatus.SUCCESS,
                pr_url=pr_url,
                message=f"{len(files_updated)} archivo(s) actualizados",
                files_updated=files_updated,
                files_failed=files_failed,
                branch_created=branch_name,
            )

        except Exception as e:
            if branch_name:
                self._client.delete_branch(repo, branch_name)

            logger.exception("Error creando PR para %s", repo.name)
            return SyncResult(
                repo_name=repo.name,
                status=SyncStatus.ERROR,
                message=f"Error: {str(e)}",
                files_updated=files_updated,
                files_failed=files_failed,
                branch_created=branch_name,
            )

    def _generate_unique_branch_name(self, repo: Repository) -> str:
        """Genera un nombre de branch único."""
        timestamp = int(time.time() * 1000)
        branch_name = f"{self.BRANCH_PREFIX}-{timestamp}"

        if self._client.branch_exists(repo, branch_name):
            branch_name = f"{branch_name}-{random.randint(1000, 9999)}"
            logger.debug("Branch existía, usando %s", branch_name)

        return branch_name

    def _log_result(self, result: SyncResult) -> None:
        """Registra el resultado de sincronización."""
        duration_str = (
            f" ({result.duration_seconds:.1f}s)"
            if result.duration_seconds > 0
            else ""
        )

        if result.status == SyncStatus.SUCCESS:
            logger.info(
                "[%s] PR creado: %s%s",
                result.repo_name,
                result.pr_url,
                duration_str,
            )
            if result.files_failed:
                logger.warning(
                    "[%s] (parcial: %d archivos fallaron)",
                    result.repo_name,
                    len(result.files_failed),
                )
        elif result.status == SyncStatus.NO_CHANGES:
            logger.info(
                "[%s] Sin cambios necesarios%s", result.repo_name, duration_str
            )
        elif result.status == SyncStatus.SKIPPED:
            logger.info("[%s] Saltado: %s", result.repo_name, result.message)
        elif result.status == SyncStatus.ERROR:
            logger.error(
                "[%s] Error: %s%s", result.repo_name, result.message, duration_str
            )
