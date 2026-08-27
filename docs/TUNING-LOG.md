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

## 2026-08-27 — run #001, the first live run

The first run against the real feeds. 71 detected, 31 significant, 10 worth
investigating — and the top tier was useless. **All ten were EUR-Lex.** Seven
were General Court judgments about trade marks. The single item genuinely on
brief — *"Cost of living and young people priorities for the PM"* — scored 49
and sat at number thirteen.

Diagnosis, in one line: **the digest was ranked by title length.**

### What the system missed

*"Cost of living and young people priorities for the PM during first visit to
Northern Ireland"* (92 characters) should have led. It scored 49 against 82 for
a CELEX notice about GATT tariff-rate quotas.

Cause: a title match was worth a flat double a body match. EUR-Lex titles run
400–800 characters and list every party, instrument and recital; a gov.uk
headline runs 30–100. The long ones accumulated matches by length, not
relevance. Worse, they tripped *six* signals apiece without meaning any of
them — "entry into force" read as **decided**, "for the first time" as
**unusual**, a tariff figure as **economic**, and the words *United Kingdom* and
*China* as **uk** and **geopolitical**. Six incidental signals beat two
deliberate ones.

Four beats — tech-and-online-life, climate-and-energy, borders-and-moving,
power-and-democracy — returned **nothing at all**, while the Commission press
corner had returned 60 items dated that day. Those items were not missed. They
were outranked.

### Fixes

**1. Title boost damped by length** (`title_boost_ref_chars: 110`). A title at
or under the reference length keeps the full ×2; longer titles decay towards
×1, so they still count for more than body text but stop winning on word count.

**2. `match_cap: {beat: 4, signal: 3}`.** Only the strongest distinct matches in
each keyword set count. Four strong matches and twelve are not different kinds
of evidence.

**3. `signal_count_cap: 4`.** Breadth of reasons should beat repetition of one
reason — but breadth has a ceiling. Only the four strongest signals contribute
to the score. *Every* signal that fired is still reported on the review screen:
capping the score is right, hiding the reasons would make the digest lie about
why something surfaced.

**4. `score_multiplier: 0.6` on the two EUR-Lex feeds.** EUR-Lex is authoritative
about what a rule says and silent about why anyone should care. It is how you
*verify* a story, not how you *find* one. Weighted down rather than dropped —
its links are still what every claim in a published brief points at.

**5. `investigate_requires_any` on `rights-and-courts`** = youth / uk /
contested / unusual / social. The case-law feed returns a hundred judgments a
fortnight. Being a ruling is not by itself a reason to read something; a court
item now needs a second reason that is not simply that a court decided it.
Landmark rulings clear this easily — the docket does not.

**6. `caps.investigate_per_beat: 3`.** No single beat can take more than three
of the ten top slots. Anything demoted lands in the tier below, where it is
still read.

**7. Noise list +8 terms** for the trade-mark docket: `euipo`, `trade mark`,
`trademark`, `figurative mark`, `word mark`, `opposition division`, `board of
appeal`, `order of the president`. These killed five items outright on the
re-score. An EUIPO dispute is never this publication's story.

**8. Thresholds 55/3 → 36/2 (investigate), 25/2 → 22/2 (significant).** Capping
breadth and damping length compressed the whole score scale. Requiring three
signals was excluding exactly the items this publication exists for: a real
headline trips two signals on purpose where a legal notice tripped six by
accident.

### Effect, measured on the real run-001 items

Re-scoring the 31 flagged items from run #1 against the new rules:

| | before | after |
|---|---|---|
| "Cost of living and young people…" | #13, significant | **#1, investigate** |
| CELEX GATT notice | #1, investigate | #4, significant |
| EUIPO trade-mark cases | 5 in the flag list | killed by noise |
| Top-tier beats | 2 (courts, money) | spread, capped at 3 each |

**This calibration set is biased** — it contains only what the *old* scorer
flagged, which is to say the long items. The next live run is the real test,
because it will surface items the old rules buried.

### Source health

- **Three European Parliament feeds failed** from GitHub's runners with
  `no element found: line 1, column 0` — an empty body reaching the XML parser.
  Likely a UA or geo block on Azure IP ranges. Not reproducible from a
  developer machine, which is why `parse_feed` now reports *what* came back
  (empty / HTML / non-XML with a snippet) rather than letting the parser's
  error stand in for a diagnosis.
- **EUR-Lex Commission proposals** timed out. Sources can now set their own
  `timeout`.
- **European Council meetings** reported a *negative* age (−112d) because it
  carries scheduled future dates. Added `future_tolerance_days: 2`: items dated
  further ahead are diary entries, not developments, and are excluded from both
  the digest and the staleness calculation.

### Regression tests added

Fifteen, taking the suite from 54 to 72. The important ones use the **real
strings from run #1** rather than invented fixtures: the actual 444-character
CELEX notice must not outrank the actual 92-character headline, and the
headline must reach the top tier.

---

## 2026-08-27 — runs #002 to #004, sources

**Regression I caused.** The "does this start with `<`" guard added after run
#001 rejected a **UTF-8 byte-order mark**, which four Council feeds send. Three
working sources went to FAILED and the count dropped 11 → 8. Fixed with
`utf-8-sig` decoding plus a regression test. The improved diagnostic is what
caught it — the failure line printed the actual bytes, `\ufeff<?xml version=`,
which made the cause obvious immediately. Worth remembering: the better error
message paid for itself within one run.

**Fixed.** EUR-Lex Commission proposals was timing out on a 30-second default;
the feed carries 100 full document records. Given its own `timeout: 90`. Now ok.

**Added, both verified live and working from CI:** Politico Europe (10 items,
current) and EUobserver (20 items, current). Both tier 2 at
`score_multiplier: 0.8` — a short news feed refreshes constantly and would
otherwise crowd the institutional sources. Both are somebody else's editorial
judgement rather than a primary source, so they inform the digest rather than
lead it.

**Blocked, not fixable from here.** The three European Parliament feeds return
an empty 200 to CI while serving 20 current items to a browser. Euractiv returns
403 to CI while serving 100 current items to a browser. Changing the user agent
to a normal browser string fixed neither, which rules out the simple
explanation and points at IP-range filtering. `ep-press` kept enabled as a
canary; the rest disabled. See `SOURCE-AUDIT.md`.

**Also:** `daily news` and `midday express` added to the noise list — the
Commission's roundup bulletins are an index of the day's announcements, not a
development, and six of them were scoring 22–36. Enforcement verbs (`enforc*`,
`takes effect`, `applies from`, `comes into force`) added to the `decided`
signal after "Commission starts enforcing AI Act rules" scored 18 and sat in the
detected tier.

**CI:** `actions/checkout` v4 → v5 and `actions/setup-python` v5 → v6, clearing
the Node 20 deprecation warning.

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
