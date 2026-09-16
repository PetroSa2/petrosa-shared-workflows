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


