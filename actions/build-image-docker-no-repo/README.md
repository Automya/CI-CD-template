# Build Image Docker (No Repo)

Este composite action construye una imagen Docker y la sube a Google Artifact Registry. Además, soporta un flujo de despliegue automático a producción (GitOps) cuando se dispara por un evento de `release`.

## Características

*   **Build & Push**: Construye y sube imágenes Docker a GCP Artifact Registry.
*   **Workload Identity**: Utiliza Workload Identity Federation para autenticación segura sin llaves JSON.
*   **Feedback en PRs**: Comenta en el Pull Request el estado del build (éxito/fallo).
*   **Despliegue Automático (GitOps)**: Al publicar una release, actualiza automáticamente el manifiesto de Kubernetes en un repositorio GitOps y hace merge del cambio.

## Inputs

| Input | Descripción | Requerido | Default |
| :--- | :--- | :--- | :--- |
| `gitops_repo` | Repositorio GitOps destino en formato `owner/repo` (ej: `Automya/gitops`). Requerido para despliegue en release. | No | |
| `prod_manifest_path` | Ruta del manifiesto Kubernetes para producción dentro del repo GitOps (ej: `k8s/prod/deployment.yaml`). Requerido para despliegue en release. | No | |
| `gitops_token` | Token de GitHub con permisos de escritura en el repositorio GitOps. Requerido para despliegue en release. | No | |
| `container_name` | Nombre del contenedor a actualizar en el manifiesto. Si no se define, usa el valor de la variable de entorno `IMAGE_NAME`. | No | |

## Variables de Entorno Requeridas

El workflow que usa esta acción debe definir las siguientes variables de entorno:

*   `PROJECT_ID`: ID del proyecto de GCP.
*   `GCP_REGION`: Región de GCP (ej: `europe-west1`).
*   `REPOSITORY`: Nombre del repositorio en Artifact Registry.
*   `IMAGE_NAME`: Nombre de la imagen Docker.
*   `GH_TOKEN`: Token de GitHub para comentar en PRs (usualmente `${{ secrets.GITHUB_TOKEN }}`).
*   `MAVEN_USERNAME`, `MAVEN_PASSWORD`, etc.: (Opcional) Argumentos de construcción si tu Dockerfile los requiere.

## Ejemplo de Uso

```yaml
name: Build and Deploy

on:
  push:
    branches: [ "main" ]
  pull_request:
  issue_comment:
    types: [created]
  release:
    types: [published]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
      issues: write
      id-token: write # Requerido para Workload Identity

    env:
      PROJECT_ID: "my-gcp-project"
      GCP_REGION: "europe-west1"
      REPOSITORY: "my-repo"
      IMAGE_NAME: "my-app"
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

    steps:
      - uses: actions/checkout@v4

      - name: Build, Push and Deploy
        uses: Automya/CI-CD-template/actions/build-image-docker-no-repo@main
        with:
          gitops_repo: "Automya/gitops"
          prod_manifest_path: "apps/my-app/overlays/prod/deployment.yaml"
          gitops_token: ${{ secrets.GITOPS_PAT }} # Token con permisos de escritura en el repo GitOps
          container_name: "my-app-container" # Opcional
```

## Flujo de Despliegue (Release)

1.  Crea una **Release** en GitHub con un tag semántico (ej: `v1.0.0`).
2.  El workflow se dispara.
3.  La acción construye la imagen Docker y la etiqueta con `v1.0.0`.
4.  La acción hace checkout del repositorio GitOps definido en `gitops_repo`.
5.  Actualiza el archivo `prod_manifest_path` cambiando la imagen del contenedor `container_name` al nuevo tag `v1.0.0`.
6.  Crea una nueva rama y un Pull Request en el repositorio GitOps.
7.  Automáticamente hace merge del PR para aplicar el cambio en producción.
