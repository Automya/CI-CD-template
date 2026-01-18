# Workflow Sync Tool

Herramienta para sincronizar archivos de GitHub Actions workflows desde un repositorio fuente hacia todos los repositorios de una organización que tengan un topic específico.

## Instalación

```bash
cd tools/workflow_sync
pip install .
```

## 🖥️ Aplicación Interactiva

### Ejecutar con doble clic (macOS)

```
WorkflowSync.command
```

### Ejecutar desde terminal

```bash
cd tools/workflow_sync
python3 interactive.py
```

### Características

- 🎨 Interfaz de terminal con colores
- 📝 Prompts interactivos para introducir datos
- ✅ Validación en tiempo real
- 📊 Resumen de configuración antes de ejecutar
- 🔍 Modo dry-run
- ⚡ Ejecución paralela
- 🔐 Persistencia de token (guardado en `~/.workflow-sync-config`)
- 🔑 Opción para cambiar/rotar token

## ⌨️ Línea de Comandos (CLI)

```bash
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"

# Sincronizar todos los workflows
workflow-sync --org Automya --topic microservice --source-repo api-gateway

# Solo archivos específicos
workflow-sync --org Automya --topic microservice --source-repo api-gateway \
    --files build.yml deploy.yml

# Dry-run
workflow-sync --org Automya --topic microservice --source-repo api-gateway --dry-run

# Paralelo
workflow-sync --org Automya --topic microservice --source-repo api-gateway --parallel
```

## Argumentos CLI

| Argumento | Requerido | Descripción |
|-----------|-----------|-------------|
| `--org` | Sí | Organización de GitHub |
| `--topic` | Sí | Topic para filtrar repos |
| `--source-repo` | Sí | Repositorio fuente |
| `--files` | No | Archivos específicos |
| `--dry-run` | No | Solo mostrar cambios |
| `--parallel` | No | Ejecución paralela |
| `--max-workers` | No | Workers paralelos (default: 4) |
| `-v, --verbose` | No | Modo debug |

## Comportamiento

1. **Busca** repos con el topic especificado
2. **Filtra** repos archivados, vacíos y sin permisos
3. **Compara** workflows del repo fuente con cada destino
4. **Crea PR** en repos que necesitan actualización
5. **Salta** repos con PRs de sync existentes (idempotencia)
6. **Limpia** branches huérfanos si falla

## Uso Programático

```python
from workflow_sync import SyncConfig, WorkflowSyncService
from workflow_sync.clients import GitHubClient

config = SyncConfig(
    token="ghp_xxx",
    org="Automya",
    topic="microservice",
    source_repo="api-gateway",
)

client = GitHubClient(token=config.token)
service = WorkflowSyncService(client=client, config=config)
results = service.run()
```

## Arquitectura

```
workflow_sync/
├── interactive.py           # Aplicación interactiva de terminal
├── cli.py                   # Línea de comandos
├── models.py                # Dataclasses
├── exceptions.py            # Excepciones
├── validators/              # Validación de inputs
├── clients/                 # Cliente GitHub
├── services/                # Lógica de sincronización
└── WorkflowSync.command     # Ejecutable macOS
```

## Seguridad

- Token via variable de entorno o prompt interactivo (no CLI args)
- Validación de inputs contra patrones regex
- Prevención de path traversal
- Rate limiting con backoff exponencial

## Códigos de salida

| Código | Significado |
|--------|-------------|
| 0 | Éxito |
| 1 | Error general |
| 2 | Error de validación |
| 130 | Interrumpido (Ctrl+C) |
