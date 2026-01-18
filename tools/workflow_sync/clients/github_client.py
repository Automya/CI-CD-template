"""
Cliente de GitHub con abstracción para inyección de dependencias.

Principio SOLID: Dependency Inversion
- Define una interfaz abstracta (IGitHubClient) que el servicio usa.
- La implementación concreta (GitHubClient) puede ser reemplazada (ej: para tests).

Principio SOLID: Single Responsibility
- Solo se encarga de la comunicación con la API de GitHub.
"""

from __future__ import annotations

import base64
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from github import Github, GithubException, RateLimitExceededException

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from exceptions import (
    AuthenticationError,
    RateLimitError,
    RepositoryAccessError,
    SourceRepoError,
)
from models import FileChange, RepositoryInfo

if TYPE_CHECKING:
    from github.Repository import Repository

logger = logging.getLogger(__name__)


class IGitHubClient(ABC):
    """Interfaz abstracta para el cliente de GitHub.

    Principio SOLID: Interface Segregation
    - Define solo los métodos necesarios para la sincronización.

    Principio SOLID: Dependency Inversion
    - Los servicios dependen de esta abstracción, no de la implementación.
    """

    @abstractmethod
    def get_repository(self, full_name: str) -> Repository:
        """Obtiene un repositorio por nombre completo."""
        pass

    @abstractmethod
    def search_repositories_by_topic(
        self, org: str, topic: str
    ) -> list[RepositoryInfo]:
        """Busca repositorios por topic en una organización."""
        pass

    @abstractmethod
    def get_file_content(self, repo: Repository, path: str) -> tuple[str, str] | None:
        """Obtiene contenido y SHA de un archivo. Retorna None si no existe."""
        pass

    @abstractmethod
    def get_workflow_files(self, repo: Repository, path: str) -> dict[str, str]:
        """Obtiene todos los archivos de workflow de un repositorio."""
        pass

    @abstractmethod
    def create_branch(self, repo: Repository, branch_name: str, base_sha: str) -> None:
        """Crea una nueva rama."""
        pass

    @abstractmethod
    def delete_branch(self, repo: Repository, branch_name: str) -> None:
        """Elimina una rama."""
        pass

    @abstractmethod
    def create_or_update_file(
        self,
        repo: Repository,
        path: str,
        content: str,
        message: str,
        branch: str,
        sha: str | None = None,
    ) -> None:
        """Crea o actualiza un archivo."""
        pass

    @abstractmethod
    def create_pull_request(
        self,
        repo: Repository,
        title: str,
        body: str,
        head: str,
        base: str,
    ) -> tuple[str, int]:
        """Crea un PR y retorna (URL, número del PR)."""
        pass

    @abstractmethod
    def get_open_prs_with_prefix(
        self, repo: Repository, branch_prefix: str
    ) -> list[str]:
        """Obtiene URLs de PRs abiertos cuyo branch empieza con el prefijo."""
        pass

    @abstractmethod
    def check_rate_limit(self, is_search: bool = False) -> None:
        """Verifica y maneja el rate limit."""
        pass

    @abstractmethod
    def has_workflows_folder(self, repo: Repository, path: str) -> bool:
        """Verifica si el repositorio tiene la carpeta de workflows."""
        pass

    @abstractmethod
    def get_workflow_filenames(self, repo: Repository, path: str) -> list[str]:
        """Obtiene la lista de nombres de archivos workflow en el repositorio."""
        pass

    @abstractmethod
    def delete_file(
        self,
        repo: Repository,
        path: str,
        message: str,
        branch: str,
        sha: str,
    ) -> None:
        """Elimina un archivo del repositorio."""
        pass

    @abstractmethod
    def merge_pull_request(
        self,
        repo: Repository,
        pr_number: int,
        merge_method: str = "squash",
    ) -> bool:
        """Mergea un PR. Retorna True si tuvo éxito."""
        pass

    @abstractmethod
    def update_branch(
        self,
        repo: Repository,
        pr_number: int,
    ) -> bool:
        """Actualiza el branch del PR con los cambios de base. Retorna True si tuvo éxito."""
        pass


