# Passerelle — EU monitor

Automated monitoring of EU and UK institutional sources for **Passerelle**, a fortnightly
briefing on European politics for readers in the UK under thirty.

The code finds candidates. A person decides what is worth publishing. That division is the
whole design, and the code will not cross it.

## What it does

Every run reads 19 official, journalistic and polling feeds, scores what it finds against
a fixed rulebook, and writes a dated digest sorted into three tiers. It publishes nothing.

```
sources.json  ──▶  collect.py  ──▶  digests/YYYY-MM-DD.md   (the machine stops here)
rules.json    ──┘                        │
                                         ▼
                                    review.py  ──▶  editions/NNN/   (a person starts here)
```

## Running it

Collection runs itself on the 1st and 15th, plus a Monday source-health check. To run it by
hand: **Actions → Passerelle → Run workflow**. Set *Source health only* if you want to test
the feeds without writing a digest.

Locally, pure standard library, no dependencies:

```
python3 collect.py --days 14        # write a digest for the last 14 days
python3 collect.py --check-sources  # health table only, writes nothing
python3 review.py --list            # numbered flag list from the newest digest
python3 tests/test_offline.py       # 73 offline tests, no network
```

**Re-running collection on a date that already has a digest overwrites it,** and because
seen items are recorded in `state/seen.json` the second digest will be much thinner than
the first. Copy anything you care about before re-running.

## The files

| path | what it is |
|---|---|
| `sources.json` | the feeds, with tiers, weights and a health note on each |
| `rules.json` | beats, signals, noise filters and score thresholds |
| `collect.py` | fetch, parse, dedupe, score, classify, render |
| `review.py` | the human layer: pick flags, scaffold an edition |
| `digests/` | machine output, one file per run |
| `editions/` | human output, one folder per published edition |
| `state/` | what has already been seen; delete to force a full re-read |
| `tests/` | offline tests and fixtures |

## Source health

19 feeds enabled, all returning. Four more are in `sources.json` switched off and
documented: the three European Parliament feeds return an empty response to GitHub's
runners, and Euractiv returns 403 to them. Both are access blocks at the far end.

Three of the 19 are **gated**. YouGov, Ipsos and Pew publish overwhelmingly on subjects
that have nothing to do with Europe, so they carry `"require_match": ["@eu_politics"]` and
their items are dropped before scoring unless they mention European politics. The
vocabulary is the `topic_gates` block of `rules.json`, and every run reports how many the
gate dropped — the filtering is never invisible.

Every run prints a source-health table. **Read it before you read the flags** — a thin flag
list and a broken feed look identical from the digest. Trust that table over any manual
check: hand-fetching a feed from a browser and letting the runner fetch it can give
different answers.

## Maintenance and troubleshooting

Kept outside this repo, in the Instructions pack: the fortnightly cycle, editorial
standards, the tuning log, how to add or retire a source, and what to do when a run looks
wrong. Ask Leshan for the current copy.

## Licence

MIT — see `LICENSE`.
