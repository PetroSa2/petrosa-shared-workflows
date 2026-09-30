# Petrosa Shared Workflows

Reusable GitHub Actions workflows shared across Petrosa service repositories.

## Available Workflows

### CI Pipeline (`ci-pipeline.yml`)

Unified CI pipeline for Petrosa Python microservices.

**Usage:**
```yaml
jobs:
  pipeline:
    name: CI Pipeline
    uses: PetroSa2/petrosa-shared-workflows/.github/workflows/ci-pipeline.yml@main
    with:
      service-name: 'your-service'
      image-name: 'yurisa2/petrosa-your-service'
      python-version: '3.11'
      skip-docker-build: true
    secrets: inherit
```

**Inputs:**
- `service-name` (required): Name of the service
- `image-name` (required): Docker image name
- `python-version` (optional, default: `3.11`): Python version
- `coverage-threshold` (optional, default: `40`): Min coverage %
- `skip-lint`, `skip-test`, `skip-security`, `skip-docker-build` (optional booleans)

## Job timeouts

Every job in `ci-pipeline.yml` and `validate.yml` has an explicit
`timeout-minutes` (defensive; see [PetroSa2/petrosa_k8s#1064](https://github.com/PetroSa2/petrosa_k8s/issues/1064)).
A hung step now self-terminates instead of pinning a scarce
`petrosa-org-runners` slot for the 6h job default. See
[`docs/runbooks/hung-runner-mitigation.md`](./docs/runbooks/hung-runner-mitigation.md)
for the log signature, root-cause investigation, and manual mitigation.

### Agent Instructions Check (`agent-instructions.yml`)

Fails a PR when a repository has no `AGENTS.md`, keeps vendor-specific instruction files (`.cursorrules`, `.cursor/`,
`.github/prompts/`, ...), has pointer files (`CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`) that are
not short pointers, or when `AGENTS.md` names a `make` target or a path that does not exist.

```yaml
jobs:
  instructions:
    uses: PetroSa2/petrosa-shared-workflows/.github/workflows/agent-instructions.yml@<sha>
```

### External Wording Check (`external-wording.yml`)

Fails a PR whose title, body, commit messages or added lines contain a term from the organisation Actions variable
`EXTERNAL_WORDING_TERMS` (one term per line or comma-separated; `word:term` matches a whole word). The terms are never
printed. An empty variable makes the check pass with a notice.

```yaml
jobs:
  wording:
    uses: PetroSa2/petrosa-shared-workflows/.github/workflows/external-wording.yml@<sha>
```
