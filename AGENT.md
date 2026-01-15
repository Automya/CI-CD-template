# CI/CD Template - Documentación del Proyecto

## Descripción General

Este proyecto es un template de CI/CD para GitHub Actions diseñado para automatizar el ciclo de vida completo de aplicaciones, desde la construcción de imágenes Docker hasta el despliegue en Kubernetes mediante GitOps. El template está organizado en acciones públicas (`actions/`) y acciones internas reutilizables (`internal/`).

## Arquitectura

El proyecto sigue una arquitectura modular donde:
- **Acciones públicas (`actions/`)**: Acciones compuestas de alto nivel que pueden ser utilizadas directamente en workflows
- **Acciones internas (`internal/`)**: Acciones reutilizables de bajo nivel que encapsulan funcionalidades específicas

## Acciones Públicas (`actions/`)

### 1. Build de Imágenes Docker

#### `build-image-docker-gcp`
Construye y publica imágenes Docker en GCP Artifact Registry con feedback en PRs.

**Características:**
- Autenticación mediante Workload Identity Federation
- Soporte para comandos desde comentarios de PR (`build -t <tag> -b <branch>`)
- Validación de tags (semver para main, tags personalizados permitidos)
- Notificaciones a GitHub PR y Google Chat
- Actualización automática de GitOps en releases

**Inputs:**
- `gitops_repo`: Repositorio GitOps destino (opcional)
- `prod_manifest_path`: Ruta del manifiesto Kubernetes para producción
- `gitops_token`: Token con permisos write en GitOps
- `container_name`: Nombre del contenedor a actualizar
- `google_chat_webhook`: Webhook URL para Google Chat

**Variables de entorno requeridas:**
- `GCP_REGION`: Región de GCP
- `PROJECT_ID`: ID del proyecto GCP
- `REPOSITORY`: Nombre del repositorio en Artifact Registry
- `IMAGE_NAME`: Nombre de la imagen Docker
- `GH_TOKEN`: Token de GitHub
- `MAVEN_USERNAME`, `MAVEN_PASSWORD`: Credenciales Maven (opcionales)

#### `build-image-docker-automya-front`
Similar a `build-image-docker-gcp` pero configurado específicamente para proyectos frontend con tags permitidos `DEV` y `dev`.

#### `build-image-docker-no-repo`
Versión que no contiene autnticacion con repo de artefactos de github, utilizado mayormente para fronts o microservicios que no necesiten usar artefactos del registro de github, solo construye y publica imágenes.

### 2. Despliegue (`deploy-app`)

Actualiza tags de imágenes en repositorios GitOps mediante comandos desde PRs.

**Comando:** `deploy -t <tag> -e <env>` donde `env` puede ser `staging` o `prod`

**Características:**
- Actualización automática de manifiestos Kubernetes
- Creación de PRs en repositorio GitOps
- Reinicio automático de deployments en GKE
- Soporte para staging y producción
- Notificaciones en PR y Google Chat

**Inputs principales:**
- `gitops_repo`: Repositorio GitOps
- `staging_manifest_path`, `prod_manifest_path`: Rutas de manifiestos
- `image_name`: Nombre del contenedor
- `github_token`: Token con permisos
- `staging_cluster_name`, `prod_cluster_name`: Nombres de clusters GKE
- `staging_cluster_location`, `prod_cluster_location`: Ubicaciones de clusters
- `project_id`: ID del proyecto GCP
- `deployment_name`: Nombre del deployment (default: `image_name`)
- `namespace`: Namespace de Kubernetes (default: `default`)

### 3. Testing

#### `java-test`
Ejecuta tests para microservicios Java usando Gradle.

**Inputs:**
- `java-version`: Versión de Java (default: `17`)
- `gradle-args`: Argumentos para Gradle (default: `clean test`)

#### `npm-test`
Ejecuta tests para proyectos React/frontend usando NPM.

**Inputs:**
- `node-version`: Versión de Node.js (default: `22`)
- `npm-args`: Argumentos para npm test (default: `test`)
- `install-command`: Comando de instalación (default: `npm install`)

### 4. Publicación de Artefactos

#### `publish-java-artifacts`
Publica artefactos Java a un repositorio central usando Gradle.

**Características:**
- Configuración automática de Java y Gradle
- Ejecuta `./gradlew publish -x test`

#### `publish-components`
Publica paquetes NPM a GitHub Packages.

