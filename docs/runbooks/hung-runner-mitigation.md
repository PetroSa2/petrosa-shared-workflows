# Runbook: Hung ARC Runner / CI Job Timeout

**Tracking:** [PetroSa2/petrosa_k8s#1064](https://github.com/PetroSa2/petrosa_k8s/issues/1064)

## When to use this

A CI job step is stuck (no output progress) and pinning a scarce
`petrosa-org-runners` slot, or you're auditing why the org-wide CI queue
backlog isn't draining.

## Signature (how to recognize a hung runner)

- Runner pod CPU holds steady around ~800m with **no** test/lint/scan
  output advancing for several minutes.
- `kubectl -n arc-systems logs -l app.kubernetes.io/component=runner-scale-set-listener`
  shows `"assigned job": 0, "jobsCompleted": 0` while a pod in
  `petrosa-runners` has been `Running` far longer than any CI stage should
  take.
- Runner pod logs show repeated blocks (e.g. `Well known directory 'Bin'...`)
  with **every line printed twice**.

## Root cause of the doubled log lines (investigated 2026-09-16)

The `AutoscalingRunnerSet` carries a command override (annotated
`petrosa.io/command-override-reason`, added 2026-04-03) that wraps the
runner entrypoint as:

```
bash -c "/home/runner/run.sh 2>&1 | tee /proc/1/fd/1; exit ${PIPESTATUS[0]}"
```

`tee` duplicates every line the runner emits (once via its own stdout,
once via the `tee` copy to `/proc/1/fd/1`), which is what produces the
"printed doubled" pattern in `kubectl logs` output — **this is a benign
logging artifact of the command override, not evidence of a restart
loop or a stuck worker.** Live inspection on 2026-09-16 (a single running
`petrosa-org-runners` pod, listener healthy, `arc-controller` healthy, ARC
scaling 1↔4 correctly per `minRunners`/`maxRunners`) found the dispatch
path itself functioning normally; no live repro of an actual hung *job*
(as opposed to an idle listening runner) was available at investigation
time to trace which specific step triggers extended `Well known directory`
looping under load. **Per the ticket's AC, this is documented as
time-boxed-only** (see timeouts below) rather than root-caused further —
if the loop recurs, capture `kubectl -n petrosa-runners logs <pod>` around
the hang and diff against a healthy run to identify the offending step.

## Mitigation 1 (defensive, now in place): `timeout-minutes`

Every job in `ci-pipeline.yml` and `validate.yml` now declares an explicit
`timeout-minutes`, sized generously above real observed execution
durations (lint 20m, test 45m with a 25m pytest step sub-cap, security-scan
30m, build-and-push 40m, pipeline 10m, validate 15m) — all well under the
360m (6h) GitHub Actions default. **This bounds only in-progress execution
time; GitHub does not start the clock until the job is assigned a runner**,
so ARC queue backlog is unaffected by this change (by design — the queue
problem is capacity, see Mitigation 3).

> **Caller adoption note:** per petrosa_k8s#1053, all 7 service repos
> SHA-pin this repo (`uses: .../ci-pipeline.yml@<sha>`). This fix only
> takes effect for a caller once that caller's pin is bumped to (or past)
> this commit — re-pinning each caller is tracked as a fast-follow, not
> done as part of this PR.

## Mitigation 2 (manual, interim): delete the stuck pod

```bash
kubectl --kubeconfig k8s/kubeconfig.yaml --insecure-skip-tls-verify=true \
  -n petrosa-runners delete pod <hung-runner-pod-name>
```

ARC's `EphemeralRunnerSet` recycles the slot automatically; the job the
stuck runner held will be re-queued and picked up by the next available
runner.

## Mitigation 3 (capacity — pre-existing, out of scope for this ticket)

The single-node ARC pool is capped `maxRunners: 4` (annotated
`petrosa.io/max-runners-cap-reason`) because the underlying node is a
single 6-CPU host. Raising the cap requires freeing node capacity first
(see petrosa_k8s#1010, #1012/PR#1045, #1014/PR#1067, #1076) — this is
the dominant source of the 30–100 minute queue waits observed in prior
incidents, **not** a job-dispatch defect. Live check on 2026-09-16: node
CPU requests at 65% allocatable (down from #1076's 87%), zero runs
queued org-wide — headroom has genuinely improved since prior capacity
work landed.
