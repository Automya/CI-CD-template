# Workflow Sync Tool

Herramienta para sincronizar archivos de GitHub Actions workflows desde un repositorio fuente hacia todos los repositorios de una organización que tengan un topic específico.

## Arquitectura (SOLID)

```
workflow_sync/
├── __init__.py              # Exports públicos
├── __main__.py              # Entry point: python -m workflow_sync
├── cli.py                   # CLI (Single Responsibility)
├── models.py                # Dataclasses, Enums (Single Responsibility)
├── exceptions.py            # Excepciones personalizadas
├── validators/
│   ├── __init__.py
│   └── input_validator.py   # Validación (Single Responsibility, Open/Closed)
├── clients/
│   ├── __init__.py
│   └── github_client.py     # Cliente GitHub con interfaz abstracta (Dependency Inversion)
└── services/
    ├── __init__.py
    └── sync_service.py      # Servicio principal con estrategias (Open/Closed)
```


## Instalación

```bash
cd tools/workflow-sync
pip install -r requirements.txt
```

## Configuración

Exporta tu token de GitHub con permisos `repo` y `read:org`:

```bash
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
```

## Uso

### Método 1: Script directo

```bash
python sync_workflows.py \
    --org Automya \
    --topic microservice \
    --source-repo api-gateway
```

### Método 2: Como módulo Python

```bash
python -m workflow_sync \
    --org Automya \
    --topic microservice \
    --source-repo api-gateway
```

### Sincronizar solo archivos específicos

```bash
python sync_workflows.py \
    --org Automya \
    --topic microservice \
    --source-repo api-gateway \
    --files build.yml deploy.yml sync-config.yml
```

### Modo dry-run (ver qué cambiaría)

```bash
python sync_workflows.py \
    --org Automya \
    --topic microservice \
    --source-repo api-gateway \
    --dry-run
```

### Ejecución paralela

```bash
python sync_workflows.py \
    --org Automya \
    --topic microservice \
    --source-repo api-gateway \
    --parallel \
    --max-workers 8
```

### Verbose (debug)

```bash
python sync_workflows.py \
    --org Automya \
    --topic microservice \
    --source-repo api-gateway \
    -v
```

## Argumentos

| Argumento | Requerido | Descripción |
|-----------|-----------|-------------|
| `--org` | Sí | Nombre de la organización de GitHub |
| `--topic` | Sí | Topic para filtrar repositorios destino |
| `--source-repo` | Sí | Nombre del repositorio fuente (sin organización) |
| `--files` | No | Lista de archivos específicos a sincronizar |
| `--dry-run` | No | Mostrar cambios sin ejecutarlos |
| `--parallel` | No | Ejecutar sincronización en paralelo |
| `--max-workers` | No | Workers para ejecución paralela (default: 4) |
| `--timeout` | No | Timeout API en segundos (default: 30) |
| `--verbose, -v` | No | Habilitar modo debug |

## Uso Programático

```python
from workflow_sync import SyncConfig, WorkflowSyncService
from workflow_sync.clients import GitHubClient

# Configuración
config = SyncConfig(
    token="ghp_xxx",
    org="Automya",
    topic="microservice",
    source_repo="api-gateway",
    dry_run=False,
)

# Inyección de dependencias
client = GitHubClient(token=config.token, timeout=30)
service = WorkflowSyncService(client=client, config=config)

# Ejecutar
results = service.run(parallel=False)

# Procesar resultados
for result in results:
    print(f"{result.repo_name}: {result.status.value}")
```

## Testing

La arquitectura permite fácil mocking:

```python
from unittest.mock import MagicMock
from workflow_sync.clients.github_client import IGitHubClient
from workflow_sync.services.sync_service import WorkflowSyncService

# Mock del cliente
mock_client = MagicMock(spec=IGitHubClient)
mock_client.search_repositories_by_topic.return_value = []

# Servicio con mock inyectado
service = WorkflowSyncService(client=mock_client, config=config)
```

## Comportamiento

1. **Busca** repos en la organización con el topic especificado
2. **Filtra** repos archivados, vacíos y sin permisos push
3. **Compara** workflows del repo fuente con cada repo destino
4. **Crea PR** en cada repo que tenga diferencias
5. **Salta** repos con PRs de sync existentes (idempotencia)
6. **Limpia** branches huérfanos si falla la creación del PR

## Seguridad

- Token solo via `GITHUB_TOKEN` (no CLI args)
- Validación de inputs contra patrones regex
- Prevención de path traversal
- Rate limiting con backoff exponencial
- Reintentos automáticos para errores transitorios

## Códigos de salida

| Código | Significado |
|--------|-------------|
| 0 | Éxito |
| 1 | Error general |
| 2 | Error de validación |
| 130 | Interrumpido (Ctrl+C) |
