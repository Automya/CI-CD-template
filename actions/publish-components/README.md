# Publish Components Action

Acción compuesta (composite action) para publicar paquetes npm al registro de GitHub Packages.

## Descripción

Esta acción automatiza el proceso de publicación de paquetes npm a GitHub Packages. Está inspirada en el pipeline de GitLab original pero adaptada para GitHub Actions con variables de entorno configurables.

## Variables de Entorno

La acción lee las siguientes variables de entorno del job consumidor:

| Variable | Descripción | Valor por defecto | Requerida |
|----------|-------------|-------------------|-----------|
| `NPM_AUTH_TOKEN` | Token de autenticación para GitHub Packages | - | ✅ Sí |
| `NPM_SCOPE` | Scope del paquete npm (ej: @automya) | `@automya` | No |
| `GITHUB_REGISTRY_URL` | URL del registro de GitHub | `npm.pkg.github.com` | No |
| `GITHUB_REPOSITORY_OWNER` | Owner del repositorio | `github.repository_owner` | No |
| `NODE_VERSION` | Versión de Node.js a usar | `20` | No |

## Requisitos Previos

### 1. Configurar package.json

Asegúrate de que tu `package.json` tenga configurado correctamente:

```json
{
  "name": "@automya/front-components",
  "version": "1.0.0",
  "repository": {
    "type": "git",
    "url": "git://github.com/Automya/front-components.git"
  },
  "publishConfig": {
    "registry": "https://npm.pkg.github.com"
  }
}
```

### 2. Configurar Permisos del Workflow

El workflow consumidor necesita permisos para escribir en GitHub Packages:

```yaml
permissions:
  contents: read
  packages: write
```

## Ejemplo de Uso

### Workflow Básico

```yaml
name: Publish NPM Package

on:
  release:
    types: [published]
  push:
    branches:
      - main

permissions:
  contents: read
  packages: write

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Publish to GitHub Packages
        uses: Automya/CI-CD-template/actions/publish-components@main
        env:
          NPM_AUTH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Workflow Avanzado con Variables Personalizadas

```yaml
name: Publish NPM Package (Advanced)

on:
  workflow_dispatch:
  release:
    types: [published]

permissions:
  contents: read
  packages: write

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Publish to GitHub Packages
        uses: Automya/CI-CD-template/actions/publish-components@main
        env:
          NPM_AUTH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          NPM_SCOPE: '@automya'
          NODE_VERSION: '18'
          GITHUB_REGISTRY_URL: 'npm.pkg.github.com'
```

### Workflow para front-components

Ejemplo específico para el repositorio `front-components`:

```yaml
name: Publish Components to GitHub Packages

on:
  push:
    branches:
      - main
    tags:
      - 'v*'

permissions:
  contents: read
  packages: write

jobs:
  publish-npm:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Publish to GitHub Packages
        uses: Automya/CI-CD-template/actions/publish-components@main
        env:
          NPM_AUTH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          NPM_SCOPE: '@automya'
          NODE_VERSION: '20'
```

## Funcionamiento

La acción ejecuta los siguientes pasos:

1. **Setup Node.js**: Configura la versión de Node.js especificada
2. **Configurar Registro**: Crea `.npmrc` con la configuración del registro de GitHub Packages
3. **Instalar Dependencias**: Ejecuta `npm ci` para instalar las dependencias
4. **Build** (opcional): Si existe un script `build` en `package.json`, lo ejecuta
5. **Publicar**: Ejecuta `npm publish` para subir el paquete

## Comparación con GitLab CI

### Pipeline Original de GitLab

```yaml
publish-npm:
  stage: deploy
  script:
    - echo "@automya:registry=https://${CI_SERVER_HOST}/api/v4/projects/${CI_PROJECT_ID}/packages/npm/" > .npmrc
    - echo "//${CI_SERVER_HOST}/api/v4/projects/${CI_PROJECT_ID}/packages/npm/:_authToken=${CI_JOB_TOKEN}" >> .npmrc
    - npm i
    - npm publish
```

### Ventajas de la Implementación en GitHub Actions

- ✅ Variables de entorno configurables
- ✅ Setup automático de Node.js
- ✅ Soporte para build opcional
- ✅ Usa `npm ci` en lugar de `npm i` para instalaciones más confiables
- ✅ Mensajes de progreso claros
- ✅ Reutilizable como composite action

## Troubleshooting

### Error: "You must be logged in to publish packages"

Verifica que:
- El token `NPM_AUTH_TOKEN` esté configurado correctamente
- El workflow tenga permisos de `packages: write`
- El `package.json` tenga el `publishConfig` correcto

### Error: "Package name must include scope"

Asegúrate de que el nombre del paquete en `package.json` incluya el scope:
```json
{
  "name": "@automya/tu-paquete"
}
```

### Error: "You cannot publish over the previously published version"

Incrementa la versión en `package.json` antes de publicar:
```bash
npm version patch  # o minor, major según corresponda
```

## Notas Adicionales

- La acción utiliza `npm ci` que es más rápido y confiable que `npm install` para CI/CD
- Si tu proyecto tiene un script `build`, se ejecutará automáticamente antes de publicar
- El token `GITHUB_TOKEN` es proporcionado automáticamente por GitHub Actions y tiene los permisos necesarios cuando se configura correctamente en el workflow