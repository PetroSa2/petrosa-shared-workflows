# Agent instructions: petrosa-shared-workflows

Reusable GitHub Actions workflows, and the small scripts behind them, used by the Petrosa service repositories. Ecosystem rules (data pillars, commit and PR process, wording, memory) are in the umbrella [AGENTS.md](https://github.com/PetroSa2/petrosa/blob/main/AGENTS.md); this file covers this repository only.

## Layout

- `.github/workflows/ci-pipeline.yml`: the CI pipeline every service calls.
- `.github/workflows/agent-instructions.yml`: checks a repo's agent instruction files.
- `.github/workflows/external-wording.yml`: checks PR text and added lines against the organisation's term list.
- `.github/workflows/validate.yml`: lints the workflows and runs the tests of this repo.
- `scripts/`: the check scripts used by the two workflows above.
- `tests/`: pytest tests for those scripts.
- `docs/runbooks/hung-runner-mitigation.md`: runbook for hung self-hosted runners.

## Before a PR

- Run `python3 -m pytest tests -q`.
- `.github/workflows/validate.yml` runs yamllint and actionlint on `.github/workflows/`; run the same tools locally if you change a workflow.

## Rules

- Callers pin these workflows by commit SHA. Do not change a workflow's inputs in a breaking way without updating the callers.
- Commits use Conventional Commits; branches are `{type}/{issue-number}-{slug}`; never merge with `--admin`.
- The wording check reads its term list from an organisation variable on purpose: never write the terms into this repository.
- Text that leaves the repository (PR titles and bodies, commit messages, code comments) uses generic roles such as Agentic Developer, never the upstream workflow engine's name or persona names.