class GitHubClient(IGitHubClient):
    """Implementación concreta del cliente de GitHub.

    Incluye:
    - Reintentos con backoff exponencial
    - Manejo de rate limiting
    - Logging estructurado
    """

    WORKFLOWS_PATH = ".github/workflows"
    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 2
    RATE_LIMIT_THRESHOLD = 50
    SEARCH_RATE_LIMIT_THRESHOLD = 5
    MAX_RATE_LIMIT_WAIT = 300

    def __init__(self, token: str, timeout: int = 30) -> None:
        """Inicializa el cliente.

        Args:
            token: Token de autenticación de GitHub.
            timeout: Timeout para llamadas API en segundos.
        """
        self._github = Github(token, timeout=timeout, retry=3)
        self._timeout = timeout

    def get_repository(self, full_name: str) -> Repository:
        """Obtiene un repositorio por nombre completo."""
        try:
            return self._api_call_with_retry(
                self._github.get_repo,
                full_name,
                operation_name=f"get_repo({full_name})",
            )
        except GithubException as e:
            if e.status == 404:
                raise SourceRepoError(f"Repository not found: {full_name}") from e
            if e.status == 401:
                raise AuthenticationError("Invalid GitHub token") from e
            raise RepositoryAccessError(
                f"Error accessing repository {full_name}: {self._extract_error(e)}"
            ) from e

    def search_repositories_by_topic(
        self, org: str, topic: str
    ) -> list[RepositoryInfo]:
        """Busca repositorios por topic en una organización."""
        repos = []
        try:
            query = f"org:{org} topic:{topic}"
            search_results = self._api_call_with_retry(
                self._github.search_repositories,
                query=query,
                operation_name="search_repositories",
            )

            for repo in search_results:
                if repo.archived:
                    logger.debug("Saltando repo archivado: %s", repo.name)
                    continue

                has_push = True
                try:
                    if repo.permissions and not repo.permissions.push:
                        logger.debug("Saltando repo sin permisos push: %s", repo.name)
                        continue
                except Exception:
                    logger.debug(
                        "No se pudieron verificar permisos para %s", repo.name
                    )

                repos.append(
                    RepositoryInfo(
                        name=repo.name,
                        full_name=repo.full_name,
                        default_branch=repo.default_branch or "main",
                        archived=repo.archived,
                        has_push_permission=has_push,
                    )
                )

            return repos

        except GithubException as e:
            logger.error("Error buscando repos: %s", self._extract_error(e))
            return []

    def get_file_content(self, repo: Repository, path: str) -> tuple[str, str] | None:
        """Obtiene contenido y SHA de un archivo."""
        try:
            content = self._api_call_with_retry(
                repo.get_contents,
                path,
                operation_name=f"get_contents({path})",
            )
            if isinstance(content, list):
                return None

            decoded = base64.b64decode(content.content).decode("utf-8")
            return decoded, content.sha

        except GithubException as e:
            if e.status == 404:
                return None
            raise

    def get_workflow_files(self, repo: Repository, path: str) -> dict[str, str]:
        """Obtiene todos los archivos de workflow de un repositorio."""
        workflows: dict[str, str] = {}

        try:
            contents = self._api_call_with_retry(
                repo.get_contents,
                path,
                operation_name=f"get_contents({path})",
            )

            if not isinstance(contents, list):
                contents = [contents]

            for content in contents:
                if content.type == "file" and content.name.endswith((".yml", ".yaml")):
                    file_content = base64.b64decode(content.content).decode("utf-8")
                    workflows[content.name] = file_content

            return workflows

        except GithubException as e:
            if e.status == 404:
                raise SourceRepoError(f"Workflows path not found: {path}") from e
            raise

    def create_branch(self, repo: Repository, branch_name: str, base_sha: str) -> None:
        """Crea una nueva rama."""
        self._api_call_with_retry(
            repo.create_git_ref,
            ref=f"refs/heads/{branch_name}",
            sha=base_sha,
            operation_name=f"create_branch({branch_name})",
        )
        logger.debug("Branch %s creado en %s", branch_name, repo.name)

    def delete_branch(self, repo: Repository, branch_name: str) -> None:
        """Elimina una rama."""
        try:
            ref = repo.get_git_ref(f"heads/{branch_name}")
            ref.delete()
            logger.info("Branch eliminado: %s en %s", branch_name, repo.name)
        except GithubException as e:
            logger.warning(
                "No se pudo eliminar branch %s en %s: %s",
                branch_name,
                repo.name,
                str(e),
            )

    def create_or_update_file(
        self,
        repo: Repository,
        path: str,
        content: str,
        message: str,
        branch: str,
        sha: str | None = None,
    ) -> None:
        """Crea o actualiza un archivo."""
        if sha:
            self._api_call_with_retry(
                repo.update_file,
                path=path,
                message=message,
                content=content,
                sha=sha,
                branch=branch,
                operation_name=f"update_file({path})",
            )
        else:
            self._api_call_with_retry(
                repo.create_file,
                path=path,
                message=message,
                content=content,
                branch=branch,
                operation_name=f"create_file({path})",
            )

    def create_pull_request(
        self,
        repo: Repository,
        title: str,
        body: str,
        head: str,
        base: str,
    ) -> tuple[str, int]:
        """Crea un PR y retorna (URL, número del PR)."""
        pr = self._api_call_with_retry(
            repo.create_pull,
            title=title,
            body=body,
            head=head,
            base=base,
            operation_name="create_pull",
        )
        return pr.html_url, pr.number

    def get_open_prs_with_prefix(
        self, repo: Repository, branch_prefix: str
    ) -> list[str]:
        """Obtiene URLs de PRs abiertos cuyo branch empieza con el prefijo."""
        urls = []
        try:
            pulls = repo.get_pulls(state="open")
            for pr in pulls:
                if pr.head.ref.startswith(branch_prefix):
                    urls.append(pr.html_url)
        except GithubException as e:
            logger.debug(
                "No se pudieron verificar PRs existentes para %s: %s",
                repo.name,
                str(e),
            )
        return urls

    def check_rate_limit(self, is_search: bool = False) -> None:
        """Verifica y maneja el rate limit."""
        try:
            rate_limit = self._github.get_rate_limit()

            # PyGithub >= 2.x usa rate.core, versiones anteriores usan core directamente
            core_limit = getattr(rate_limit, "core", None) or getattr(rate_limit.rate, "core", rate_limit.rate)
            search_limit = getattr(rate_limit, "search", None) or core_limit

            if is_search:
                remaining = search_limit.remaining
                reset_time = search_limit.reset
                threshold = self.SEARCH_RATE_LIMIT_THRESHOLD
                limit_type = "Search API"
            else:
                remaining = core_limit.remaining
                reset_time = core_limit.reset
                threshold = self.RATE_LIMIT_THRESHOLD
                limit_type = "Core API"

            logger.debug(
                "Rate limit check - %s: %d remaining, resets at %s",
                limit_type,
                remaining,
                reset_time,
            )

            if remaining < threshold:
                self._wait_for_rate_limit_reset(reset_time, remaining, limit_type)

        except GithubException as e:
            logger.warning("No se pudo verificar rate limit: %s", str(e))

    def get_base_sha(self, repo: Repository, branch: str) -> str:
        """Obtiene el SHA del HEAD de una rama."""
        ref = self._api_call_with_retry(
            repo.get_git_ref,
            f"heads/{branch}",
            operation_name=f"get_ref({branch})",
        )
        return ref.object.sha

    def branch_exists(self, repo: Repository, branch_name: str) -> bool:
        """Verifica si una rama existe."""
        try:
            repo.get_git_ref(f"heads/{branch_name}")
            return True
        except GithubException as e:
            if e.status == 404:
                return False
            raise

    def has_workflows_folder(self, repo: Repository, path: str) -> bool:
        """Verifica si el repositorio tiene la carpeta de workflows."""
        try:
            self._api_call_with_retry(
                repo.get_contents,
                path,
                operation_name=f"check_folder({path})",
            )
            return True
        except GithubException as e:
            if e.status == 404:
                return False
            raise

    def get_workflow_filenames(self, repo: Repository, path: str) -> list[str]:
        """Obtiene la lista de nombres de archivos workflow en el repositorio."""
        filenames: list[str] = []
        try:
            contents = self._api_call_with_retry(
                repo.get_contents,
                path,
                operation_name=f"list_workflows({path})",
            )

            if not isinstance(contents, list):
                contents = [contents]

            for content in contents:
                if content.type == "file" and content.name.endswith((".yml", ".yaml")):
                    filenames.append(content.name)

            return filenames

        except GithubException as e:
            if e.status == 404:
                return []
            raise

    def delete_file(
        self,
        repo: Repository,
        path: str,
        message: str,
        branch: str,
        sha: str,
    ) -> None:
        """Elimina un archivo del repositorio."""
        self._api_call_with_retry(
            repo.delete_file,
            path=path,
            message=message,
            sha=sha,
            branch=branch,
            operation_name=f"delete_file({path})",
        )

    def merge_pull_request(
        self,
        repo: Repository,
        pr_number: int,
        merge_method: str = "squash",
        max_retries: int = 3,
    ) -> bool:
        """Mergea un PR con retry y update branch si es necesario.

        Si el merge falla porque el branch está desactualizado,
        intenta actualizar el branch y reintentar el merge.
        """
        pr = repo.get_pull(pr_number)

        for attempt in range(max_retries):
            try:
                # Verificar si es mergeable
                if pr.mergeable is False:
                    logger.warning(
                        "PR #%d no es mergeable (posible conflicto)",
                        pr_number,
                    )
                    return False

                # Intentar merge
                result = pr.merge(merge_method=merge_method)
                return result.merged

            except GithubException as e:
                error_msg = self._extract_error(e).lower()

                # Detectar si el branch está desactualizado
                is_behind = any(word in error_msg for word in [
                    "head branch was modified",
                    "not up to date",
                    "behind",
                    "out-of-date",
                ])

                if is_behind and attempt < max_retries - 1:
                    logger.info(
                        "PR #%d está desactualizado, actualizando branch (intento %d/%d)",
                        pr_number,
                        attempt + 1,
                        max_retries,
                    )

                    # Intentar actualizar branch
                    if self.update_branch(repo, pr_number):
                        # Esperar un momento y refrescar PR
                        time.sleep(2)
                        pr = repo.get_pull(pr_number)
                        continue
                    else:
                        logger.warning("No se pudo actualizar el branch")
                        return False
                else:
                    logger.warning(
                        "No se pudo mergear PR #%d: %s",
                        pr_number,
                        self._extract_error(e),
                    )
                    return False

        return False

    def update_branch(
        self,
        repo: Repository,
        pr_number: int,
    ) -> bool:
        """Actualiza el branch del PR con los cambios de base."""
        try:
            pr = repo.get_pull(pr_number)
            # PyGithub usa update_branch para hacer el "Update branch" de GitHub
            result = pr.update_branch()
            if result:
                logger.debug("Branch del PR #%d actualizado exitosamente", pr_number)
                return True
            return False
        except GithubException as e:
            logger.warning(
                "No se pudo actualizar branch del PR #%d: %s",
                pr_number,
                self._extract_error(e),
            )
            return False

    def handle_post_operation_rate_limit(self) -> None:
        """Maneja el rate limit después de cada operación."""
        try:
            rate_limit = self._github.get_rate_limit()
            # PyGithub >= 2.x usa rate.core, versiones anteriores usan core directamente
            core_limit = getattr(rate_limit, "core", None) or getattr(rate_limit.rate, "core", rate_limit.rate)
            remaining = core_limit.remaining
            reset_time = core_limit.reset

            if remaining < 10:
                self._wait_for_rate_limit_reset(reset_time, remaining, "Core API")
            elif remaining < self.RATE_LIMIT_THRESHOLD:
                time.sleep(2)
            else:
                time.sleep(1)
        except Exception as e:
            logger.debug("Rate limit check failed: %s, using conservative delay", str(e))
            time.sleep(2)

    def _wait_for_rate_limit_reset(
        self, reset_time: datetime, remaining: int, limit_type: str
    ) -> None:
        """Espera hasta que el rate limit se resetee."""
        now = datetime.now(timezone.utc)
        if reset_time.tzinfo is None:
            reset_time = reset_time.replace(tzinfo=timezone.utc)
        wait_seconds = (reset_time - now).total_seconds() + 5

        if wait_seconds > 0:
            wait_seconds = min(wait_seconds, self.MAX_RATE_LIMIT_WAIT)
            logger.warning(
                "Rate limit bajo (%d restantes para %s). Esperando %.0f segundos.",
                remaining,
                limit_type,
                wait_seconds,
            )
            time.sleep(wait_seconds)

    def _api_call_with_retry(
        self, operation, *args, operation_name: str = "API call", **kwargs
    ):
        """Ejecuta una llamada API con reintentos y backoff exponencial."""
        last_exception: Exception | None = None

        for attempt in range(self.MAX_RETRIES):
            try:
                return operation(*args, **kwargs)

            except RateLimitExceededException as e:
                wait_time = self.RETRY_DELAY_BASE ** (attempt + 1)
                logger.warning(
                    "%s: Rate limited. Retrying in %ds (attempt %d/%d)",
                    operation_name,
                    wait_time,
                    attempt + 1,
                    self.MAX_RETRIES,
                )
                time.sleep(wait_time)
                last_exception = e

            except GithubException as e:
                if e.status in (500, 502, 503, 504):
                    wait_time = self.RETRY_DELAY_BASE ** (attempt + 1)
                    logger.warning(
                        "%s: Server error %d. Retrying in %ds (attempt %d/%d)",
                        operation_name,
                        e.status,
                        wait_time,
                        attempt + 1,
                        self.MAX_RETRIES,
                    )
                    time.sleep(wait_time)
                    last_exception = e

                elif (
                    e.status == 403
                    and hasattr(e, "data")
                    and e.data
                    and "secondary rate limit" in str(e.data).lower()
                ):
                    wait_time = min(60 * (2**attempt), self.MAX_RATE_LIMIT_WAIT)
                    logger.warning(
                        "%s: Secondary rate limit. Waiting %ds (attempt %d/%d)",
                        operation_name,
                        wait_time,
                        attempt + 1,
                        self.MAX_RETRIES,
                    )
                    time.sleep(wait_time)
                    last_exception = e

                else:
                    raise

            except Exception as e:
                wait_time = self.RETRY_DELAY_BASE ** (attempt + 1)
                logger.warning(
                    "%s: Network error '%s'. Retrying in %ds (attempt %d/%d)",
                    operation_name,
                    str(e),
                    wait_time,
                    attempt + 1,
                    self.MAX_RETRIES,
                )
                time.sleep(wait_time)
                last_exception = e

        logger.error("%s: All %d retries exhausted", operation_name, self.MAX_RETRIES)
        if last_exception:
            raise last_exception
        raise RuntimeError(f"{operation_name} failed after {self.MAX_RETRIES} retries")

    @staticmethod
    def _extract_error(exception: GithubException) -> str:
        """Extrae mensaje de error de una GithubException."""
        if hasattr(exception, "data") and isinstance(exception.data, dict):
            return exception.data.get("message", str(exception))
        return str(exception)
