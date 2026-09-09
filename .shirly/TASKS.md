# Task Ledger

**Owner:** Orion (Owl Astro) · **Manager:** Shirly · **Timezone:** US Eastern
**Last full sweep:** 2026-09-09 (Routine deleted this day — check-ins are OFF)

**Live board:** https://claude.ai/code/artifact/172a2eba-3351-4322-bb49-e87711e41522
The desk computes every age from the `since` date on each item, so it is never stale.
The day counts written here are correct only as of the sweep date above — when they
disagree with the desk, the desk is right.

This is the single source of truth for what Orion has committed to. Shirly reads it
at every check-in, verifies each line against **evidence** — not memory, not
self-report — and updates `Last evidence` in place.

**The rule that makes this work:** a task is only "done" when its Evidence check
passes. Shirly never asks "did you do X?" She runs the check and reports.

---

## Status vocabulary

| Status | Meaning |
|--------|---------|
| `ACTIVE` | Being worked this week. Expected to show movement. |
| `BLOCKED` | Cannot proceed. Must name the blocker AND the workaround. |
| `STALLED` | Was active, no evidence of movement past its cadence. Needs a decision. |
| `SILENT-FAIL` | Automation that should be producing output and isn't. Nobody noticed. |
| `PARKED` | Deliberately paused with a stated reason and a revisit date. |
| `DONE` | Evidence check passes. |

`STALLED` is not a synonym for `BLOCKED`. Blocked means something external stops
you. Stalled means nothing stops you and it still isn't moving — which is
usually an unmade decision wearing a task's clothes.

---

## Standing commitments (recurring)

| # | Commitment | Cadence | Evidence check | Last evidence | Status |
|---|-----------|---------|----------------|---------------|--------|
| S1 | Comedy Factory publishes a daily video | Daily 06:00 UTC | Latest `comedy-factory-daily.yml` run concluded `success` | **Never succeeded** — 0/22 runs; last attempt 2026-04-17 | `SILENT-FAIL` |
| S2 | Repo receives work | Weekly | `git log -1 master` within 7 days | 2026-04-05 (~157 days) | `STALLED` |
| S3 | VPS security posture verified | Monthly | UFW + fail2ban + cert expiry checks pass | **Never** — no baseline date exists | `STALLED` |
| S4 | Shirly's check-ins produce durable output | 6×/day | New `.shirly/LOG/YYYY-MM-DD.md` on origin after each 21:00 close-out | **Never** — ~45 runs, zero commits. Routine deleted 2026-09-09 | `BLOCKED` |

S3 carries no day count on purpose. There is no evidence to measure from, and an
unmeasured control is not a passing one — it is simply unmeasured.

---

## Active tasks

### T1 — Deploy universal369.com
- **Status:** `STALLED` (was `BLOCKED` — see commentary)
- **Age:** Files ready since 2026-03-19. **~174 days.**
- **Blocker of record:** SSH from Windows drops at banner exchange (Hostinger network block).
- **Documented workaround:** hPanel File Manager upload — in `HANDOFF.md` since day one.
- **Evidence check:** `curl -s -o /dev/null -w "%{http_code}" https://universal369.com` → `200`
- **Last evidence:** `index.html` untouched since 2026-03-18. Liveness unverified — no egress from the check-in sandbox.
- **Next action:** Upload both files via hPanel File Manager (browser, no SSH). ~10 minutes.

> **Shirly's read:** A blocker with a documented workaround that has sat unused for
> five months is not a blocker — it's an avoidance. The SSH problem is real, but it
> stopped being the reason on roughly day three. Two files, one browser upload.
> Reclassified to `STALLED` so it stops getting the sympathy that `BLOCKED` earns.

### T2 — thesoulhunter.com first PLAN
- **Status:** `STALLED`
- **Age:** `.paul/STATE.md` last activity 2026-03-18. **~175 days.**
- **Position:** Ready for first PLAN. Roadmap drafted, never approved. Milestone 0%.
- **Evidence check:** `.paul/STATE.md` "Last activity" within 14 days, or Phase 1 named in `ROADMAP.md`
- **Last evidence:** 2026-03-18. Phase 1 still literally "TBD".
- **Next action:** One decision — approve the roadmap as drafted, or name the one phase adjustment blocking it. Then `/paul:plan`.

> **Shirly's read:** Five months parked one decision short of starting. The roadmap
> doesn't need to be right, it needs to exist — Phase 1 is still "TBD" and that's
> the whole obstruction. Approve it imperfect; `/paul:plan` will reshape it anyway.

