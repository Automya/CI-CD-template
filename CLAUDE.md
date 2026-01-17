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
2. **Deploy Flow**: PR comment triggers (`deploy -t <tag> -e <env>`) → parse → GitOps PR → K8s rollout restart → notify
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
| `build-image-docker` | Base Docker build action with full configuration |
| `build-image-docker-gcp` | Docker build with GitOps integration (wrapper) |
| `build-image-docker-no-repo` | Docker build without GitOps (wrapper) |
| `build-image-docker-automya-front` | Frontend build with DEV tag restriction (wrapper) |
| `deploy-app` | GitOps deployment with K8s rollout restart |
| `sync-config` | Sync config files to GitOps ConfigMaps |
| `java-test` | Run Gradle tests |
| `npm-test` | Run npm tests |
| `sast-scan` | Trivy vulnerability scanning via SBOM (pinned to v0.28.0) |
| `publish-java-artifacts` | Publish to artifact repository |
| `publish-components` | Publish npm packages to GitHub Packages |

## Internal Actions

| Action | Purpose |
|--------|---------|
| `setup-gcp` | GCP authentication with Workload Identity Federation |
| `setup-yq` | Cross-platform yq installation |
| `docker-build-push` | Docker build and push (no eval, uses arrays) |
| `notify` | PR comments and Google Chat notifications (uses jq for JSON) |
| `parse-comment` | Parse PR comment commands |
| `gitops-pr` | Update manifest and create GitOps PR |
| `create-pr` | Generic PR creation with auto-merge |

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
