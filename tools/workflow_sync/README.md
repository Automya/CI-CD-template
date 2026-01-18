# Workflow Sync Tool

Herramienta para sincronizar archivos de GitHub Actions workflows desde un repositorio fuente hacia todos los repositorios de una organización que tengan un topic específico.

## Instalación

Genera el ejecutable standalone (no requiere Python instalado para usar):

```bash
cd tools/workflow_sync
./build.sh
```

Esto genera el ejecutable `dist/WorkflowSync`.

## Uso

```bash
./dist/WorkflowSync
```

### Características

- Interfaz de terminal con colores ANSI
- Prompts interactivos para introducir datos
- Validación en tiempo real
- Resumen de configuración antes de ejecutar
- Modo dry-run (solo mostrar cambios sin aplicar)
- Auto-merge de PRs (mergea automáticamente después de crear)
- Ejecución paralela opcional
- Persistencia de token (guardado en `~/.workflow-sync-config` con permisos 600)
- Menú para cambiar/rotar token en cualquier momento
- Eliminación automática de workflows obsoletos (archivos en destino que no existen en fuente)
- Retry con update branch si hay conflictos de merge

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

### Opciones de Sincronización

| Opción | Descripción |
|--------|-------------|
| Organización | Organización de GitHub donde están los repos |
| Topic | Topic para filtrar qué repos sincronizar |
| Repo fuente | Repositorio de donde se copian los workflows |
| Archivos | Archivos específicos (vacío = todos los workflows) |
| Dry Run | Solo mostrar qué cambiaría, sin hacer cambios reales |
| Auto-merge | Mergear automáticamente los PRs después de crearlos |
| Paralelo | Procesar múltiples repos simultáneamente |

## Comportamiento

1. **Busca** repositorios con el topic especificado en la organización
2. **Filtra** repos archivados, vacíos y sin permisos de escritura
3. **Salta** repos sin carpeta `.github/workflows` (no necesitan workflows)
4. **Compara** workflows del repo fuente con cada repo destino
5. **Detecta** archivos obsoletos (existen en destino pero no en fuente) para eliminar
6. **Crea PR** en repos que necesitan actualización
7. **Auto-merge** PRs si la opción está habilitada (con retry si hay conflictos)
8. **Salta** repos que ya tienen PRs de sync pendientes (idempotencia)
9. **Limpia** branches huérfanos si el proceso falla

## Arquitectura

```
workflow_sync/
├── interactive.py           # Aplicación interactiva de terminal
├── models.py                # Dataclasses (SyncConfig, SyncResult, etc.)
├── exceptions.py            # Excepciones personalizadas
├── validators/              # Validación de inputs
│   └── input_validator.py   # Validadores con patrones regex
├── clients/                 # Cliente GitHub
│   └── github_client.py     # Wrapper de PyGithub con auto-merge y retry
├── services/                # Lógica de negocio
│   └── sync_service.py      # Servicio de sincronización
├── WorkflowSync.spec        # Configuración PyInstaller
└── build.sh                 # Script para generar ejecutable standalone
```

## Seguridad

- Token guardado con permisos 600 (solo lectura/escritura para el usuario)
- Token via prompt interactivo (nunca visible en logs)
- Validación de inputs contra patrones regex
- Prevención de path traversal en nombres de archivo
- Rate limiting con backoff exponencial
