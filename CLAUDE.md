# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a GitHub Actions reusable composite actions library for CI/CD pipelines, designed for GCP (Google Cloud Platform) and GitOps workflows. The library is maintained by Automya and provides standardized actions for building, deploying, and managing containerized applications.

## Architecture

### Directory Structure

- **`actions/`** - Public composite actions intended to be consumed by other repositories
- **`internal/`** - Internal helper actions used only by the public actions (not for external consumption)

### Action Pattern

All actions follow the GitHub composite action pattern with `action.yml` files. Public actions orchestrate multiple internal actions to provide complete workflows.

The docker build actions follow a composition pattern:
- `build-image-docker` - Base action with all configuration options
- `build-image-docker-gcp`, `build-image-docker-no-repo`, `build-image-docker-automya-front` - Wrapper actions that delegate to the base with preset configurations

### Key Workflows

1. **Build Flow**: PR comment triggers (`build -b <branch> -t <tag>`) → parse comment → checkout → GCP auth → Docker build/push → notify
2. **Deploy Flow**: PR comment triggers (`deploy -t <tag> -e <env> [-r <deployment|cronjob>]`) → parse → GitOps PR → K8s rollout restart (skipped for CronJobs) → notify
3. **Sync Config Flow**: PR comment triggers (`sync -b <branch> -e <env>`) → update ConfigMap in GitOps repo → create PR

### Environment Variables Convention

Actions expect these environment variables to be set by the consuming workflow:
- `GH_TOKEN` - GitHub token for API calls
- `GCP_REGION`, `PROJECT_ID`, `REPOSITORY`, `IMAGE_NAME` - GCP Artifact Registry config
- `MAVEN_USERNAME`, `MAVEN_PASSWORD`, `MAVEN_USERNAME2`, `MAVEN_PASSWORD2` - For Java builds with private dependencies

### Required Inputs (Security)

GCP credentials are NOT hardcoded. Consuming workflows must provide:
- `workload_identity_provider` - GCP Workload Identity Provider resource name
- `service_account` - GCP Service Account email

## Public Actions Reference

| Action | Purpose |
|--------|---------|
| `build-image-docker` | Base Docker build action with full configuration. Supports `resource_type` input for CronJob GitOps updates on release. Supports `release_branch` input (default: `main`) for repos where the main branch is not `main` |
| `build-image-docker-gcp` | Docker build with GitOps integration (wrapper). Passes `resource_type` and `release_branch` to base |
| `build-image-docker-no-repo` | Docker build without GitOps (wrapper). Passes `resource_type` and `release_branch` to base |
| `build-image-docker-automya-front` | Frontend build with DEV tag restriction (wrapper). Passes `resource_type` and `release_branch` to base |
| `deploy-app` | GitOps deployment with K8s rollout restart. Supports Deployments (default) and CronJobs via `-r cronjob` flag |
| `sync-config` | Sync config files to GitOps ConfigMaps |
| `java-test` | Run Gradle tests |
| `npm-test` | Run npm tests |
| `sast-scan` | Trivy vulnerability scanning via SBOM (pinned to v0.28.0) |
| `publish-java-artifacts` | Publish to artifact repository |
| `publish-components` | Publish npm packages to GitHub Packages |

## Internal Actions

| Action | Purpose |
|--------|---------|
| `build-context-determine` | Determine build context (branch, tag, event type) |
| `build-report-message` | Generate build report messages |
| `create-pr` | Generic PR creation with auto-merge |
| `deploy-context-init` | Initialize deployment context |
| `deploy-report` | Generate deployment report messages |
| `deploy-select-manifest` | Select correct manifest path for deployment |
| `deploy-validate-context` | Validate deployment parameters (env, tag, resource type) |
| `docker-build-push` | Docker build and push (no eval, uses arrays) |
| `gitops-pr` | Update manifest and create GitOps PR (supports Deployment and CronJob yq paths) |
| `k8s-rollout-restart` | Kubernetes rollout restart |
| `notify` | PR comments and Google Chat notifications (uses jq for JSON) |
| `parse-comment` | Parse PR comment commands (supports `-t`, `-e`, `-b`, `-r` flags) |
| `setup-gcp` | GCP authentication with Workload Identity Federation |
| `setup-java-gradle` | Java and Gradle environment setup |
| `setup-yq` | Cross-platform yq installation |
| `sync-context-determine` | Determine sync context |
| `sync-context-init` | Initialize sync context |
| `sync-report` | Generate sync report messages |
| `sync-set-env` | Set environment variables for sync |
| `sync-update-configmap` | Update ConfigMap in GitOps repo |
| `trivy-report` | Generate Trivy scan report |
| `util-normalize-repo` | Normalize repository name format |

