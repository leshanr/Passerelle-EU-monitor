# Source audit — 27 August 2026

Every endpoint in `sources.json` fetched and read by hand. Recorded here because
the result is the most useful thing the project has learned so far, and because
a source list nobody has checked is a liability presented as an asset.

---

## Headline finding

**Four of the ten EU feeds parse cleanly, report items, and have published
nothing in weeks.**

| Source | Tier | Parses | Newest item | Age | Verdict |
|---|---|---|---|---|---|
| European Commission — press corner | 1 | yes | 28 Jul 2026 | 30d | **stale** |
| European Parliament — press releases | 1 | yes | 12 Jun 2026 | 76d | **stale** |
| European Parliament — committees | 1 | yes | 16 Jun 2026 | 72d | **stale** |
| European Parliament — texts adopted | 1 | yes | 18 Jun 2026 | 70d | **stale** |
| Council of the EU — press releases | 1 | yes | 15 Jun 2026 | 73d | **stale** |
| Council register — summary of acts | 2 | yes | 22 Jul 2026 | 36d | stale |
| EUR-Lex — Commission proposals | 1 | yes | 17 Aug 2026 (channel) | 10d | **current** |
| EUR-Lex — CJEU case-law | 1 | yes | 12 Jun 2026 | 76d | stale |
| EUR-Lex — Official Journal L | 1 | yes | 20 Jul 2026 | 38d | stale |
| European Central Bank — press | 1 | yes | 26 Aug 2026 | 1d | **current** |
| gov.uk — news and communications | 1 | yes | 27 Aug 2026 | 0d | **current** |
| gov.uk — FCDO | 2 | yes | 26 Aug 2026 | 1d | **current** |
| gov.uk — DBT | 2 | yes | 21 Aug 2026 | 6d | **current** |
| UK Parliament — all bills | 2 | yes | 26 Aug 2026 | 1d | **current** |
| European Parliament — top stories | — | yes | 08 Nov 2023 | 1023d | **dead, rejected** |

---

## What that means

Part of it is the August recess — Brussels genuinely closes. But a 76-day gap on
the Parliament press feed spans a plenary session, and the "top stories" feed has
not moved since 2023 while the page it corresponds to is updated constantly.
These feeds are not maintained with the same care as the web pages behind them.

Three consequences, all now built into the system:

**1. Staleness detection is not optional.** A feed reporting `ok` tells you the
XML parsed. It tells you nothing about whether the institution is still
publishing to it. Every health table now carries a newest-item age column and
flags anything over `stale_after_days` (21) as STALE, and the digest opens with a
warning when sources are stale.

**2. Redundancy per institution.** One Parliament feed is a single point of
failure that fails silently. Three — general press, committees, texts adopted,
from two different publishing systems — means a dead one is visible because the
others are not.

**3. Do not promise a beat one feed supports.** If the only source for a beat is
stale, the beat is not covered, whatever the keyword list says.

---

## Rejected

**European Parliament — top stories** (`/rss/doc/top-stories/en.xml`). Newest
item November 2023. Evergreen editorial picks, not news. Rejected.

**Eurostat news releases.** The documented Atom endpoint is disallowed by the
site's robots.txt. Statistics remain a gap — worth solving, because "one number"
is a fixed slot in every edition. Next thing to try: the Eurostat API rather
than the feed.

**European Environment Agency newsroom.** Disallowed by robots.txt.

**EEAS.** The documented feed URL returns 404. The External Action Service is a
real gap for the geopolitics beat; the Council and Commission feeds partly cover
it.

---

## Held back, not enabled

Three credible non-institutional sources sit in `sources.json` with
`"enabled": false` — Euractiv, EUobserver, and the Parliament's research service.

They are off on purpose. Turning them on changes what the system *is*: it would
start monitoring other people's editorial judgement alongside the institutions'
raw output, and the flag count would rise sharply. That may be the right call
later. Enable one at a time and watch what it does to the flag counts before
adding another.

---

## Re-audit schedule

- **Weekly, automatic.** The Monday health-check run. Writes nothing, fails
  loudly.
- **Every six months, by hand.** Fetch every endpoint, update `newest_seen`,
  re-read the notes, and record the result in this file. A note that is two
  years old is worse than no note.

Next hand audit: **February 2027.**
