# Workflow Sync Tool

Herramienta para sincronizar archivos de GitHub Actions workflows desde un repositorio fuente hacia todos los repositorios de una organización que tengan un topic específico.

## Instalación

```bash
cd tools/workflow_sync
pip install .
```

## 🖥️ Aplicación Interactiva de Terminal

La forma recomendada de usar esta herramienta es mediante la aplicación interactiva de terminal.

### Ejecutar con doble clic (macOS)

Simplemente haz doble clic en el archivo `WorkflowSync.command`.

### Ejecutar desde terminal

```bash
cd tools/workflow_sync
python3 interactive.py
```

O después de instalar:

```bash
workflow-sync-interactive
```

### Características

- 🎨 Interfaz de terminal con colores ANSI
- 📝 Prompts interactivos para introducir datos
- ✅ Validación en tiempo real
- 📊 Resumen de configuración antes de ejecutar
- 🔍 Modo dry-run (solo mostrar cambios sin aplicar)
- ⚡ Ejecución paralela opcional
- 🔐 Persistencia de token (guardado en `~/.workflow-sync-config` con permisos 600)
- 🔑 Menú para cambiar/rotar token en cualquier momento

### Menú Principal

```
╔══════════════════════════════════════════════════════════╗
║              🔄  WORKFLOW SYNC TOOL  🔄                  ║
╚══════════════════════════════════════════════════════════╝

─── Menú Principal ───

1) 🔄 Sincronizar workflows
2) 🔑 Cambiar/Rotar token
3) 🚪 Salir
```

## ⌨️ Línea de Comandos (CLI)

Para usuarios avanzados o automatización:

```bash
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"

# Sincronizar todos los workflows
workflow-sync --org Automya --topic microservice --source-repo api-gateway

# Solo archivos específicos
workflow-sync --org Automya --topic microservice --source-repo api-gateway \
    --files build.yml deploy.yml

# Dry-run (solo mostrar qué cambiaría)
workflow-sync --org Automya --topic microservice --source-repo api-gateway --dry-run

# Ejecución paralela
workflow-sync --org Automya --topic microservice --source-repo api-gateway --parallel
```

### Argumentos CLI

| Argumento | Requerido | Descripción |
|-----------|-----------|-------------|
| `--org` | Sí | Organización de GitHub |
| `--topic` | Sí | Topic para filtrar repos |
| `--source-repo` | Sí | Repositorio fuente de workflows |
| `--files` | No | Archivos específicos a sincronizar |
| `--dry-run` | No | Solo mostrar cambios sin aplicar |
| `--parallel` | No | Ejecución paralela |
| `--max-workers` | No | Número de workers paralelos (default: 4) |
| `-v, --verbose` | No | Modo debug con logs detallados |

## Comportamiento

1. **Busca** repositorios con el topic especificado en la organización
2. **Filtra** repos archivados, vacíos y sin permisos de escritura
3. **Compara** workflows del repo fuente con cada repo destino
4. **Crea PR** en repos que necesitan actualización
5. **Salta** repos que ya tienen PRs de sync pendientes (idempotencia)
6. **Limpia** branches huérfanos si el proceso falla

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
├── models.py                # Dataclasses (SyncConfig, SyncResult, etc.)
├── exceptions.py            # Excepciones personalizadas
├── validators/              # Validación de inputs
│   └── input_validator.py   # Validadores con patrones regex
├── clients/                 # Cliente GitHub
│   └── github_client.py     # Wrapper de PyGithub
├── services/                # Lógica de negocio
│   └── sync_service.py      # Servicio de sincronización
└── WorkflowSync.command     # Launcher macOS (doble clic)
```

## Seguridad

- Token guardado con permisos 600 (solo lectura/escritura para el usuario)
- Token via prompt interactivo (nunca como argumento CLI visible)
- Validación de inputs contra patrones regex
- Prevención de path traversal en nombres de archivo
- Rate limiting con backoff exponencial

## Códigos de salida

| Código | Significado |
|--------|-------------|
| 0 | Éxito |
| 1 | Error general |
| 2 | Error de validación |
| 130 | Interrumpido (Ctrl+C) |
