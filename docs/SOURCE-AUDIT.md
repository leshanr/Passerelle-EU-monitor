# Source audit

## The correction that matters

**An earlier version of this file was wrong, and the way it was wrong is worth
keeping on the record.**

Before launch, every endpoint was fetched by hand from a development sandbox.
That audit reported the Commission press corner 30 days stale, the European
Parliament press feed 76 days, the Council 73 days, EUR-Lex 38 days — and a
whole design argument was built on it about EU institutional feeds being poorly
maintained.

The first live run from GitHub's own runners, on 27 August 2026, showed the
opposite:

| Source | Live run | Pre-launch audit claimed |
|---|---|---|
| European Commission — press corner | **0d**, 60 items | 30d stale |
| Council of the EU — press releases | **0d**, 20 items | 73d stale |
| EUR-Lex — Official Journal L | **0d**, 100 items | 38d stale |
| EUR-Lex — CJEU case-law | **3d**, 100 items | 76d stale |
| European Central Bank — press | **0d**, 15 items | 1d |
| gov.uk ×3, UK Parliament bills | **0d** | 0–6d |

The staleness was an artefact of the sandbox's egress proxy and its cache, not a
property of the feeds. The feeds are current and well maintained.

**The lesson is about method, not about Brussels.** A source audit run from a
different network than the one the pipeline runs on is not an audit of the
pipeline's sources. The staleness *detector* is still worth having and stays —
it just was not detecting what it appeared to be detecting.

---

## Real failures, 27 August 2026

Four of fifteen sources failed from GitHub's network.

**European Parliament ×3 — press releases, committee press releases, texts
adopted.** All three returned `no element found: line 1, column 0`, which is
what an empty body looks like by the time it reaches the XML parser. All three
work from a browser and from a developer machine. The most likely explanation is
a user-agent or geographic block on Azure IP ranges, which is where GitHub's
hosted runners live.

This is the significant one: it removes the Parliament entirely, and the
Parliament is where the plain-English version of an EU story usually appears
first. Committee deals — *"Deal on air passenger rights: MEPs secure improved
traveller protection"* — are exactly this publication's material.

`parse_feed` now distinguishes an empty response, an HTML page, and non-XML
content with a snippet of what actually arrived, so the next run diagnoses this
rather than restating that the parser could not parse it. Fix the cause once the
next run says what the cause is.

**EUR-Lex Commission proposals** — read timeout. The feed carries 100 full
document records and is slow. Sources can now set their own `timeout`.

**Council document register (summary of acts)** — genuinely stale, 36 days.
Low value anyway; it is a backstop for when the press feeds go quiet.

---

## A parsing bug this run exposed

The European Council meetings feed reported a **negative** newest-item age
(−112 days). It carries *scheduled* meetings, dated into the future.

Two consequences, both now fixed: the staleness calculation was measuring from a
date that had not happened yet, and those future-dated diary entries passed the
window check and leaked into the digest as detected developments.
`future_tolerance_days` (default 2) now excludes them from both, and the health
table reports them separately as `scheduled`.

---

## What the browser check settled (27 August 2026)

Every failing source was loaded directly in a browser and compared against what
CI sees. That comparison is the whole diagnosis.

| Source | In a browser | From GitHub's runners |
|---|---|---|
| EP press releases | 20 items, newest 23 Jul | empty 200, 0 bytes |
| EP committees | works | empty 200, 0 bytes |
| EP texts adopted | works | empty 200, 0 bytes |
| Euractiv | 100 items, newest today | HTTP 403 Forbidden |
| EUR-Lex proposals | works | was timing out — **fixed**, 90s timeout |
| Politico Europe | 10 items, newest today | **works**, now enabled |
| EUobserver | (domain unreachable from the test browser) | **works**, now enabled |

**The Parliament block is on the IP range, not the request.** Swapping the user
agent for a normal browser string changed nothing, which rules out the simplest
explanation. Same for Euractiv's 403. Nothing in this repo can fix either; the
only real remedies are running the collector from somewhere other than GitHub's
hosted runners, or covering Parliament through outlets that report on it.

**What was done about it:**

- `ep-press` stays enabled as a **canary**. One FAIL line in the health table is
  the cheapest possible way to learn the day the block lifts. The other two EP
  feeds are disabled so the table is not cluttered by three lines saying the
  same thing — re-enable all three together.
- Euractiv disabled. Politico Europe and EUobserver cover the same ground and
  both work from CI.
- Politico Europe carries `score_multiplier: 0.8` and mixes English, French and
  German. The scorer is English-only, so non-English items score near zero and
  fall harmlessly into the detected tier.

**What this costs.** Parliament is where the plain-English version of an EU
story usually appears first — committee deals on passenger rights, social media
safety, the digital euro. Losing it is the single biggest gap in the source
list, and it is now covered second-hand rather than first-hand.

**Rejected as a workaround:** a Google News RSS bridge on
`site:europarl.europa.eu`. It returns 100 items whose newest is October 2025,
and the titles are multimedia pages and a PDF calendar. Google indexes the
Parliament's site poorly enough to be useless here.

---

## Rejected sources

- **European Parliament "top stories"** — newest item November 2023. Evergreen
  editorial picks, not news.
- **Eurostat news releases** and the **European Environment Agency newsroom** —
  both disallowed by robots.txt. Statistics remain a genuine gap, and "one
  number" is a fixed slot in every edition. Next thing to try is the Eurostat
  API rather than the feed.
- **EEAS** — the documented feed URL returns 404. A real gap for the geopolitics
  beat, partly covered by the Council and Commission feeds.

---

## Held back, not enabled

Two sources sit in `sources.json` with `"enabled": false` for reasons other than
being broken: **Euractiv** (blocked — HTTP 403 from CI) and the **Parliament's
research service**.

The research service is off on purpose. Turning it on changes what the system
*is*: it would start monitoring other people's editorial judgement alongside the
institutions' raw output, and the flag count would rise sharply.

**EUobserver and Politico Europe are now enabled**, at `score_multiplier: 0.8`.
That was a deliberate reversal of the position this section used to state, forced
by the Parliament block: with the Parliament gone there was no source left that
reports a committee stage in a sentence a human wrote. The multiplier is the
brake. Watch it — in run #005 all eight flags came from those two feeds. Partly
an artefact (the institutional items were already in `state/seen.json`, and the
institutions were in recess), but if a full run still returns nothing from the
Commission or the Council, lower the multiplier before the next collection. A
digest with no institutional item in it is a news roundup, and a news roundup is
not what this publication promises.

---

## Source weighting

Not every working source is a *discovery* source. The two EUR-Lex feeds carry
`score_multiplier: 0.6`.

EUR-Lex is authoritative about what a rule says and silent about why anyone
should care, and its house style — 400 to 800 character titles listing every
party and instrument — games any keyword scorer. It is how you verify a story,
not how you find one. Weighted down rather than dropped: its links are what
every claim in a published brief should point at.

See `TUNING-LOG.md`, entry for run #001.

---

## Re-audit schedule

- **Weekly, automatic** — the Monday health-check run. Writes nothing, fails
  loudly.
- **Every six months, by hand** — and *from the environment the pipeline
  actually runs in*, which is the whole point of the correction at the top of
  this file. In practice that means reading the health table from a real run
  rather than fetching the endpoints somewhere else.

Next hand audit: **February 2027.**