**Características:**
- Configuración automática del registro npm para GitHub Packages
- Soporte para scope `@automya` (configurable)
- Variables de entorno requeridas:
  - `NPM_AUTH_TOKEN`: Token de autenticación
  - `GITHUB_REGISTRY_URL`: URL del registro (default: `npm.pkg.github.com`)
  - `GITHUB_REPOSITORY_OWNER`: Owner del repositorio
  - `NPM_SCOPE`: Scope del paquete (default: `@automya`)

### 5. Seguridad

#### `sast-scan`
Escaneo de seguridad usando Trivy con SBOM (Software Bill of Materials).

**Características:**
- Generación de SBOM usando CycloneDX (`cdxgen`)
- Escaneo de vulnerabilidades con Trivy
- Soporte para `.trivyignore` con fechas de expiración
- Reporte HTML generado y subido como artifact
- Filtrado por severidad: CRITICAL y HIGH
- Exit code 1 si encuentra vulnerabilidades no ignoradas

**Inputs:**
- `trivyignore-file`: Ruta al archivo `.trivyignore` (default: `.trivyignore`)

### 6. Sincronización de Configuración (`sync-config`)

Sincroniza archivos de configuración locales a ConfigMaps en GitOps.

**Comando:** `sync -b <branch> -e <env>`

**Características:**
- Sincronización desde repositorio fuente a GitOps
- Actualización de ConfigMaps en Kubernetes
- Creación automática de PRs en GitOps
- Soporte para staging y producción

**Inputs principales:**
- `staging_source_file`, `prod_source_file`: Archivos fuente locales
- `staging_configmap`, `prod_configmap`: Rutas de ConfigMaps en GitOps
- `gitops_repo`: Repositorio GitOps
- `github_token`: Token con permisos
- `configmap_key`: Clave en el ConfigMap (default: `application.yml`)

## Acciones Internas (`internal/`)

### Build y Docker

#### `build-context-determine`
Determina el contexto de build (branch, tag, status) basado en el tipo de evento.

**Lógica de validación:**
- Para `main`: Tags semver o tags permitidos (ej: `MAIN`, `DEV`)
- Para otras ramas: Tags semver no permitidos, solo tags personalizados
- Eventos soportados: `issue_comment`, `release`

**Outputs:**
- `branch`: Rama de git a usar
- `safe_branch`: Nombre de rama seguro para tags Docker
- `tag`: Tag final de Docker
- `status`: Estado lógico (ej: `invalid_tag_main`, `success`)
- `job_url`: URL del workflow run

#### `docker-build-push`
Construye y publica imágenes Docker a un registro.

**Inputs:**
- `image_full_name`: Nombre completo de la imagen con tag
- `build_args`: Lista de build-time variables
- `context`: Contexto de build (default: `.`)

**Outputs:**
- `status`: Resultado (`success`, `build_failed`, `push_failed`)

#### `build-report-message`
Genera mensajes de reporte para builds.

### Despliegue

#### `deploy-context-init`
Inicializa el contexto para despliegues, configurando tokens.

#### `deploy-validate-context`
Valida y prepara el contexto de despliegue.

**Validaciones:**
- Comando válido
- Tag especificado
- Entorno válido (`staging` o `prod`)

#### `deploy-select-manifest`
Selecciona la ruta del manifiesto según el entorno objetivo.

#### `deploy-report`
Genera reportes de despliegue con información de PRs GitOps y estado de reinicio.

#### `k8s-rollout-restart`
Reinicia un deployment de Kubernetes y espera el estado del rollout.

**Inputs:**
- `deployment_name`: Nombre del deployment
- `namespace`: Namespace (default: `default`)

**Outputs:**
- `success`: `true` si fue exitoso

### GitOps

#### `gitops-pr`
Actualiza un manifiesto Kubernetes, crea una rama y PR en GitOps.

**Características:**
- Usa `yq` para modificar YAML
- Detecta si la imagen ya está actualizada (retorna `needs_restart=true`)
- Crea PRs con formato estándar

**Inputs:**
- `gitops_repo`: Repositorio GitOps
- `gitops_token`: Token con permisos
- `manifest_path`: Ruta del manifiesto
- `container_name`: Nombre del contenedor
- `image_tag`: Nuevo tag de imagen
- `base_branch`: Rama base (default: `main`)
- `target_env`: Entorno objetivo (`staging`/`prod`)

**Outputs:**
- `pr_url`: URL de la PR creada
- `needs_restart`: `true` si no hubo cambios

