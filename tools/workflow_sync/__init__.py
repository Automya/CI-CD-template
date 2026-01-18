"""
Workflow Sync - Sincronizador de GitHub Actions workflows.

Este paquete proporciona herramientas para sincronizar workflows de GitHub Actions
desde un repositorio fuente hacia múltiples repositorios destino filtrados por topic.
"""

import sys
from pathlib import Path

# Agregar directorio actual al path para imports
sys.path.insert(0, str(Path(__file__).parent))

from models import SyncConfig, SyncResult, SyncStatus
from services.sync_service import WorkflowSyncService

__version__ = "1.0.0"
__all__ = ["SyncConfig", "SyncResult", "SyncStatus", "WorkflowSyncService"]
