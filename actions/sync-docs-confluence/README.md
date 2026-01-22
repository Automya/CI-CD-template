# Sync Documentation to Confluence

Action de GitHub que sincroniza automáticamente documentación Markdown desde un repositorio hacia Confluence Cloud.

## Características

- ✅ **Sincronización automática** en push a la carpeta de documentación
- 📁 **Preservación de jerarquía** - Las carpetas se convierten en páginas padre en Confluence
- 🏷️ **Páginas deprecated** - Archivos eliminados se marcan como deprecated (no se eliminan)
- 🔄 **Idempotencia** - Solo actualiza si el contenido cambió
- 📝 **Soporte de frontmatter** - Extrae títulos y metadata de archivos YAML frontmatter
- 🚀 **Detección de cambios** - Modo "changed" sincroniza solo archivos modificados

## Uso

### Ejemplo Básico (carpeta docs/)

```yaml
name: Sync Docs to Confluence

on:
  push:
    branches:
      - main
    paths:
      - 'docs/**/*.md'
  workflow_dispatch:

permissions:
  contents: read

jobs:
  sync-docs:
    runs-on: ubuntu-latest
    steps:
      - name: Sync to Confluence
        uses: Automya/CI-CD-template/actions/sync-docs-confluence@main
        with:
          confluence_url: ${{ secrets.CONFLUENCE_URL }}
          confluence_username: ${{ secrets.CONFLUENCE_USERNAME }}
          confluence_api_token: ${{ secrets.CONFLUENCE_API_TOKEN }}
          confluence_space_key: 'DOCS'
          confluence_parent_page_id: '123456789'
          docs_folder: 'docs'
          sync_mode: 'changed'
          page_title_from_frontmatter: 'true'
```

### Ejemplo: Sincronizar desde la raíz del repositorio

```yaml
name: Sync All Markdown to Confluence

on:
  push:
    branches:
      - main
    paths:
      - '**.md'
      - '!.github/**'  # Excluir workflows
  workflow_dispatch:

permissions:
  contents: read

jobs:
  sync-all-docs:
    runs-on: ubuntu-latest
    steps:
      - name: Sync to Confluence
        uses: Automya/CI-CD-template/actions/sync-docs-confluence@main
        with:
          confluence_url: ${{ secrets.CONFLUENCE_URL }}
          confluence_username: ${{ secrets.CONFLUENCE_USERNAME }}
          confluence_api_token: ${{ secrets.CONFLUENCE_API_TOKEN }}
          confluence_space_key: 'DOCS'
          confluence_parent_page_id: '123456789'
          docs_folder: '.'  # Sincroniza desde la raíz
          sync_mode: 'changed'
          page_title_from_frontmatter: 'true'
```

## Inputs

### Requeridos

