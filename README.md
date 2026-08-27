# EU MONITOR

**European politics. Actually worth knowing.**

A fortnightly, youth-focused European politics and policy publication, built on
an automated monitoring system that watches EU institutional sources
continuously so that nobody has to read them every day.

```
The code does the boring monitoring.   I do the interesting part.
The system finds the signal.           I decide what matters.
Substack provides the depth.           Instagram provides the accessibility.
```

Standard library Python only. No dependencies, no API keys, no paid tiers,
nothing to expire.

**Status:** pipeline built and tested (54 offline checks passing), source list
audited 27 August 2026, first scheduled run not yet fired. Described as *in
progress* until it has.

---

## What it does

Fifteen institutional feeds — the Commission, Parliament, Council, EUR-Lex, the
Court of Justice, the ECB, and the UK side of the relationship — are pulled
every fortnight, stripped of what has already been seen, and scored on two
independent axes. Then it stops, and a human takes over.

```
EU SOURCES → AUTOMATED MONITOR → FLAGGED DEVELOPMENTS → HUMAN REVIEW
   → RESEARCH → EDITORIAL SELECTION → SUBSTACK → INSTAGRAM → DISTRIBUTION
```

What you come back to after two weeks:

```
EU MONITOR — 14 DAYS

WINDOW        13 Aug 2026 → 27 Aug 2026
SOURCES       14/15 returned a feed   (4 stale)

  37  developments detected
  12  potentially significant
   7  worth investigating
   ?  selected for publication   ← your call
```

---

## Setup (about ten minutes)

1. Create a new **public** repository on GitHub. Public matters — it is the
   thing you link to in applications.
2. Upload these files, keeping the folder structure.
3. **Settings → Actions → General → Workflow permissions → Read and write
   permissions.** Without this the workflow cannot commit the digest.
4. **Actions → EU Monitor → Run workflow.** This is the first real test of the
   feeds.
5. Read the run summary, and read the **source health** table at the bottom of
   it *before* you read anything else.

After that it runs itself: a full collection on the 1st and 15th of each month,
and a source health check every Monday that writes nothing and exists purely to
tell you when a feed has died.

### Running it locally

```bash
python3 collect.py --check          # feed health and staleness, writes nothing
python3 collect.py --dry-run        # print the digest without saving
python3 collect.py --days 7         # narrow the window
python3 tests/test_offline.py       # 54 checks against fixtures, no network
python3 tests/demo.py               # run the whole pipeline on fixture data
```

---

## How it works

```
sources.json → fetch → parse (RSS + Atom) → window + dedupe → score → classify
                                                  ↑              ↑        ↑
                                          state/seen.json   rules.json  flag tiers
                                                                          ↓
                          digests/YYYY-MM-DD.md  (for you)  +  .json  (for review.py)
```

### Two axes, not one

Most keyword monitors ask one question: *is this about my topic?* That surfaces
everything the Commission publishes about digital policy, which is roughly forty
items a fortnight and useless. This asks two questions independently:

| Axis | Question | What it decides |
|---|---|---|
| **Beat** | What is this *about*? | Which section of the digest it lands in |
| **Signals** | Why might it *matter*? | Whether it is flagged at all, and the reason printed next to it |

There are eight beats and eleven signals. An item's score is its (capped) beat
weight plus the sum of the signals it trips. **Breadth beats repetition:** each
signal's contribution is capped, so an item that trips four different signals
outranks one that uses six words from a single signal's keyword list. That is
deliberate — four independent reasons to care is a better story than one reason
stated loudly.

**The eight beats**

| Beat | What sits here |
|---|---|
| Power and democracy | Elections, rule-of-law fights, enlargement, institutional power |
| War and security | Ukraine, Russia, defence, sanctions, NATO, hybrid threats |
| Tech and online life | AI Act, DSA/DMA, platforms, age verification, privacy, chips |
| Climate and energy | Targets, carbon pricing, energy bills, and who pays |
| Borders and moving around | Schengen, ETIAS, visas, Erasmus, migration, travel rights |
| Money and work | Wages, housing, the budget, the single market, trade |
| Rights and courts | CJEU and ECHR rulings, consumer rights, press freedom |
| The UK and Europe | The reset, divergence, youth mobility, Windsor |

**The eleven signals** — genuinely new · decision taken · unusual or unexpected ·
likely to generate debate · consequential · **relevant to young Europeans** ·
UK–EU relevance · geopolitically important · economically significant ·
technologically significant · socially relevant.

*Relevant to young Europeans* carries the heaviest weight in the file. It is the
reason this exists rather than being one more Brussels newsletter.

### Three flag tiers

| Tier | Gate | What you do with it |
|---|---|---|
| **Worth investigating** | score ≥ 55, ≥ 3 signals, **and** at least one of *youth / unusual / decided / consequential / uk* | Read properly. This is the shortlist. |
| **Potentially significant** | score ≥ 25, ≥ 2 signals | Scan. Promote anything the top tier missed. |
| **Also detected** | everything else that cleared the noise filter | Skim headlines only. |