## Usage Pattern

Actions are referenced from other repos via:
```yaml
uses: Automya/CI-CD-template/actions/<action-name>@main
```

Internal actions (not for external use):
```yaml
uses: Automya/CI-CD-template/internal/<action-name>@main
```

## Shell Script Conventions

- All scripts use `set -euo pipefail` for strict error handling
- JSON encoding uses `jq` (not manual sed escaping)
- Timeouts on curl: `curl --max-time 30`
- Cross-platform compatibility for sed and yq
- No `eval` usage - arrays for command construction

## Testing Changes

There are no automated tests. Validate changes by:
1. Creating a test workflow in a consuming repository
2. Testing the PR comment trigger patterns: `build`, `deploy`, `sync`

## Keeping CLAUDE.md Up to Date

**IMPORTANT:** Every change to this repository MUST be reflected in this `CLAUDE.md` file. This includes:

- **New actions**: Add to the "Public Actions Reference" or "Internal Actions" table.
- **Removed actions**: Remove from the corresponding table.
- **Renamed actions or changed inputs/outputs**: Update the relevant table entry and any references.
- **New conventions or patterns**: Document in "Shell Script Conventions" or create a new section.
- **New tools or scripts**: Add to the "Tools" section with architecture details.
- **Changes to architecture or workflows**: Update "Architecture" and "Key Workflows" sections.
- **New skills relevant to the repo**: Add to "Skills Reference" section.

If you are unsure whether a change affects CLAUDE.md, err on the side of updating it.

## Tools

### Workflow Sync Tool (`tools/workflow_sync/`)

Interactive terminal application to synchronize GitHub Actions workflows from a source repository to all repositories in an organization with a specific topic.

**Key Features:**
- Interactive terminal UI with ANSI colors
- Token persistence (`~/.workflow-sync-config` with 600 permissions)
- Auto-merge PRs with retry on conflicts
- Automatic deletion of obsolete workflows (files in destination not in source)
- Skip repos without `.github/workflows` folder
- Dry-run mode for previewing changes
- Parallel execution support
- Standalone executable (no Python required to run)

**Usage:**
```bash
# Build standalone executable
cd tools/workflow_sync
./build.sh

# Run the app
./dist/WorkflowSync
```

**Architecture:**
- `interactive.py` - Terminal UI application (entry point)
- `clients/github_client.py` - GitHub API wrapper with rate limiting and retry
- `services/sync_service.py` - Sync logic with PR creation and auto-merge
- `models.py` - Data classes (SyncConfig, SyncResult, FileChange)
- `exceptions.py` - Custom exceptions (ValidationError, WorkflowSyncError)
- `validators/input_validator.py` - Input validation with regex patterns
- `build.sh` / `WorkflowSync.spec` - PyInstaller packaging

### SmartFridge Deploy Tool (`tools/smartfridge_deploy/`)

Interactive terminal application to deploy SmartFridge Java application to vending machines via SSH through a jump host (sistemas-sp).

**Key Features:**
- SSH via jump host (local -> sistemas-sp -> vending machine)
- SFTP file transfer through jump host
- Automatic backup of JAR and application.properties with date suffix
- Service stop/start with interactive confirmation
- Startup verification by watching logs for marker string
- Automatic rollback on failure (restores JAR, properties, restarts service)
- Config persistence (`~/.smartfridge-deploy-config` with 600 permissions)
- Connection test utility (SSH, disk space, service status, log file)
- Standalone executable via PyInstaller

**Usage:**
```bash
# Run directly
cd tools/smartfridge_deploy
python3 interactive.py

# Build standalone executable
./build.sh
./dist/SmartFridgeDeploy
```

