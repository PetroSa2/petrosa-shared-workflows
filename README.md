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

---

### Request Copilot Review (`request-copilot-review.yml`)

Requests a GitHub Copilot code review after CI passes. Implements the draft-PR gate
(skips draft PRs) and per-PR dedup (no re-request if Copilot already reviewed).

**Caller pattern** (thin ~25-line file in each service repo):

```yaml
name: Request Copilot Review
on:
  workflow_run:
    workflows: ["CI Checks"]
    types: [completed]
  workflow_dispatch:
    inputs:
      pull_number:
        description: 'PR number to request Copilot review for'
        required: true
        type: number
jobs:
  request-copilot-review:
    if: >
      (github.event_name == 'workflow_dispatch') ||
      (github.event.workflow_run.conclusion == 'success' &&
      github.event.workflow_run.event == 'pull_request' &&
      github.event.workflow_run.head_repository.full_name == github.repository)
    permissions:
      pull-requests: write
      contents: read
    uses: PetroSa2/petrosa-shared-workflows/.github/workflows/request-copilot-review.yml@main
    with:
      dispatch-pull-number: ${{ github.event.inputs.pull_number || '' }}
    secrets: inherit
```

**Inputs:**
- `dispatch-pull-number` (optional): PR number when caller was triggered by `workflow_dispatch`. Leave empty for `workflow_run` callers.

**Behavior:**
- Draft PRs are skipped. When the PR is marked ready-for-review, CI re-fires (via `ready_for_review` in `ci-checks.yml`) and Copilot is then requested automatically.
- Per-PR dedup: if Copilot has already reviewed the PR (any non-dismissed review), the request is skipped.
- 422 responses from `requestReviewers` are swallowed (Copilot unavailable or already queued).

**F3 requirement:** Caller job MUST declare its own `permissions:` block (`pull-requests: write`, `contents: read`). `secrets: inherit` does not widen `GITHUB_TOKEN` permissions on `workflow_run`-triggered runs.

---

### Copilot Review Gate (`copilot-review-gate.yml`)

Enforces merge blocking: polls until Copilot submits a review, then verifies all
non-outdated Copilot-started review threads are resolved. Posts a `copilot-review`
check_run directly on the PR head SHA (branch protection looks at PR head checks).

**Caller pattern** (thin ~25-line file in each service repo):

```yaml
name: copilot-review
on:
  workflow_dispatch:
    inputs:
      pull_number:
        description: 'PR number to gate'
        required: true
        type: number
  workflow_run:
    workflows: ["CI Checks"]
    types: [completed]
jobs:
  copilot-review:
    if: >
      github.event_name != 'workflow_run' ||
      (github.event.workflow_run.conclusion == 'success' &&
       github.event.workflow_run.event == 'pull_request')
    permissions:
      contents: read
      pull-requests: read
      checks: write
    uses: PetroSa2/petrosa-shared-workflows/.github/workflows/copilot-review-gate.yml@main
    with:
      dispatch-pull-number: ${{ github.event.inputs.pull_number || '' }}
    secrets: inherit
```

**Inputs:**
- `dispatch-pull-number` (optional): PR number when caller was triggered by `workflow_dispatch`. Leave empty for `workflow_run` callers.

**Behavior:**
- Polls up to 20 minutes for a Copilot review.
- Fails if any non-outdated, unresolved Copilot-started review thread exists.
- Creates a `copilot-review` check_run on the PR head SHA so branch protection sees the result on the correct commit (#559).
- `cancel-in-progress: false` — never cancels a polling run in flight (#362).

**F3 requirement:** Caller job MUST declare its own `permissions:` block (`contents: read`, `pull-requests: read`, `checks: write`).

**Branch protection:** The required status check name is `copilot-review` (matches the job name). See `petrosa_k8s/docs/COPILOT_REVIEW_ENFORCEMENT.md`.

**Do NOT add `pull_request_review` to the caller's `on:` triggers** — the Copilot Bot account triggers the fork-pr-contributor-approval banner (#559). Trigger from `CI Checks` only.