The `requires_any` gate on the top tier is the most opinionated line in the
config. A development can be geopolitically enormous and still be the fourth
Ukraine statement that fortnight. Requiring one signal that makes it worth a
young reader's ten minutes is what stops the shortlist filling with important
things nobody needs to read.

### Keyword matching is bounded, and stems are explicit

Substring matching was the original approach and it was quietly wrong: `uk`
matched inside *Ukraine*, `ai` inside *said*, *chain* and *campaign*, `cap`
inside *capital*. Every one of those inflated scores on items that had nothing to
do with the signal. Matching is now bounded on both sides.

A keyword ending in `*` is a prefix stem — `criticis*` catches *criticise*,
*criticised* and *criticism*. **Shorter stems catch more.** Prefer `sanction*`
over listing four inflections, and guard against false positives with the noise
list rather than with longer phrases.

### A feed that parses is not a feed that works

The single most useful thing this pipeline does is tell you when a source has
quietly stopped publishing.

At the 27 August 2026 audit, the Commission press corner had published nothing
for 30 days, the European Parliament press feed for 76, the Council press feed
for 73. All three parse cleanly, return items, and report `ok`. Only the ECB and
the EUR-Lex document feeds were current.

So every health table carries a **newest-item age** column, anything older than
`stale_after_days` is flagged **STALE**, and the digest opens with a warning when
sources are stale. **Read that column before you conclude it was a quiet
fortnight in Brussels.** The other half of the answer is redundancy: several
feeds per institution, drawn from different systems, so that one dying is visible
rather than silent.

### Files

| File | What it is |
|---|---|
| `collect.py` | The engine. Fetch, parse, window, dedupe, score, classify, render. |
| `review.py` | The human layer. Reads flags, scaffolds an edition around your choices. |
| `sources.json` | The feeds, with a tier, a verification date and an honest note each. |
| `rules.json` | The editorial intelligence — beats, signals, thresholds, noise. |
| `digests/` | One markdown digest per run, plus a JSON sidecar for the tooling. |
| `state/seen.json` | Every item ever surfaced, by hash. Stops the digest repeating itself. |
| `state/history.json` | A run log — detected/significant/investigate counts over time. |
| `editions/NNN/` | **Never written by the automated run.** Your selections and drafts. |

---

## The human layer

This is the part that matters, and the file layout enforces it. Nothing in
`editions/` is ever written by a scheduled run.

```bash
python3 review.py --list                          # the numbered flag list
python3 review.py --list --signals youth,unusual  # only flags carrying these
python3 review.py --new-edition 7 --select 1,3,4,9,12
python3 review.py --status                        # where you are in the cycle
```

`--new-edition` writes `editions/007/` containing:

- **`brief.md`** — the Substack draft, with every selected development already
  carrying its source link, the reasons it was flagged, and the seven editorial
  questions as empty headings.
- **`carousel-NN-….md`** — one seven-slide Instagram script per development,
  structured hook → what happened → what changed → why → who → why you should
  care → what next.
- **`checklist.md`** — the 14-day production checklist, pre-filled with your
  selections.
- **`selection.json`** — what you chose out of what, so the ratio is recoverable.

The seven questions are the whole editorial method:

> What actually happened? · What changed? · Why did it happen? · Who does it
> affect? · **Why should a young person care?** · What is the wider political
> significance? · What happens next?

If the honest answer to the fifth is *they shouldn't*, cut the item. That
question is the entire publication.

---

## The fortnightly cycle

| Days | What happens | Who |
|---|---|---|
| 1–10 | The monitor runs. You do not think about it. | Machine |
| 11 | Read the flags. Check the source health table. Select. | Human |
| 11–12 | Research the selected developments against primary sources. | Human |
| 12–13 | Write the Substack. Produce the Instagram carousels. | Human |
| 14 | Publish. Distribute through university society networks. | Human |

Designed to be genuinely maintainable by one person alongside university and
work. Fortnightly beats weekly if weekly means missing one.

---

## Tuning

Tune `rules.json`, never `collect.py`. That separation is the entire point of
keeping them apart.

- Too much surfacing → raise `score_threshold` values, cut low-value keywords,
  add to the noise list.
- Too little → add keywords, lower thresholds, widen `window_days`.
- The right item in the wrong beat → the beat keyword weights, not the code.

Expect two or three cycles before the signal is right, and **write every
adjustment into `docs/TUNING-LOG.md`.** That log is not housekeeping — the tuning
process is itself publishable material, and it is the most convincing evidence
that a human is exercising judgement over the machine rather than accepting its
output.

---

## Scope

This monitors institutional publications: legislation, press releases, court
rulings, consultations and bills. It is a policy monitoring tool, not a
people-tracking one, and the source list should stay that way.

---

## The publication

- **Substack** — fortnightly briefing, 5–8 developments, one deeper analysis,
  one statistic, one lighter item. About ten minutes.
- **Instagram** — not an advert for the Substack. A second editorial format
  built from the same research: seven-slide explainers, maps, timelines, charts.
- **University societies** — EU, Politics, IR and European societies, and student
  newspapers. Joint explainers, guest contributions, takeovers, cross-promotion.

See `docs/` for the editorial standards, the audience and distribution plan, the
worked example, and the tuning log. See `brand/` for the visual system.