**Architecture:**
- `interactive.py` - Terminal UI application (entry point)
- `clients/ssh_client.py` - SSH/SFTP client with jump host support (paramiko)
- `services/deploy_service.py` - Deploy orchestration with rollback
- `models.py` - Data classes (DeployConfig, VMInfo, JumpHostConfig, DeployResult)
- `exceptions.py` - Custom exceptions (DeployError hierarchy)
- `validators/input_validator.py` - Input validation (hostname, VM name, files, SSH key)
- `build.sh` / `SmartFridgeDeploy.spec` - PyInstaller packaging

**Deploy flow per VM:**
1. Connect (verify SSH via jump host)
2. Upload JAR (SFTP to jump host, then scp to VM)
3. Backup JAR (mv SmartFridge.jar SmartFridge.jar.YYYYMMDD)
4. Install JAR (mv + chown)
5. Backup properties (cp application.properties application.properties_YYYYMMDD)
6. Upload properties (SFTP + chown)
7. Check idle (review recent logs)
8. Stop service (with user confirmation)
9. Start service
10. Verify startup (tail -f log, wait for "Started SmartFridgeApplication")

## Skills Reference

Use the following skills (slash commands) when working on this repository:

### GitHub Actions (Primary)

| Skill | When to Use |
|-------|-------------|
| `/github-actions-validator` | Validating any `action.yml` file (33 files in `actions/` and `internal/`). Use after modifying actions to check syntax, inputs/outputs consistency, and best practices. |
| `/github-actions-generator` | Creating new composite actions, adding steps to existing actions, or generating workflow files for consuming repositories. |
| `/ci-cd` | Designing CI/CD pipeline flows, troubleshooting pipeline failures in consuming repos, optimizing build performance, and debugging action orchestration issues. |

### Shell Scripts (Embedded in Actions)

| Skill | When to Use |
|-------|-------------|
| `/bash-script-validator` | Validating inline bash scripts within `action.yml` files and `tools/workflow_sync/build.sh`. Check for `set -euo pipefail`, proper quoting, and shellcheck compliance. |
| `/bash-script-generator` | Generating new bash logic for action steps (e.g., parsing, API calls with curl, JSON handling with jq). |

### Docker & Containers

| Skill | When to Use |
|-------|-------------|
| `/dockerfile-validator` | Reviewing Dockerfiles in consuming repositories when troubleshooting build failures from `docker-build-push` action. |
| `/dockerfile-generator` | Helping consuming repositories create Dockerfiles compatible with the build actions (multi-stage builds, build args for MAVEN credentials). |

### Kubernetes

| Skill | When to Use |
|-------|-------------|
| `/k8s-troubleshooter` | Debugging deployment issues triggered by `deploy-app` action (rollout restart failures, pod crashes after deploy). |
| `/k8s-yaml-generator` | Generating Kubernetes manifests compatible with the GitOps flow (patches, overlays for kustomize). |
| `/k8s-yaml-validator` | Validating manifest patches used in `gitops-pr` and `deploy-select-manifest` actions. |

### Code Quality

| Skill | When to Use |
|-------|-------------|
| `/code-reviewer` | Reviewing changes to Python code in `tools/workflow_sync/` or reviewing action.yml modifications before merging. |

### Monitoring & Observability

| Skill | When to Use |
|-------|-------------|
| `/monitoring-observability` | Designing notification strategies (Google Chat webhooks, PR comments) and troubleshooting notification delivery in `notify` action. |

### Skill Selection by Task

| Task | Primary Skill | Secondary Skill |
|------|---------------|-----------------|
| New composite action | `/github-actions-generator` | `/bash-script-generator` |
| Fix broken action | `/github-actions-validator` | `/bash-script-validator` |
| Debug failed workflow run | `/ci-cd` | `/github-actions-validator` |
| Modify Docker build logic | `/github-actions-validator` | `/dockerfile-validator` |
| Fix deployment action | `/k8s-troubleshooter` | `/ci-cd` |
| Update workflow_sync tool | `/code-reviewer` | `/bash-script-validator` |
| Troubleshoot GitOps PR | `/ci-cd` | `/github-actions-validator` |
