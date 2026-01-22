# Guía de Configuración: Sync Docs to Confluence

Esta guía te llevará paso a paso para configurar la sincronización automática de documentación desde GitHub a Confluence.

## 📋 Pre-requisitos

- Repositorio de GitHub con documentación en Markdown
- Cuenta de Confluence Cloud con permisos para crear páginas
- Permisos de admin en el repositorio de GitHub (para configurar secrets)

## 🔧 Paso 1: Generar API Token de Confluence

1. Inicia sesión en tu cuenta de Atlassian
2. Ve a: https://id.atlassian.com/manage-profile/security/api-tokens
3. Click en **"Create API token"**
4. Dale un nombre descriptivo: `GitHub Actions Sync`
5. **Copia el token** (solo se muestra una vez)

💡 **Tip**: Guarda el token en un lugar seguro. No podrás verlo de nuevo.

## 📍 Paso 2: Obtener el Parent Page ID

El Parent Page ID es el ID de la página bajo la cual se crearán todas las páginas de documentación.

### Opción A: Desde la URL

1. Ve a la página en Confluence donde quieres que se cree la documentación
2. Copia el ID desde la URL:

```
https://yourorg.atlassian.net/wiki/spaces/DOCS/pages/123456789/Page+Title
                                                        ^^^^^^^^^
                                                        Este es el ID
```

### Opción B: Desde el menú de página

1. Ve a la página en Confluence
2. Click en los tres puntos `···` → **"Page Information"**
3. El ID aparece en la URL o en la sección de información

### Opción C: Usando la API

```bash
curl -u "tu-email@example.com:tu-api-token" \
  "https://yourorg.atlassian.net/wiki/rest/api/content/search?cql=title='Tu Página'&spaceKey=DOCS"
```

El ID estará en el campo `id` del resultado.

## 🔐 Paso 3: Configurar Secrets en GitHub

1. Ve a tu repositorio en GitHub
2. Click en **Settings** → **Secrets and variables** → **Actions**
3. Click en **"New repository secret"**
4. Agrega los siguientes secrets:

| Secret Name | Descripción | Ejemplo |
|-------------|-------------|---------|
| `CONFLUENCE_URL` | URL base de tu Confluence | `https://yourorg.atlassian.net/wiki` |
| `CONFLUENCE_USERNAME` | Tu email de Confluence | `tu-email@example.com` |
| `CONFLUENCE_API_TOKEN` | El token generado en Paso 1 | `ATATT3x...` |
| `CONFLUENCE_SPACE_KEY` | Clave del espacio (en mayúsculas) | `DOCS` o `TEAM` |
| `CONFLUENCE_PARENT_PAGE_ID` | ID de la página padre (Paso 2) | `123456789` |

### 📸 Captura de pantalla de ejemplo:

```
Name:  CONFLUENCE_URL
Value: https://mycompany.atlassian.net/wiki

[Add secret]
```

## 📁 Paso 4: Crear la carpeta de documentación

En tu repositorio, crea la estructura de carpetas:

```bash
mkdir -p docs
```

Agrega algunos archivos Markdown de ejemplo:

```bash
# docs/index.md
---
title: Índice de Documentación
---

# Bienvenido

Esta es la documentación de nuestro proyecto.

## Contenido

- [Guía de Inicio](getting-started.md)
- [Guías](guides/)
```

```bash
# docs/getting-started.md
---
title: Guía de Inicio Rápido
---

# Guía de Inicio Rápido

Pasos para comenzar...
```

```bash
# docs/guides/installation.md
---
title: Instalación
---

# Instalación

Instrucciones de instalación...
```

## ⚙️ Paso 5: Crear el Workflow

Crea el archivo `.github/workflows/sync-docs-confluence.yml`:

```yaml
name: Sync Documentation to Confluence

on:
  push:
    branches:
      - main
    paths:
      - 'docs/**/*.md'
  workflow_dispatch:
    inputs:
      sync_mode:
        description: 'Sync mode'
        required: false
        default: 'all'
        type: choice
        options:
          - all
          - changed

permissions:
  contents: read

jobs:
  sync-to-confluence:
    name: Sync Docs to Confluence
    runs-on: ubuntu-latest

    steps:
      - name: Sync Documentation to Confluence
        uses: Automya/CI-CD-template/actions/sync-docs-confluence@main
        with:
          confluence_url: ${{ secrets.CONFLUENCE_URL }}
          confluence_username: ${{ secrets.CONFLUENCE_USERNAME }}
          confluence_api_token: ${{ secrets.CONFLUENCE_API_TOKEN }}
          confluence_space_key: ${{ secrets.CONFLUENCE_SPACE_KEY }}
          confluence_parent_page_id: ${{ secrets.CONFLUENCE_PARENT_PAGE_ID }}
          docs_folder: 'docs'
          sync_mode: ${{ github.event.inputs.sync_mode || 'changed' }}
          page_title_from_frontmatter: 'true'
```

## 🚀 Paso 6: Probar la Sincronización

### Primera sincronización (manual)

1. Ve a tu repositorio en GitHub
2. Click en **Actions**
3. Selecciona el workflow **"Sync Documentation to Confluence"**
4. Click en **"Run workflow"**
5. Selecciona `sync_mode: all`
6. Click en **"Run workflow"**