#### `create-pr`
Acción genérica para crear PRs en repositorios.

### Sincronización

#### `sync-context-init`
Inicializa contexto para sincronización.

#### `sync-context-determine`
Determina el contexto de sincronización (repositorio fuente, archivos, entorno).

#### `sync-update-configmap`
Actualiza un ConfigMap con contenido de un archivo fuente.

#### `sync-set-env`
Establece variables de entorno para reportes.

#### `sync-report`
Genera reportes de sincronización.

### Utilidades

#### `parse-comment`
Parsea comandos desde comentarios de PR.

**Soporta comandos:**
- `build -t <tag> -b <branch>`
- `deploy -t <tag> -e <env>`
- `sync -b <branch> -e <env>`

**Características:**
- Ignora respuestas automáticas de bots
- Extrae flags: `-t` (tag), `-e` (env), `-b` (branch)
- Valida formato del comando

**Outputs:**
- `action`: Acción detectada
- `tag`, `env`, `branch`: Valores extraídos
- `is_valid`: `true` si el formato es válido
- `error_msg`: Mensaje de error si es inválido

#### `notify`
Envía notificaciones a GitHub PR y Google Chat.

**Inputs:**
- `github_token`: Token de GitHub
- `pr_number`: Número de PR
- `repo`: Repositorio (default: `github.repository`)
- `webhook_url`: URL de webhook de Google Chat
- `pr_message`: Mensaje para PR
- `chat_message`: Mensaje para Google Chat (default: `pr_message`)

#### `setup-gcp`
Configura autenticación GCP usando Workload Identity Federation.

**Características:**
- Limpia variables de entorno de credenciales
- Instala gcloud SDK
- Autentica usando Workload Identity
- Configura Docker para Artifact Registry

**Inputs:**
- `workload_identity_provider`: Provider de Workload Identity
- `service_account`: Service Account de GCP
- `region`: Región de GCP

#### `setup-java-gradle`
Configura Java y Gradle para proyectos Java.

**Inputs:**
- `java-version`: Versión de Java

#### `util-normalize-repo`
Normaliza nombres de repositorios (formato `owner/repo`).

#### `trivy-report`
Genera reportes de Trivy (usado por `sast-scan`).

## Flujos de Trabajo Típicos

### 1. Build desde PR
```
Comentario en PR: "build -t dev -b feature/my-feature"
→ Parse comment
→ Determine context
→ Checkout branch
→ Setup GCP
→ Build & Push Docker image
→ Notify result
```

### 2. Deploy desde PR
```
Comentario en PR: "deploy -t v1.2.3 -e staging"
→ Parse comment
→ Validate context
→ Select manifest
→ Update GitOps manifest
→ Create GitOps PR
→ Get GKE credentials
→ Restart deployment
→ Notify result
```

### 3. Release
```
Evento: release
→ Determine context (tag from release)
→ Build & Push Docker image
→ Update GitOps (prod)
→ Create GitOps PR
```

### 4. Sync Config
```
Comentario en PR: "sync -b feature/config -e staging"
→ Parse comment
→ Determine context
→ Checkout source repo
→ Checkout GitOps repo
→ Update ConfigMap
→ Create GitOps PR
→ Report result
```

## Variables de Entorno Requeridas

### Para Builds Docker
- `GCP_REGION`: Región de GCP (ej: `us-central1`)
- `PROJECT_ID`: ID del proyecto GCP
- `REPOSITORY`: Nombre del repositorio en Artifact Registry
- `IMAGE_NAME`: Nombre de la imagen Docker
- `GH_TOKEN`: Token de GitHub con permisos

### Para Despliegues
- `GCP_REGION`, `PROJECT_ID`: Configuración GCP
- Tokens de GitHub con permisos en repositorio fuente y GitOps

### Para Publicación NPM
- `NPM_AUTH_TOKEN`: Token de autenticación npm
- `GITHUB_REGISTRY_URL`: URL del registro (opcional)
- `GITHUB_REPOSITORY_OWNER`: Owner del repositorio (opcional)
- `NPM_SCOPE`: Scope del paquete (opcional, default: `@automya`)

## Configuración de Workload Identity Federation

El proyecto utiliza Workload Identity Federation para autenticación segura con GCP sin necesidad de almacenar credenciales.

**Configuración por defecto:**
- Provider: `projects/244039780319/locations/global/workloadIdentityPools/github-actions-pool/providers/github-provider-automya`
- Service Account: `github-ci-sa@automya.iam.gserviceaccount.com`

