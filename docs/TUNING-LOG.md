# Tuning log

Every adjustment to `rules.json` and `sources.json`, with the reason.

This is not housekeeping. The tuning process is publishable material and it is
the most convincing evidence that a human is exercising judgement over the
machine rather than accepting its output. Employers and collaborators reading
the repo will get more from this file than from `collect.py`.

**Format:** date · what changed · what triggered it · what it fixed.

---

## 2026-08-27 — build

**Source audit.** All fifteen endpoints fetched and read by hand.

Finding: the EU institutional feeds are far less current than they look. The
Commission press corner had published nothing for 30 days, the European
Parliament press feed for 76, the Council press feed for 73. All three parse
cleanly and report `ok`. Only the ECB (1 day) and the EUR-Lex document feeds
(10 days) were current.

Fixes:
- Added `ep-committees` and `ep-texts-adopted` alongside the general EP press
  feed, so one dying is visible rather than silent.
- Added `eurlex-caselaw` — court rulings are the most under-covered
  high-consequence events in European politics and nothing else in the set
  carried them.
- Added `ecb-press`, the only reliably current EU feed found.
- Kept the stale feeds. They are the right sources; they are seasonally quiet
  and occasionally neglected. The staleness detector is the answer, not deletion.

**Undated items.** EUR-Lex predefined feeds date the channel but not the items.
The window check treated undated as out-of-window and silently discarded the
entire feed. Added a per-source `date_fallback: "channel"` option rather than
special-casing EUR-Lex in the code.

**CELEX titles.** EUR-Lex titles arrive as `CELEX:52026PC0435: Proposal for a
...`. The identifier is noise to a keyword scorer and was diluting every match.
Now stripped before scoring.

**Substring matching was wrong.** The original scorer used plain `in` tests.
`uk` matched inside *Ukraine*. `ai` matched inside *said*, *chain* and
*campaign*. `cap` matched inside *capital*. Every one inflated scores on items
with nothing to do with the signal — and `ai`/`uk` are two of the most-used
keywords in the file, so this was not marginal.

Fixed with bounded matching plus an explicit `*` stem syntax, and nine
regression tests so it cannot come back. Converted 32 keyword groups to stems
(`sanction*`, `criticis*`, `protest*`) which catch more than the inflections
they replaced.

**`erasmus` removed from the `uk` signal.** "Erasmus+ budget cut by 12 percent"
was being flagged as UK–EU relevant on the strength of the word *Erasmus* alone.
Erasmus is a mobility story; the UK angle needs its own evidence.

**Score calibration.** First run put every fixture item in the top tier —
thresholds were an order of magnitude below the actual score scale, and the
scale itself was unbounded, so an item using six words from one signal's list
outscored an item tripping four different signals. Backwards.

Capped each signal's contribution and capped the beat component. Breadth of
reasons now beats repetition of one reason. Recalibrated to
`significant ≥ 25 / 2 signals` and `investigate ≥ 55 / 3 signals`, which on the
fixture set gives 12 detected / 9 significant / 7 investigate.

**These thresholds are a guess against fixtures, not against reality.** Expect
to move them after the first two real runs. Log it here when you do.

---

## Template for future entries

```
## YYYY-MM-DD — edition #NNN review

**What the system missed.** <item> should have been flagged and was not.
Cause: <no keyword / wrong beat / below threshold / source not monitored>.
Fix: <what changed in rules.json>.

**What the system over-flagged.** <item> reached investigate and was not worth
it. Cause: <keyword too generous / signal firing on boilerplate>.
Fix: <what changed>.

**Source health.** <which feeds were stale, what was done>.

**Threshold effect.** Flag counts before: N/N/N. After: N/N/N.
```