### Observar el resultado

1. Espera a que termine el workflow (1-2 minutos)
2. Revisa los logs para ver las páginas sincronizadas
3. Ve a Confluence y verifica que las páginas se crearon correctamente

## ✅ Verificar la Configuración

### Checklist de Verificación:

- [ ] ¿Se crearon todas las páginas en Confluence?
- [ ] ¿La jerarquía de carpetas se respetó?
- [ ] ¿Los títulos de las páginas son correctos?
- [ ] ¿Las páginas están bajo la página padre correcta?
- [ ] ¿El contenido Markdown se convirtió correctamente?

### Si algo falló:

1. **Revisa los logs del workflow** en GitHub Actions
2. **Verifica los secrets**:
   ```bash
   # Prueba manualmente la autenticación
   curl -u "tu-email:tu-token" \
     "https://yourorg.atlassian.net/wiki/rest/api/space/DOCS"
   ```
3. **Verifica permisos** en Confluence:
   - ¿Puedes crear páginas en el espacio?
   - ¿La página padre existe?

## 🔄 Paso 7: Sincronización Automática

Ahora cada vez que hagas push a `main` con cambios en `docs/**/*.md`:

1. El workflow se ejecutará automáticamente
2. Solo sincronizará archivos modificados (modo `changed`)
3. Recibirás un resumen en el job summary

### Probar sincronización automática:

```bash
# Edita un archivo
echo "## Nueva sección" >> docs/index.md

# Commit y push
git add docs/index.md
git commit -m "docs: actualizar índice"
git push origin main

# Observa el workflow ejecutarse automáticamente
```

## 📚 Uso Avanzado

### Frontmatter YAML

Usa frontmatter para personalizar títulos y metadata:

```markdown
---
title: Mi Título Personalizado
labels:
  - documentation
  - api
---

# Contenido del documento
```

### Sincronizar desde la Raíz del Repositorio

Si quieres sincronizar **todo el repositorio** en lugar de solo una carpeta, configura `docs_folder: '.'`:

```yaml
with:
  docs_folder: '.'  # Sincroniza desde la raíz del repo
```

Esto sincronizará todos los archivos `.md` del repositorio, **excluyendo automáticamente**:
- `.github/` - Workflows de GitHub
- `.git/` - Repositorio Git
- `node_modules/`, `__pycache__/`, `.venv/` - Dependencias y caches

### Estructura Recomendada

**Opción 1: Carpeta docs/ dedicada (recomendado)**
```
docs/
├── index.md              # Página principal
├── getting-started.md    # Guía de inicio
├── guides/               # Guías por categoría
│   ├── installation.md
│   ├── configuration.md
│   └── deployment.md
├── api/                  # Documentación de API
│   ├── overview.md
│   └── reference.md
└── troubleshooting/      # Resolución de problemas
    └── common-issues.md
```

**Opción 2: Sincronizar desde la raíz**
```
repo-root/
├── README.md             # Página principal
├── SETUP.md              # Guía de instalación
├── guides/
│   └── quickstart.md
└── .github/              # EXCLUIDO automáticamente
```

### Eliminar Documentación

Cuando elimines un archivo `.md`:

1. La página en Confluence **no se eliminará**
2. Se marcará como "deprecated" con un label
3. Se agregará un banner de advertencia

Para eliminar completamente una página, hazlo manualmente en Confluence.

## 🆘 Troubleshooting

### Error: "Authentication failed"

**Causa**: Credenciales incorrectas

**Solución**:
1. Verifica que `CONFLUENCE_USERNAME` sea tu email
2. Regenera el API token
3. Actualiza el secret `CONFLUENCE_API_TOKEN`

### Error: "Page not found"

**Causa**: Parent Page ID incorrecto

**Solución**:
1. Verifica el ID de la página padre
2. Asegúrate de tener permisos en esa página

### Error: "Space not found"

**Causa**: Space Key incorrecto

**Solución**:
1. Verifica el Space Key en Confluence (debe estar en MAYÚSCULAS)
2. Asegúrate de tener acceso al espacio

### Las páginas no se actualizan

**Causa**: Modo `changed` no detecta cambios

**Solución**:
1. Ejecuta manualmente con `sync_mode: all`
2. Verifica que los cambios estén en la carpeta `docs/`

### Token expirado

**Causa**: Los tokens creados antes del 15 de diciembre de 2024 expirarán

**Solución**:
1. Genera un nuevo API token
2. Actualiza el secret `CONFLUENCE_API_TOKEN`

## 📞 Soporte

Si tienes problemas:

1. Revisa los logs del workflow en GitHub Actions
2. Consulta el [README.md](README.md) para más detalles
3. Contacta al equipo de DevOps de Automya

## 🎉 ¡Listo!

Tu documentación ahora se sincroniza automáticamente con Confluence. Cada cambio en `docs/` se reflejará en Confluence en 1-2 minutos.

### Próximos pasos:

- ✏️ Escribe más documentación en `docs/`
- 🏷️ Usa frontmatter para personalizar títulos
- 📊 Monitorea los workflows en GitHub Actions
- 🔄 Mantén la documentación actualizada