### T3 — Comedy Factory: diagnose total automation failure
- **Status:** `SILENT-FAIL` · **Priority: highest on the board**
- **Age:** Quiet since 2026-04-17. **~145 days.**
- **Evidence:** 22 scheduled runs, **21 failed + 1 cancelled, 0 succeeded.** First run 2026-03-27, last 2026-04-17. The schedule has not fired since.
- **Failure shape:** Runs died in 45–70s, before any media work. That points at setup — `apt-get install ffmpeg` without a preceding `apt-get update`, the `pip install`, or `--test-config` rejecting missing keys. The workflow env omits `GEMINI_API_KEY`, `PEXELS_API_KEY`, `DID_API_KEY`, `YOUTUBE_CLIENT_SECRETS`.
- **Why it also stopped firing:** GitHub disables scheduled workflows in repos with no commit activity. Last commit to `master` was 2026-04-05.
- **Logs:** Expired (`410 Gone`). Root cause needs a fresh run.
- **Evidence check:** Latest run concluded `success` AND a new dir exists under `comedy-factory/runs/`
- **Next action:** Trigger `workflow_dispatch` with `dry_run=true`, read the fresh log, fix the setup step. Dry run isolates infrastructure from API keys.

> **Shirly's read:** This is the failure mode a person cannot catch unaided, and the
> clearest case for these check-ins. CLAUDE.md documents it as a working daily
> pipeline. It has never once worked. It failed 22 consecutive times, then went
> quiet — and the quiet reads exactly like success from the outside. Nothing
> screamed, so nothing got looked at. Fix this first: it's the only item here that
> was actively lying about its own state.

### S4 — Shirly's check-ins are off, pending a Routine with a repo
- **Status:** `BLOCKED` — genuinely, as of today. Not an avoidance yet.
- **Age:** Blocked since 2026-09-09. **0 days.** (The underlying defect ran 2026-09-01 → 2026-09-09.)
- **What happened:** The original Routine (`trig_01VMUuZT7692VFYvHcPzt4xm`) fired ~45 times over 8 days. Every run reported `ROUTINE_RUN_STATUS_SUCCEEDED`. Zero commits and zero `.shirly/LOG/` entries ever reached origin — including seven 21:00 close-outs. Deleted 2026-09-09 rather than left running, since it was consuming six sessions a day to produce nothing.
- **Root cause:** The trigger carried no git source. Its `session_request` had no `config.sources` block, unlike the five WeekendMarket Routines on the same account, which each name a `git_repository` and work correctly. Neither `create_trigger` nor `update_trigger` accepts a sources parameter, so this could neither be set at creation nor added afterward.
- **Why not fixed in place:** The one programmatic route that attaches a repo is binding the Routine to a persistent session, and the server rejects `notifications` on that Routine type — it would have traded away the push notifications that were working. The claude.ai Routines UI is the only place a repo and notifications coexist.
- **Blocker:** Requires the claude.ai Routines UI. **Workaround: none — this genuinely cannot be done from here.**
- **Evidence check:** a new `.shirly/LOG/YYYY-MM-DD.md` on origin after a 21:00 close-out
- **Next action (Orion):** Create the Routine per **`.shirly/ROUTINE.md`** — settings, both cron expressions, and the paste-ready prompt are all there.

> **Shirly's read:** I am off the air until this is rebuilt, and that is the right
> trade — a Routine that reports success while producing nothing is worse than no
> Routine, because it manufactures false confidence. `BLOCKED` is honest today: the
> tooling genuinely cannot attach a repo, and the workaround column is empty for a
> reason. But my own rule says watch for a blocker that outlives its excuse. If this
> is still `BLOCKED` in seven days, it has become a stall, and it should be
> reclassified without ceremony — the same judgment I applied to T1.

---

## Backlog (not yet committed — no due dates, no drift)

- Approve or revise `.paul/ROADMAP.md` phase structure
- Re-verify VPS security checklist after universal369 deploy
- Decide whether Comedy Factory publishing stays daily or drops to weekly
- Point the desk at compassclub.pro once its source location is known

---

## Parked

*None.*

> If T1/T2/T3 are not going to be worked, the honest move is `PARKED` with a
> revisit date — not `ACTIVE` indefinitely. A ledger that quietly carries dead
> weight stops being worth reading, and that costs more than any single task.

---

## Drift summary — as of 2026-09-09

| Item | Days since evidence | Kind |
|------|--------------------:|------|
| T2 thesoulhunter | ~175 | Stall |
| T1 universal369 | ~174 | Stall (mislabeled blocked) |
| S2 repo activity | ~157 | Stall |
| T3 comedy-factory | ~145 | Silent failure |
| S4 Shirly's check-ins | 0 | Blocked (check-ins OFF) |
| S3 VPS security | never measured | Stall |

**Three projects, one shape.** T1, T2 and T3 all stopped inside a three-week window
in spring 2026 and nothing has moved since. That is not three independent lapses —
it's one interruption that nothing was in place to recover from. The check-ins exist
to make the next interruption visible in hours instead of months.

**And one of them was ours.** S4 was the same failure as T3 — a green light over an
empty room — caught at eight days instead of five months because something was
finally watching. The broken Routine is now deleted rather than left to accumulate
false confidence. That is the system working. It only finishes working when the
replacement lands and writes its first close-out log.

---
*Shirly updates this file at the 06:00 and 21:00 sweeps. See `.shirly/CHECKIN.md`.*