## Convenciones de Naming

### Tags Docker
- **Main branch**: Tags semver (`v1.2.3`) o tags permitidos (`MAIN`, `DEV`)
- **Otras ramas**: Tags personalizados (no semver), nombre de rama por defecto

### Ramas GitOps
- Deploy: `deploy/<env>/<container-name>-<tag>`
- Sync: `sync/<env>/<branch>`

### Commits GitOps
- Deploy: `chore(<env>): update <container> to <tag>`
- Sync: `chore(<env>): sync config from <branch>`

## Seguridad

### Autenticación
- **GCP**: Workload Identity Federation (sin credenciales almacenadas)
- **GitHub**: Tokens con permisos mínimos necesarios
- **Docker**: Autenticación mediante `gcloud auth configure-docker`

### Escaneo de Vulnerabilidades
- Trivy con SBOM (CycloneDX)
- Soporte para ignorar CVEs con fechas de expiración
- Reportes HTML generados automáticamente

## Notificaciones

### GitHub PR
- Comentarios automáticos en PRs con estado de builds/deploys
- Enlaces a logs de workflows
- Mensajes formateados con emojis

### Google Chat
- Notificaciones opcionales mediante webhooks
- Mensajes formateados en Markdown
- Enlaces a workflows y PRs

## Mejores Prácticas

1. **Tags**: Usar semver para producción, tags descriptivos para desarrollo
2. **Branches**: Mantener nombres de ramas compatibles con tags Docker
3. **Manifests**: Mantener estructura consistente en GitOps
4. **Tokens**: Usar tokens con permisos mínimos necesarios
5. **ConfigMaps**: Mantener configuración versionada en GitOps

## Estructura del Proyecto

```
CI-CD-template/
├── actions/              # Acciones públicas de alto nivel
│   ├── build-image-docker-gcp/
│   ├── build-image-docker-automya-front/
│   ├── build-image-docker-no-repo/
│   ├── deploy-app/
│   ├── java-test/
│   ├── npm-test/
│   ├── publish-java-artifacts/
│   ├── publish-components/
│   ├── sast-scan/
│   └── sync-config/
└── internal/             # Acciones internas reutilizables
    ├── build-context-determine/
    ├── build-report-message/
    ├── create-pr/
    ├── deploy-context-init/
    ├── deploy-report/
    ├── deploy-select-manifest/
    ├── deploy-validate-context/
    ├── docker-build-push/
    ├── gitops-pr/
    ├── k8s-rollout-restart/
    ├── notify/
    ├── parse-comment/
    ├── setup-gcp/
    ├── setup-java-gradle/
    ├── sync-context-determine/
    ├── sync-context-init/
    ├── sync-report/
    ├── sync-set-env/
    ├── sync-update-configmap/
    ├── trivy-report/
    └── util-normalize-repo/
```

## Uso en Workflows

### Ejemplo: Build desde PR
```yaml
on:
  issue_comment:
    types: [created]

jobs:
  build:
    runs-on: ubuntu-latest
    env:
      GCP_REGION: us-central1
      PROJECT_ID: my-project
      REPOSITORY: my-repo
      IMAGE_NAME: my-service
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    steps:
      - uses: Automya/CI-CD-template/actions/build-image-docker-gcp@main
        with:
          gitops_repo: Automya/gitops
          prod_manifest_path: k8s/prod/my-service.yaml
          gitops_token: ${{ secrets.GITOPS_TOKEN }}
```

### Ejemplo: Deploy desde PR
```yaml
on:
  issue_comment:
    types: [created]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: Automya/CI-CD-template/actions/deploy-app@main
        with:
          gitops_repo: Automya/gitops
          staging_manifest_path: k8s/staging/my-service.yaml
          prod_manifest_path: k8s/prod/my-service.yaml
          image_name: my-service
          github_token: ${{ secrets.GITOPS_TOKEN }}
          staging_cluster_name: staging-cluster
          prod_cluster_name: prod-cluster
          staging_cluster_location: us-central1
          prod_cluster_location: us-central1
          project_id: my-project
```

## Mantenimiento

- Las acciones internas están diseñadas para ser reutilizables
- Los cambios en acciones internas afectan a todas las acciones públicas que las usan
- Mantener compatibilidad hacia atrás al modificar acciones públicas
- Documentar cambios significativos en los inputs/outputs

