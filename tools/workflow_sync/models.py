"""
Modelos de datos para el sincronizador de workflows.

Este módulo contiene todas las estructuras de datos (dataclasses),
enumeraciones y excepciones personalizadas del paquete.

Principio SOLID: Single Responsibility
- Solo contiene definiciones de datos, sin lógica de negocio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SyncStatus(Enum):
    """Estados posibles de sincronización."""

    SUCCESS = "success"
    SKIPPED = "skipped"
    ERROR = "error"
    NO_CHANGES = "no_changes"


@dataclass
class SyncResult:
    """Resultado de sincronización para un repositorio.

    Attributes:
        repo_name: Nombre del repositorio procesado.
        status: Estado de la sincronización.
        pr_url: URL del PR creado (si aplica).
        message: Mensaje descriptivo del resultado.
        files_updated: Lista de archivos actualizados exitosamente.
        files_failed: Lista de archivos que fallaron.
        branch_created: Nombre del branch creado (para cleanup).
        duration_seconds: Duración de la operación en segundos.
    """

    repo_name: str
    status: SyncStatus
    pr_url: str | None = None
    message: str = ""
    files_updated: list[str] = field(default_factory=list)
    files_failed: list[str] = field(default_factory=list)
    branch_created: str | None = None
    duration_seconds: float = 0.0


@dataclass
class SyncConfig:
    """Configuración para la sincronización de workflows.

    Attributes:
        token: Token de autenticación de GitHub.
        org: Nombre de la organización.
        topic: Topic para filtrar repositorios.
        source_repo: Nombre del repositorio fuente.
        dry_run: Si es True, no realiza cambios.
        files_filter: Lista de archivos específicos a sincronizar.
        max_workers: Número máximo de workers para procesamiento paralelo.
        timeout: Timeout para llamadas API en segundos.
    """

    token: str
    org: str
    topic: str
    source_repo: str
    dry_run: bool = False
    files_filter: list[str] = field(default_factory=list)
    max_workers: int = 4
    timeout: int = 30


@dataclass
class FileChange:
    """Representa un cambio de archivo a sincronizar.

    Attributes:
        filename: Nombre del archivo.
        content: Contenido nuevo del archivo.
        existing_sha: SHA del archivo existente (None si es nuevo).
    """

    filename: str
    content: str
    existing_sha: str | None = None

    @property
    def is_new(self) -> bool:
        """Indica si el archivo es nuevo (no existe en destino)."""
        return self.existing_sha is None


@dataclass
class RepositoryInfo:
    """Información básica de un repositorio.

    Attributes:
        name: Nombre del repositorio.
        full_name: Nombre completo (org/repo).
        default_branch: Branch por defecto.
        archived: Si el repositorio está archivado.
        has_push_permission: Si tenemos permisos de push.
    """

    name: str
    full_name: str
    default_branch: str
    archived: bool = False
    has_push_permission: bool = True
