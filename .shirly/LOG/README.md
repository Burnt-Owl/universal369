# Check-In Log

One file per day, written by Shirly at the **21:00 ET close-out**: `YYYY-MM-DD.md`.

The log exists so drift is measurable across weeks rather than re-litigated from
memory every morning. A single day's "no movement" is noise; fourteen of them in a
row is the finding — and only the log can show that.

## Format

```markdown
# 2026-09-01 · Tue

**Score:** shipped | partial | no movement

## Moved
- <evidence — a commit, a passing check, a 200 response. Not "worked on X".>

## Didn't move
- T1 universal369 — 166d — no action taken

## Flags raised
- 06:00 T3 challenged (137d silent failure)
- 15:00 T1 escalated to force-decision

## Tomorrow's top item
- <one thing>
```

## Reading the log

At each **06:00** standup Shirly scans the last 7 entries before setting the day:

- **3+ consecutive `no movement`** on one task → escalate a rung, regardless of age.
- **A flag raised 5+ days running with no action** → stop flagging. Put the
  underlying decision to Orion directly: does this still matter?
- **A task that only ever appears under "Didn't move"** → it was never really
  active. Propose `PARKED` with a revisit date.

That last pattern is worth catching early. A task nobody has touched in a month is
rarely blocked on work — it's blocked on a decision that hasn't been made, and it
will sit there indefinitely until someone names it.
