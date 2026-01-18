"""
Validador de inputs para el sincronizador de workflows.

Principio SOLID: Single Responsibility
- Solo se encarga de validar inputs.

Principio SOLID: Open/Closed
- Nuevos patrones de validación se pueden agregar sin modificar código existente.
"""

from __future__ import annotations

import re
import sys
from abc import ABC, abstractmethod
from pathlib import Path

# Agregar directorio padre al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from exceptions import ValidationError


class ValidationPattern(ABC):
    """Clase base abstracta para patrones de validación.

    Principio SOLID: Open/Closed
    - Permite extender validaciones sin modificar código existente.
    """

    @property
    @abstractmethod
    def pattern(self) -> re.Pattern[str]:
        """Retorna el patrón de validación."""
        pass

    @property
    @abstractmethod
    def field_name(self) -> str:
        """Retorna el nombre del campo para mensajes de error."""
        pass

    @property
    def error_message(self) -> str:
        """Mensaje de error personalizado."""
        return f"Must match pattern: {self.pattern.pattern}"

    def validate(self, value: str) -> str:
        """Valida el valor contra el patrón.

        Args:
            value: Valor a validar.

        Returns:
            El valor validado.

        Raises:
            ValidationError: Si el valor no coincide con el patrón.
        """
        if not self.pattern.match(value):
            raise ValidationError(
                f"Invalid {self.field_name}: '{value}'. {self.error_message}"
            )
        return value


class OrganizationNamePattern(ValidationPattern):
    """Patrón para nombres de organización/repositorio de GitHub."""

    _pattern = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,99}$")

    @property
    def pattern(self) -> re.Pattern[str]:
        return self._pattern

    @property
    def field_name(self) -> str:
        return "organization name"


class RepositoryNamePattern(ValidationPattern):
    """Patrón para nombres de repositorio de GitHub."""

    _pattern = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,99}$")

    @property
    def pattern(self) -> re.Pattern[str]:
        return self._pattern

    @property
    def field_name(self) -> str:
        return "repository name"


class TopicPattern(ValidationPattern):
    """Patrón para topics de GitHub (lowercase, alfanumérico, guiones)."""

    _pattern = re.compile(r"^[a-z0-9][a-z0-9-]{0,49}$")

    @property
    def pattern(self) -> re.Pattern[str]:
        return self._pattern

    @property
    def field_name(self) -> str:
        return "topic"


class WorkflowFilePattern(ValidationPattern):
    """Patrón para nombres de archivos de workflow."""

    _pattern = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*\.(yml|yaml)$")

    @property
    def pattern(self) -> re.Pattern[str]:
        return self._pattern

    @property
    def field_name(self) -> str:
        return "workflow file name"

    @property
    def error_message(self) -> str:
        return "Must be alphanumeric with .yml or .yaml extension"


class InputValidator:
    """Validador de inputs del usuario.

    Principio SOLID: Single Responsibility
    - Solo se encarga de validar inputs.

    Principio SOLID: Dependency Inversion
    - Depende de abstracciones (ValidationPattern), no de implementaciones.
    """

    # Patrones predefinidos (singleton-like)
    _org_pattern = OrganizationNamePattern()
    _repo_pattern = RepositoryNamePattern()
    _topic_pattern = TopicPattern()
    _workflow_pattern = WorkflowFilePattern()

    @classmethod
    def validate_organization(cls, value: str) -> str:
        """Valida nombre de organización."""
        return cls._org_pattern.validate(value)

    @classmethod
    def validate_repository(cls, value: str) -> str:
        """Valida nombre de repositorio."""
        return cls._repo_pattern.validate(value)

    @classmethod
    def validate_topic(cls, value: str) -> str:
        """Valida topic (convierte a lowercase primero)."""
        return cls._topic_pattern.validate(value.lower())

    @classmethod
    def validate_workflow_file(cls, filename: str) -> str:
        """Valida nombre de archivo de workflow.

        Args:
            filename: Nombre del archivo.

        Returns:
            El nombre validado.

        Raises:
            ValidationError: Si el nombre es inválido o hay intento de path traversal.
        """
        # Prevenir path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            raise ValidationError(
                f"Invalid file name (path traversal attempt): '{filename}'"
            )
        return cls._workflow_pattern.validate(filename)

    @classmethod
    def validate_workflow_files(cls, files: list[str] | None) -> list[str]:
        """Valida una lista de nombres de archivos de workflow.

        Args:
            files: Lista de nombres de archivo.

        Returns:
            Lista de nombres validados (vacía si files es None).

        Raises:
            ValidationError: Si algún nombre es inválido.
        """
        if not files:
            return []

        return [cls.validate_workflow_file(f) for f in files]

    @classmethod
    def validate_token(cls, token: str | None) -> str:
        """Valida el token de GitHub.

        Args:
            token: Token de GitHub.

        Returns:
            El token validado.

        Raises:
            ValidationError: Si el token es inválido.
        """
        if not token:
            raise ValidationError("GitHub token is required")

        if len(token) < 20:
            raise ValidationError("GitHub token appears to be invalid (too short)")

        return token