| Input | Descripción |
|-------|-------------|
| `confluence_url` | URL de Confluence Cloud (ej: `https://yourorg.atlassian.net/wiki`) |
| `confluence_username` | Email del usuario de Confluence |
| `confluence_api_token` | API token de Confluence ([cómo generarlo](#generar-api-token)) |
| `confluence_space_key` | Clave del espacio donde se crearán las páginas |
| `confluence_parent_page_id` | ID de la página padre bajo la cual se crearán las páginas |

### Opcionales

| Input | Descripción | Default |
|-------|-------------|---------|
| `docs_folder` | Ruta a la carpeta de documentación. Usa `"."` para sincronizar desde la raíz del repositorio (excluyendo automáticamente `.github/` y carpetas de sistema) | `docs` |
| `sync_mode` | Modo de sync: `all` (todos los archivos) o `changed` (solo modificados) | `changed` |
| `page_title_from_frontmatter` | Extraer título desde YAML frontmatter | `true` |

## Outputs

| Output | Descripción |
|--------|-------------|
| `synced_pages` | Número de páginas sincronizadas exitosamente |
| `failed_pages` | Número de páginas que fallaron |
| `confluence_urls` | Array JSON con URLs de las páginas sincronizadas |

## Configuración de Secrets

### Generar API Token

1. Ve a https://id.atlassian.com/manage-profile/security/api-tokens
2. Click en "Create API token"
3. Dale un nombre descriptivo (ej: "GitHub Actions Sync")
4. Copia el token generado

### Agregar Secrets en GitHub

Puedes configurar los secrets a **nivel de repositorio** o a **nivel de organización** (recomendado si usas la misma configuración en múltiples repos).

**Opción A: Secrets a nivel de organización (recomendado para múltiples repos)**

1. Ve a tu organización en GitHub
2. Click en **Settings** > **Secrets and variables** > **Actions**
3. Click en **New organization secret**
4. Agrega los siguientes secrets y selecciona los repositorios que tendrán acceso:
   - `CONFLUENCE_URL`: ej. `https://yourorg.atlassian.net/wiki`
   - `CONFLUENCE_USERNAME`: Tu email de Confluence
   - `CONFLUENCE_API_TOKEN`: El token generado arriba

**Opción B: Secrets a nivel de repositorio (para un solo repo)**

1. Ve a tu repositorio en GitHub
2. Click en **Settings** > **Secrets and variables** > **Actions**
3. Click en **New repository secret**
4. Agrega los siguientes secrets:
   - `CONFLUENCE_URL`: ej. `https://yourorg.atlassian.net/wiki`
   - `CONFLUENCE_USERNAME`: Tu email de Confluence
   - `CONFLUENCE_API_TOKEN`: El token generado arriba

**Nota:** Los secrets de organización se pueden compartir entre múltiples repositorios, lo cual es ideal si tienes varios repos de documentación que sincronizan al mismo Confluence.

### Obtener el Parent Folder/Page ID

El Parent Folder ID es el ID de la carpeta o página de Confluence donde se crearán todas las páginas de documentación.

**Nota:** En Confluence Cloud, las carpetas son en realidad páginas especiales que actúan como contenedores.

**Opción 1: Desde la URL de una carpeta**
```
https://yourorg.atlassian.net/wiki/spaces/DOCS/folder/81264642
                                                      ^^^^^^^^
                                                      Este es el ID
```

**Opción 2: Desde la URL de una página**
```
https://yourorg.atlassian.net/wiki/spaces/DOCS/pages/123456789/Page+Title
                                                        ^^^^^^^^^
                                                        Este es el ID
```

**Opción 3: Usando la API**
```bash
curl -u "your-email@example.com:your-api-token" \
  "https://yourorg.atlassian.net/wiki/api/v2/pages/81264642"
```

## Estructura de Documentación

### Frontmatter (Opcional)

Puedes usar YAML frontmatter para especificar metadatos:

```markdown
---
title: Mi Título Personalizado
---

# Contenido del documento
```

Sin frontmatter, el título se genera automáticamente desde el nombre del archivo.

### Jerarquía de Carpetas

La estructura de carpetas se preserva como jerarquía de páginas:

```
docs/
  ├── index.md              → Página "Index" (nivel 1)
  ├── getting-started.md    → Página "Getting Started" (nivel 1)
  └── guides/               → Página "Guides" (nivel 1, auto-creada)
      ├── installation.md   → Página "Installation" (nivel 2, hijo de "Guides")
      └── configuration.md  → Página "Configuration" (nivel 2, hijo de "Guides")
```

### Sincronizar desde la Raíz del Repositorio

Si quieres sincronizar todos los archivos Markdown del repositorio (no solo una carpeta específica), configura `docs_folder: '.'`:

```yaml
with:
  docs_folder: '.'  # Sincroniza desde la raíz
```

**Carpetas excluidas automáticamente:**
- `.github/` - Workflows y configuración de GitHub
- `.git/` - Repositorio Git
- `node_modules/` - Dependencias de Node.js
- `__pycache__/`, `.venv/`, `venv/` - Archivos de Python
- `.DS_Store` - Archivos de sistema macOS

**Ejemplo de estructura:**
```
repo-root/
  ├── README.md              → Página "README" (nivel 1)
  ├── SETUP.md               → Página "SETUP" (nivel 1)
  ├── guides/
  │   └── quickstart.md     → Página "Quickstart" (nivel 2, hijo de "Guides")
  └── .github/              → EXCLUIDO (no se sincroniza)
```

### Archivos Eliminados

Cuando eliminas un archivo `.md` del repositorio:

1. La página en Confluence **no se elimina**
2. Se agrega un label `deprecated` a la página
3. Se agrega un banner de advertencia al inicio:
   > ⚠️ Esta página ha sido deprecada y ya no se mantiene.

Esto previene la pérdida accidental de documentación.

## Cómo Funciona

1. **Detección de cambios**: Compara el commit actual vs el anterior para identificar archivos `.md` modificados/eliminados
2. **Conversión**: Convierte Markdown a Confluence Storage Format usando la librería `md2cf`
3. **Búsqueda**: Busca si la página ya existe en Confluence por título
4. **Sync**: Crea o actualiza la página según corresponda
5. **Jerarquía**: Crea páginas intermedias para carpetas si es necesario
6. **Reporte**: Genera un resumen con páginas sincronizadas y errores

## Troubleshooting

### Warning: "No file matched to requirements*.txt"

**Causa**: Mensaje de advertencia (no error) de setup-python cuando no encuentra archivos de dependencias

**Solución**:
- Este warning es **normal y seguro** si tu repositorio solo contiene documentación
- Las dependencias Python se instalan correctamente en el siguiente paso
- No afecta la funcionalidad del sync
- El warning ya fue eliminado en la última versión de la action

### Error: "Authentication failed"

**Causa**: Credenciales incorrectas

**Solución**:
1. Verifica que `CONFLUENCE_USERNAME` sea tu email
2. Regenera el API token
3. Actualiza el secret `CONFLUENCE_API_TOKEN`
4. Los tokens creados antes del 15 de diciembre de 2024 expirarán entre marzo y mayo de 2026

### Error: "Page not found"

- Verifica que el `confluence_parent_page_id` sea correcto
- Verifica que tu usuario tenga permisos para crear páginas en ese espacio

### Error: "Space not found"

- Verifica que el `confluence_space_key` sea correcto (en mayúsculas)
- Verifica que tu usuario tenga acceso al espacio

### Las páginas no se actualizan

- Verifica que `sync_mode` sea `all` o que los archivos realmente hayan cambiado
- El modo `changed` solo sincroniza archivos modificados en el último commit

## Arquitectura

Esta action sigue el patrón de composite actions del repositorio:

```
actions/sync-docs-confluence/          (Action pública)
  └─ Orquesta:
      ├─ internal/confluence-context-init/      (Inicialización)
      ├─ internal/confluence-detect-changes/    (Detección de cambios)
      ├─ internal/confluence-sync-pages/        (Sync con Python/md2cf)
      └─ internal/confluence-report/            (Generación de reportes)
```

## Dependencias

- Python 3.11
- Librerías Python:
  - `md2cf`: Conversión Markdown → Confluence
  - `PyYAML`: Parseo de frontmatter
  - `requests`: Cliente HTTP
- GitHub Actions:
  - `actions/checkout@v4`
  - `actions/setup-python@v5`
  - `actions/github-script@v7`

## Limitaciones Conocidas

- **Imágenes y adjuntos**: Actualmente no soportado (próxima versión)
- **Archivos eliminados**: Requiere que el título de la página coincida exactamente con el nombre del archivo para marcarla como deprecated
- **Rate limiting**: Sin retry automático en errores 429 (próxima versión)
- **Sincronización bidireccional**: No soportado (solo GitHub → Confluence)

## Mejoras Futuras

- ✨ Soporte para imágenes y archivos adjuntos
- ✨ Retry automático con exponential backoff
- ✨ Comparación de hash MD5 para updates más inteligentes
- ✨ Procesamiento paralelo de archivos
- ✨ Template configurable para mensajes de deprecación
- ✨ Sincronización bidireccional (Confluence → GitHub)

## Contribuir

Este es un proyecto interno de Automya. Para reportar issues o sugerir mejoras, contacta al equipo de DevOps.

## Licencia

Uso interno de Automya.
