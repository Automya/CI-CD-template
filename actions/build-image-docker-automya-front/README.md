# Build Image Docker (Automya Front)

Este composite action está diseñado específicamente para el frontend de Automya (o flujos similares basados en la rama `dev`). Construye y sube imágenes Docker, y gestiona el despliegue a producción vía GitOps en eventos de `release`.

## Diferencias Clave

*   **Rama Principal**: Espera que la rama de desarrollo principal sea `dev` en lugar de `main`.
*   **Validación de Tags**: Verifica que las releases apunten a la rama `dev`.

## Inputs

| Input | Descripción | Requerido | Default |
| :--- | :--- | :--- | :--- |
| `gitops_repo` | Repositorio GitOps destino. | No | |
| `prod_manifest_path` | Ruta del manifiesto de producción. | No | |
| `gitops_token` | Token con permisos de escritura en el repo GitOps. | No | |
| `container_name` | Nombre del contenedor a actualizar. | No | |

## Variables de Entorno Requeridas

*   `PROJECT_ID`
*   `GCP_REGION`
*   `REPOSITORY`
*   `IMAGE_NAME`
*   `GH_TOKEN`

## Ejemplo de Uso

```yaml
name: Build Front

on:
  push:
    branches: [ "dev" ] # Nota: dev en lugar de main
  pull_request:
  release:
    types: [published]

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
      issues: write
      id-token: write

    env:
      PROJECT_ID: "automya-project"
      GCP_REGION: "europe-west1"
      REPOSITORY: "frontend-repo"
      IMAGE_NAME: "automya-front"
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

    steps:
      - uses: actions/checkout@v4

      - name: Build and Deploy
        uses: Automya/CI-CD-template/actions/build-image-docker-automya-front@main
        with:
          gitops_repo: "Automya/gitops"
          prod_manifest_path: "k8s/prod/frontend.yaml"
          gitops_token: ${{ secrets.GITOPS_PAT }}
```
