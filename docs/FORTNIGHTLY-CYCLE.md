# The fortnightly cycle

The project is designed around 1–2 week independent bursts of work, so that it
survives a dissertation, a job, and a fortnight when nothing gets done.

---

## Days 1–10 — the machine works, you do not

The monitor runs on the 1st and 15th. A source health check runs every Monday
and writes nothing; its only job is to fail loudly when a feed dies.

**Your total involvement in these ten days is zero.** That is the point. If you
find yourself checking feeds manually during this window, the system is not
doing its job and the fix belongs in `sources.json`, not in your evenings.

The one thing worth watching: if the Monday health check reports a new **STALE**
or **FAILED** source, fix the URL then. Fixing it on day 11 costs you the cycle.

---

## Day 11 — review (60–90 minutes)

```bash
python3 review.py --status
python3 review.py --list
```

1. **Read the source health table first.** A thin flag list and a broken source
   list look identical. Rule the second out before you believe the first.
2. **Read the top tier properly.** Ten items maximum, by design.
3. **Scan the significant tier.** Promote anything the gate missed.
4. **Skim the detected tier.** You are looking for the thing the rules got
   wrong, not for content.
5. **Select 5–8.** Then cut one more. Aim for spread across beats — five stories
   about the same file is a briefing, not an edition.
6. **Log anything the system missed** in `TUNING-LOG.md` while it is fresh.

```bash
python3 review.py --new-edition 7 --select 1,3,4,9,12
```

---

## Days 11–12 — research (3–5 hours)

Roughly 90 minutes for the lead item, 30–40 minutes each for the rest.

Per item: read the primary source in full · find one independent account ·
establish the stage (proposal / agreement / adopted / in force) · find one
number worth putting on a slide · answer all seven questions in `brief.md`.

Stop researching when you can answer *why should a young person care* in one
sentence without hedging. If you cannot after 40 minutes, cut the item — that is
information, not failure.

---

## Days 12–13 — produce (4–6 hours)

**Substack (2–3 hours).** Write the items first, the opener last. Cut to
1,200–1,800 words. Every claim linked. One chart or map. One lighter item.

**Instagram (2–3 hours).** One carousel from the lead item for publication day.
Two or three more scheduled across the following fortnight — an edition should
feed the feed for two weeks, not one afternoon.

Design once, reuse forever: the brand templates in `brand/templates/` exist so
that slide layout is never a decision you make twice.

---

## Day 14 — publish and distribute (1 hour)

- Substack out.
- Lead carousel posted. Story with a link sticker.
- Sent to the university society contacts.
- LinkedIn repost with the lede and a link.
- Remaining carousels scheduled.

---

## After

Note what performed. Put anything the system got wrong into `TUNING-LOG.md`.
Then leave it alone for ten days.

---

## Realistic budget

| Stage | Hours |
|---|---|
| Days 1–10 | 0 |
| Review | 1–1.5 |
| Research | 3–5 |
| Production | 4–6 |
| Distribution | 1 |
| **Per edition** | **9–13.5** |

Roughly five to seven hours a week, concentrated into a four-day burst. That is
the whole argument for fortnightly: it fits into a fortnight that also contains
a dissertation.

---

## When a cycle fails

It will. The honest options, in order of preference:

1. **Publish short.** Three items and a chart is a real edition. Nobody counts.
2. **Publish late.** Two days late is invisible. Skipping is not.
3. **Skip and say so.** One line to subscribers: no edition this fortnight,
   back on the Nth. Silence is what loses subscribers, not absence.

Never publish something you have not read the source for to keep a schedule.
That is the one failure mode that costs you the thing the project is for.
