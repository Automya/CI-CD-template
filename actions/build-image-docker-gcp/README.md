# Build Image Docker (GCP)

Este composite action es similar a `build-image-docker-no-repo` pero está optimizado para flujos estándar en GCP. Construye una imagen Docker, la sube a Google Artifact Registry y soporta despliegue automático a producción vía GitOps en eventos de `release`.

## Características

*   **Build & Push**: Construye y sube imágenes Docker a GCP Artifact Registry.
*   **Workload Identity**: Autenticación segura con GCP.
*   **Feedback en PRs**: Notificaciones en los comentarios del PR.
*   **Despliegue Automático (GitOps)**: Actualización automática de manifiestos Kubernetes en producción al publicar una release.

## Inputs

| Input | Descripción | Requerido | Default |
| :--- | :--- | :--- | :--- |
| `gitops_repo` | Repositorio GitOps destino (ej: `Automya/gitops`). | No | |
| `prod_manifest_path` | Ruta del manifiesto de producción en el repo GitOps. | No | |
| `gitops_token` | Token con permisos de escritura en el repo GitOps. | No | |
| `container_name` | Nombre del contenedor a actualizar. | No | |

## Variables de Entorno Requeridas

*   `PROJECT_ID`
*   `GCP_REGION`
*   `REPOSITORY`
*   `IMAGE_NAME`
*   `GH_TOKEN`
*   `MAVEN_USERNAME`, `MAVEN_PASSWORD`, etc. (Opcional)

## Ejemplo de Uso

```yaml
name: Build and Deploy GCP

on:
  push:
    branches: [ "main" ]
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
      PROJECT_ID: "my-gcp-project"
      GCP_REGION: "europe-west1"
      REPOSITORY: "my-repo"
      IMAGE_NAME: "my-service"
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

    steps:
      - uses: actions/checkout@v4

      - name: Build and Deploy
        uses: Automya/CI-CD-template/actions/build-image-docker-gcp@main
        with:
          gitops_repo: "Automya/gitops"
          prod_manifest_path: "k8s/prod/my-service.yaml"
          gitops_token: ${{ secrets.GITOPS_PAT }}
```
