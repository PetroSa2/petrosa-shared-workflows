# Runbook: Hung ARC Runner or CI Job

Use this runbook when a CI job stops producing output while occupying a scarce
self-hosted runner, or when the runner queue stops draining.

## Identify the condition

- A job step produces no new test, lint, scan, or build output for several minutes.
- The runner listener reports no completed work while a runner remains active beyond the
  expected duration of its CI stage.
- Runner logs repeat the same startup or directory messages without advancing the job.

Repeated log lines alone do not prove that a worker is stuck. Confirm that the job has no
progress before deleting a runner.

## Defensive timeout

The reusable workflows set explicit job and step timeouts below GitHub Actions' default limit.
This bounds an in-progress job after it is assigned to a runner; it does not reduce time spent
waiting in the runner queue. A caller receives these limits only after updating its pinned
workflow reference to a commit that contains them.

## Manual recovery

1. Capture the affected job URL, runner name, pod name, and the surrounding log output.
2. Confirm that the job is not still making progress.
3. Delete the stuck runner pod through the cluster's normal operator or GitOps procedure.
4. Confirm that the job is re-queued and that a replacement runner accepts work.
5. Escalate recurring hangs with the captured job and runner evidence; do not treat duplicated
   output as a root cause without a reproducible stalled job.

## Capacity note

Queue delay is separate from job execution timeout. If jobs are queued while assigned runners
are healthy, inspect runner capacity and node resources before changing workflow timeouts.
