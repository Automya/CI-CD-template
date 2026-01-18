"""
Excepciones personalizadas para el sincronizador de workflows.

Principio SOLID: Single Responsibility
- Solo contiene definiciones de excepciones.
"""


class WorkflowSyncError(Exception):
    """Excepción base para errores de sincronización."""

    pass


class SourceRepoError(WorkflowSyncError):
    """Error al acceder al repositorio fuente."""

    pass


class ValidationError(WorkflowSyncError):
    """Error de validación de inputs."""

    pass


class RateLimitError(WorkflowSyncError):
    """Error cuando se excede el rate limit de la API."""

    pass


class AuthenticationError(WorkflowSyncError):
    """Error de autenticación con GitHub."""

    pass


class RepositoryAccessError(WorkflowSyncError):
    """Error al acceder a un repositorio específico."""

    pass
