# Evidence-Backed Portfolio Maintenance

## Actual Activation

As of 2026-10-28, `daily-maintenance.yml` is published and GitHub reports its state
as active in all seven gallery reference repositories. The completed deployment
rollout pins maintenance, delivery and web deployment proof to controller revision
`e205849fa00bfcafb83b1bc645ae26e9ca378b47`. Configuration updates use ordinary
protected PRs, never direct main pushes or administrator bypass.
The controller's [cross-platform CI40660929643](https://github.com/Sushant-Nemade/autonomous-quality-redteam-harness/actions/runs/40660929643)
passed 69 tests on Linux Python3.12/3.13 and Windows Python3.13, plus lint, the
existing type gate, dependency audits, packaging and container checks.
This security maintenance pin includes `uv`0.13.4; the first complete pilot below
ran the same proposal/model policy before that build-tool-only update.
The fixed toolchain was subsequently exercised end to end by
[pilot40602640097](https://github.com/Sushant-Nemade/TravelBrain/actions/runs/40602640097),
again completing 27 tests, four integration cases, 1,000 serial journeys and real
inference with a no-safe-change outcome. No PR or improvement was manufactured.

The shared schedule is **12:00 noon Europe/Berlin**, not midnight or 09:00.
An epoch-based round robin selects one project per Berlin calendar day:

| First selected date | Project | Approved proposal function | Workload profile |
| --- | --- | --- | --- |
| 2026-10-28 | ai-blog-publisher | StorageHistory.get_recent_history | 1,000 serial approved-publication/integrity journeys |
| 2026-10-29 | gitpulse | Person.__post_init__ | 1,000 serial local state/health API journeys |
| 2026-10-30 | Doclify | clean_cache | 1,000 serial offline draft/approval/publication journeys |
| 2026-10-31 | MarketInsight | evidence_summary | 1,000 serial fixture-provider research/save/reopen/clear journeys |
| 2026-11-01 | TravelBrain | truncate | 1,000 serial local itinerary API journeys |
| 2026-11-02 | airbnb-price-workbench | vector | 1,000 serial actual local ONNX API contract journeys |
| 2026-11-03 | boston-housing-workbench | Scenario.vector | 1,000 total ONNX journeys, max16 workers |

The sequence repeats every seven days. Other scheduled callers perform selection
and do not run a second project. Explicit operator `pilot=true` dispatches are
separate diagnostic runs with separate durable keys, not daily-selection evidence.
All future starts are best effort: GitHub can delay/drop schedules and disable
public scheduled workflows after inactivity. No exact-start or uptime SLA is promised.

## Owner-Authorized Unattended Delivery

On 2026-10-28 the owner explicitly authorized removal of routine manual PR approval.
All seven repositories now have `MAINTENANCE_AUTO_MERGE=1`, protected main branches
with the exact existing independent CI jobs required, strict up-to-date bases,
administrator enforcement, PR-only/linear history, conversation resolution and
no force pushes/deletions. There were no existing protection rules to weaken.

The trusted completion hook executes only pinned controller code, never candidate
code with write credentials. It verifies the original successful maintenance run,
same-repository bot PR, exact head/base SHAs, two approved paths, complete real
CI job results, demonstrated RED/GREEN evidence and unresolved-finding absence.
Only then can it squash-merge the exact candidate without another owner approval.
Failed/stale candidates are rejected/closed, allowing a future scheduled fresh attempt.

Approved concrete work may include a controller-owned immutable regression. That
test is executed against unchanged source before the author runs. Already-green
tests result in no change; observed RED becomes the author's evidence, and a model
claim that the defect is already fixed cannot replace the actual test result.
The seven controller pin updates themselves used protected PRs and native auto-merge
after every required check, without temporarily disabling protection or admin bypass.

The merged main SHA receives a separately dispatched full CI run. Six web apps
deploy only successful current-main owner CI results from push or workflow dispatch.
Each Pages workflow also accepts a `verified_ci_run_id` dispatch. A separate
read-only pinned proof job checks the owned CI workflow, event, exact current main
SHA and every required job; missing, duplicated, skipped or failed jobs reject it.
The build checks out only that attested SHA and rechecks main immediately before
deployment. A newer main can be reconciled only after proving it descends from
the original merge, then independently verifying its own complete CI.
Doclify automatically builds verified wheel/source artifacts; no PyPI publishing
identity is configured and no PyPI publication is claimed.

Every project also reconciles delivery state at `17 */6 * * *` Europe/Berlin;
this is housekeeping, not a second daily improvement selection. It catches missed
CI events, retries missing post-merge dispatch at most twice and failed main CI
once. It explicitly dispatches Pages when completion callbacks are suppressed,
with at most two dispatch attempts and one retry of a failed deployment. A green
workflow with a skipped deployment job is not recorded as deployed. Failed
verification does not bypass deployment. Global/per-project stop
controls still apply. Infrastructure, permissions or safety failures can stop a
run; this is not a promise that every possible failure can repair itself.

Earlier no-change pilots below prove actual execution, not automatic merging.
The following later pilot demonstrates a real generated change and protected merge.

## Executed Automatic Merge Proof

- [Live pilot40621360289](https://github.com/Sushant-Nemade/TravelBrain/actions/runs/40621360289)
  generated the negative-truncation-budget repair from source
  `985474bece390577b049a0cbe28d1a1829b76de5`. Baseline 27/27 tests and 4/4 integration
  cases passed. The immutable regression demonstrated RED: one failure and one pass,
  followed by GREEN 2/2. Final 29/29 tests and 4/4 integration cases passed.
- Both before-change and after-change workloads ran 1,000 serial journeys with zero
  failures. These are local regression journeys, not 1,000 concurrent external users.
  The separately pinned 7B model reviewer approved the candidate without findings.
- [Bot PR5](https://github.com/Sushant-Nemade/TravelBrain/pull/5) contained exact candidate
  `870d2fc00f610678f20845568960f3336262173a`.
  [Independent candidate CI40622204667](https://github.com/Sushant-Nemade/TravelBrain/actions/runs/40622204667)
  passed every required Linux, Windows and container job.
- [Trusted reconciliation40623354813](https://github.com/Sushant-Nemade/TravelBrain/actions/runs/40623354813)
  automatically performed the protected merge at2026-10-28T02:51:42Z, producing
  `c79ed99baa98235fa0717b803a1c32feb93228cc`. No routine owner merge approval was used.
- [Automatically dispatched main CI40623391622](https://github.com/Sushant-Nemade/TravelBrain/actions/runs/40623391622)
  passed in full. Its suppressed Pages callback exposed the explicit-promotion
  gap fixed by the current controller; successful main CI alone was not called a deployment.
- The [durable delivery report](https://github.com/Sushant-Nemade/TravelBrain/blob/maintenance-reports/runs/maintenance-2026-10-28-pilot-40621360289.json)
  retains `merged_sha`, separately attested `verified_sha`, `main_ci_run_id` and
  `pages_run_id`. A later protected workflow-only rollout changes the current main
  SHA without rewriting the original agent merge or earlier rejected pilot evidence.
- The later protected workflow-only rollout produced current main
  `a5c793ca3e912dbeb8405edfdfaef78017ead0ee`, a verified descendant of the agent merge.
  [Full main CI40662028220](https://github.com/Sushant-Nemade/TravelBrain/actions/runs/40662028220)
  and [proof-gated Pages40662530170](https://github.com/Sushant-Nemade/TravelBrain/actions/runs/40662530170)
  both succeeded. [Trusted housekeeping40662759511](https://github.com/Sushant-Nemade/TravelBrain/actions/runs/40662759511)
  verified the actual deployment job and recorded **deployed** in the durable report.
  During setup this same six-hour scheduled job was dispatched for immediate
  verification; routine future operation needs no owner start or approval.

## Earlier Executed Proof

- [Actual model runtime40589962908](https://github.com/Sushant-Nemade/autonomous-quality-redteam-harness/actions/runs/40589962908): pinned 1.12GB Qwen GGUF checksum verified; pinned llama.cpp compiled;
  real schema-constrained CPU inference succeeded in a non-root, network-none container.
- [Complete TravelBrain pilot40596897772](https://github.com/Sushant-Nemade/TravelBrain/actions/runs/40596897772): source `161653e941a7f941da1012c71595f8e5a0b3dae4`; 27/27 existing tests and 4/4 integration
  cases executed; 1,000/1,000 serial itinerary journeys passed with zero failures,
  errors or skips. P95~28ms/P99~30ms on that runner, not production network latency.
  Real planning and author inference ran. The author corrected the planner's mistaken
  non-string defect claim and returned **no-safe-change**. No regression, PR, security
  remediation or deployment is claimed for this pilot. The author/reviewer correction
  highlights the model's limitations, not an autonomous-quality guarantee.
- [Durable pilot report](https://github.com/Sushant-Nemade/TravelBrain/blob/maintenance-reports/latest.json): inspect source SHA, observed cases, measured profile, model-response provenance
  and actual outcome. Earlier failed diagnostic runs remain recorded; they were not
  rewritten into successful improvement claims.
- Controller integration tests execute real failing and passing temporary-project
  pytest subprocesses; Docker, model and workload boundaries there are explicitly
  fixture substitutes. These test orchestration, not live model quality or all
  seven deployed workload adapters. Only TravelBrain's complete unattended path
  and Boston's separate real load run were exercised before this activation.

## Unattended Pipeline

1. A read-only preflight checks owner/repository, trusted main SHA, global/per-repo
   stop controls, Berlin selection, durable date marker and pending maintenance PRs.
2. A separate read-only job copies tracked source, builds the reviewed dependency
   image, executes the actual existing test suite plus a reviewed integration slice,
   and runs the project's bounded local workflow profile.
3. A pinned offline model returns a concise defect/no-change decision. Only a
   defensible candidate proceeds to function-only code plus a new regression file.
4. The new test runs against unchanged production source first. RED requires exit1,
   observed behavioral failures, no collection/environment errors and no skips.
5. Apply only the reviewed function-body change. Run GREEN, then use a fresh model
   context to review security/correctness risks. At most two repairs; demonstrated
   regression and all existing tests remain immutable. Unresolved findings reject it.
6. Rerun existing tests, integration and workload; recheck source/test inventory.
   Candidates need the existing passed-test count plus the new demonstrated cases.
7. A separate trusted publisher validates provenance, paths, function scope,
   observed gates and review outcome. It rejects main drift or duplicates, opens a
   normal PR, and explicitly dispatches ordinary project CI on that branch.
8. The separately trusted automatic-delivery guard validates the exact candidate
  and all independent CI jobs against protected main. Authorized bounded changes
  merge without routine human approval. Full main CI runs separately, and only its
  successful current SHA can deploy. No self-review, test weakening, force push or
  bypass of protected checks is permitted.

No safe change, rejected regression and blocked baseline are valid report outcomes,
not manufactured improvements. Existing provider tests use documented mocks and
fixtures; no paid/cloud API, private account data or live financial/weather endpoint
is stress-tested. Cloudflare's four older static snapshots remain manually updated;
post-merge GitHub Pages does not automatically refresh that separate collection.
Doclify is a CLI release, not a hosted app; this system does not autonomously publish
a new PyPI/release version. Existing project CI remains the package/browser gate.

## Isolation, Budgets And Trust

- Model: Qwen2.5-Coder-1.5B-Instruct-GGUF, Apache-2.0, immutable revision
  `f86cb2c1fa58255f8052cc32aeede1b7482d4361`; exact Q4_K_M SHA-256
  `cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046`.
- Separate reviewer, live-tested on TravelBrain's approved repair: Qwen2.5-Coder-7B-Instruct-GGUF,
  Apache-2.0, immutable revision `13fb94bfda8c8cf22497dc57b78f391a9acb426a`,
  file size4,683,073,536 bytes, SHA-256
  `509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c`.
  It replaces the repeatedly contradicted smaller reviewer, not the real tests.
  Its rollout must still pass protected project CI. Full upstream license and
  provenance are retained under maintenance/third-party and in the verified cache.
- Runtime: llama.cpp `a919179942157e0554f92c1c6f31ac874f50b40a`, MIT.
  No paid AI credential or inference API is used. GitHub compute/storage policies
  still apply; standard public-runner eligibility is not a permanent billing promise.
- Generated code and model run non-root, no network, read-only root/source,
  no capabilities, no-new-privileges, max4GB RAM for actor/project tests or8GB for
  the separate7B reviewer, 2CPU/128PIDs, bounded tmpfs and
  output/file limits. No GitHub token, Docker socket or provider secret is mounted.
- Max7 model calls, 1,700 output tokens each, 8,192 context tokens, two repairs.
  Per subprocess deadlines plus a 45-minute budget checked between stages and a 55-minute job cap
  bound failure. Cold model/engine download/build can dominate run time.
- Only one approved existing Python function and one date-named new test may be
  proposed. No imports/signatures, other functions, existing tests, dependency locks,
  workflows, auth, data, model weights, licenses or spending-policy edits.
- Approved modules remain within the owner's narrowly authorized automatic scope.
  Changes outside that scope are rejected rather than expanded silently. Sandbox isolation limits impact;
  static checks/JUnit are not proof that arbitrary generated code cannot misbehave
  within its process. Independent CI and the separate trusted guard are still mandatory.
- Automated model review, including a separate larger reviewer, is not independent
  human pentest certification or a substitute for expert review. False defect claims,
  rejected repairs and no-change days remain possible; no passing result is fabricated.

Six profiles are **serial regression repetitions**, with concurrency1 and no
independently counted HTTP request total. Boston uses max16 active local journeys,
with actual status/latency/range/hash checks. Neither means 1,000 simultaneous humans,
browser processes, external users or a production capacity SLA. Python-only memory
figures exclude native ONNX/RSS; serial profiles report CPU time, not load saturation.

## Stop, Recover And Review

Global stop: change [maintenance/control.json](../maintenance/control.json) to
`{"paused": true}` on the controller's main branch. All pinned callers read this
current owner-controlled switch and fail closed if it is unavailable/invalid.
An explicit pilot cannot bypass it. A run already executing must be cancelled
separately in Actions; the switch prevents new execution.

Per-project stop: set repository Actions variable `MAINTENANCE_DISABLED=1`, or disable
that repository's `Daily Reviewed Maintenance` workflow. No local Windows Task
Scheduler job was installed by this implementation; the old fixture registration
script is not an operational prerequisite or substitute for this cloud schedule.

Reports live on each project's `maintenance-reports` branch as `latest.json`, a
human-readable README, and versioned date/run-key records. Ordinary scheduled keys
are deduplicated and per-project runs serialized. A pending maintenance PR prevents
another proposal. GitHub artifacts retain detailed evidence for30days; durable
sanitized reports remove test log tails and preserve counts/hashes/outcomes.

The 15:00 Europe/Berlin controller monitor checks the selected day's report and
opens a deduplicated owner issue for missing/blocked/rejected outcomes. Global pause
suppresses missed-run alerts. This monitor shares GitHub's scheduler and cannot
guarantee detection of its own outage; owner monitoring remains necessary.

For a failed run, inspect its actual report before retrying. Do not equate green
workflow plumbing with a passed project outcome. Manual pilots use distinct keys;
they do not erase the first diagnostic record. Resume ordinary selection with
`pilot=false`; preserve evidence rather than force-update date markers. Review
and pin a new controller SHA in all seven callers together when changing policy
or the registry. Never switch callers to mutable `@main` for convenience.