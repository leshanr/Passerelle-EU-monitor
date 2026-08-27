#!/usr/bin/env python3
"""
Offline verification of the EU Monitor pipeline.

No network. Every feed is a fixture in tests/fixtures/. The point is that a
scheduled run should never be the first time you find out the parser broke —
this runs first in CI and the collect step does not execute if it fails.

    python3 tests/test_offline.py
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(ROOT))

import collect  # noqa: E402

PASS, FAIL = [], []


def check(name: str, condition: bool, detail: str = "") -> None:
    (PASS if condition else FAIL).append(name)
    mark = "  ok  " if condition else "  FAIL"
    print(f"{mark}  {name}" + (f"   — {detail}" if detail and not condition else ""))


RULES = json.loads((ROOT / "rules.json").read_text())
NOW = dt.datetime(2026, 8, 27, tzinfo=dt.timezone.utc)

SRC_RSS = {"id": "fixture-rss", "name": "Fixture press feed", "tier": 1}
SRC_ATOM = {"id": "fixture-atom", "name": "Fixture UK feed", "tier": 2}
SRC_EURLEX = {"id": "fixture-eurlex", "name": "Fixture EUR-Lex",
              "tier": 1, "date_fallback": "channel"}


def load(fixture: str, src: dict) -> list[dict]:
    return collect.parse_feed((FIX / fixture).read_bytes(), src)


print("\nEU MONITOR — offline pipeline check\n" + "─" * 60)

# ── parsing ────────────────────────────────────────────────────────────────
rss = load("sample_rss.xml", SRC_RSS)
atom = load("sample_atom.xml", SRC_ATOM)
eurlex = load("sample_eurlex.xml", SRC_EURLEX)

check("RSS 2.0 parses", len(rss) == 6, f"got {len(rss)}")
check("Atom parses", len(atom) == 2, f"got {len(atom)}")
check("Atom link uses rel=alternate href",
      atom[0]["link"] == "https://example.gov.uk/youth-mobility")
try:
    collect.parse_feed(b"<!DOCTYPE html><html><body>moved</body></html>", SRC_RSS)
    html_rejected = False
except RuntimeError:
    html_rejected = True
check("HTML served instead of a feed raises", html_rejected)

# ── date handling ──────────────────────────────────────────────────────────
by_title = {i["title"]: i for i in rss}
sanctions = by_title["Council adopts new sanctions package targeting shadow fleet"]
check("a10:updated read when pubDate is absent",
      sanctions["date"] is not None and sanctions["date"].day == 19,
      f"got {sanctions['date']}")

check("undated items stay undated without date_fallback",
      all(i["date"] is not None for i in rss))

check("date_fallback inherits the channel date",
      eurlex[0]["date"] is not None and eurlex[0]["date"].day == 23,
      f"got {eurlex[0]['date']}")
check("inherited dates are marked as such", eurlex[0]["inherited_date"] is True)

# ── title cleaning ─────────────────────────────────────────────────────────
check("CELEX identifier stripped from the title",
      eurlex[0]["title"].startswith("Proposal for a REGULATION"),
      eurlex[0]["title"][:50])

# ── noise filter ───────────────────────────────────────────────────────────
advisory = by_title["Media advisory - General Affairs Council of 16 September 2026"]
diary = by_title["Weekly schedule of President von der Leyen"]
travel = [i for i in atom if i["title"].startswith("Travel advice")][0]
check("media advisory killed by the noise list",
      collect.score_item(advisory, RULES) is None)
check("diary item killed by the noise list",
      collect.score_item(diary, RULES) is None)
check("travel advice killed by the noise list",
      collect.score_item(travel, RULES) is None)

# ── scoring: beats ─────────────────────────────────────────────────────────
air = collect.score_item(by_title[
    "Deal on air passenger rights: MEPs secure improved traveller protection"], RULES)
age = collect.score_item(by_title[
    "Commission proposes first-ever EU rules on age verification for social media"], RULES)
sanc = collect.score_item(sanctions, RULES)
ymob = collect.score_item(atom[0], RULES)
plat = collect.score_item(eurlex[0], RULES)

check("air passenger rights lands on borders-and-moving",
      air["beat"] == "borders-and-moving", air["beat"])
check("age verification lands on tech-and-online-life",
      age["beat"] == "tech-and-online-life", age["beat"])
check("sanctions package lands on war-and-security",
      sanc["beat"] == "war-and-security", sanc["beat"])
check("youth mobility lands on uk-and-europe",
      ymob["beat"] == "uk-and-europe", ymob["beat"])
check("platform work proposal lands on money-and-work",
      plat["beat"] == "money-and-work", plat["beat"])

# ── scoring: signals ───────────────────────────────────────────────────────
check("'provisional agreement' fires the decided signal",
      "decided" in air["signals"], str(air["signals"]))
check("'first-ever' fires the unusual signal",
      "unusual" in age["signals"], str(age["signals"]))
check("'proposes'/'unveiled' fires the new signal",
      "new" in age["signals"], str(age["signals"]))
check("'criticised'/'watered down' fires the contested signal",
      "contested" in air["signals"], str(air["signals"]))
check("'binding'/'mandatory'/'fines' fires the consequential signal",
      "consequential" in age["signals"], str(age["signals"]))
check("student/traveller language fires the youth signal",
      "youth" in air["signals"], str(air["signals"]))
check("UK content fires the uk signal",
      "uk" in ymob["signals"], str(ymob["signals"]))
check("Hungary veto fires the unusual signal on the sanctions item",
      "unusual" in sanc["signals"], str(sanc["signals"]))

# ── keyword boundaries (regression: substring matching was silently wrong) ──
BOUNDARY = [
    ("uk", " russia and ukraine talks ", False, "'uk' must not match inside 'Ukraine'"),
    ("uk", " the uk government said ", True, "'uk' must match a standalone UK"),
    ("ai", " said the chain of command ", False, "'ai' must not match inside said/chain"),
    ("ai", " the ai act enters into force ", True, "'ai' must match standalone AI"),
    ("cap", " capital markets union ", False, "'cap' must not match inside 'capital'"),
    ("cap", " a price cap on gas ", True, "'cap' must match a standalone cap"),
    ("criticis*", " campaigners criticised it ", True, "stems match inflections"),
    ("sanction*", " new sanctions package ", True, "stems match plurals"),
    ("erasmus", " the erasmus+ programme ", True, "a trailing + is a boundary"),
]
for kw, hay, want, why in BOUNDARY:
    check(f"boundary: {why}",
          bool(collect.keyword_pattern(kw).search(hay)) is want)

check("Erasmus alone no longer fires the UK signal",
      "erasmus" not in {k.lower() for s_ in RULES["signals"] if s_["id"] == "uk"
                        for k in s_["keywords"]})

# ── title weighting ────────────────────────────────────────────────────────
t_only = {"title": "Erasmus funding doubled", "summary": "", "tier": 2}
b_only = {"title": "Committee meets", "summary": "Erasmus funding doubled", "tier": 2}
st, sb = collect.score_item(t_only, RULES), collect.score_item(b_only, RULES)
check("a title match outweighs the same match in the body",
      st["beat_score"] > sb["beat_score"], f"{st['beat_score']} vs {sb['beat_score']}")

# ── tier bonus ─────────────────────────────────────────────────────────────
t1 = dict(t_only, tier=1)
check("tier-1 sources get a scoring edge",
      collect.score_item(t1, RULES)["score"] > st["score"])

# ── classification ─────────────────────────────────────────────────────────
check("a multi-signal high-score item reaches investigate",
      collect.classify(age, RULES) == "investigate",
      f"{collect.classify(age, RULES)} score={age['score']} sig={age['signals']}")
weak = collect.score_item({"title": "Cloud market data", "summary": "", "tier": 2}, RULES)
check("a thin single-signal item does not reach investigate",
      weak is None or collect.classify(weak, RULES) != "investigate")

check("investigate requires one of the required signals",
      all(set(RULES["flag_tiers"]["investigate"]["requires_any"]) & set(s)
          for s in [age["signals"], air["signals"]]))

# ── config integrity ───────────────────────────────────────────────────────
sources = json.loads((ROOT / "sources.json").read_text())["sources"]
ids = [s["id"] for s in sources]
check("source ids are unique", len(ids) == len(set(ids)))
check("every source has a url and a tier",
      all(s.get("url") and s.get("tier") in (1, 2) for s in sources))
check("every beat has a unique id and keywords",
      len({b["id"] for b in RULES["beats"]}) == len(RULES["beats"])
      and all(b.get("keywords") for b in RULES["beats"]))
check("every signal has a unique id and keywords",
      len({s["id"] for s in RULES["signals"]}) == len(RULES["signals"])
      and all(s.get("keywords") for s in RULES["signals"]))
check("investigate threshold sits above significant",
      RULES["flag_tiers"]["investigate"]["min_score"]
      > RULES["flag_tiers"]["significant"]["min_score"])
check("requires_any names real signals",
      set(RULES["flag_tiers"]["investigate"]["requires_any"])
      <= {s["id"] for s in RULES["signals"]})
check("window is fortnightly", RULES["window_days"] == 14)

# ── rendering ──────────────────────────────────────────────────────────────
items = []
for it in rss + atom + eurlex:
    s = collect.score_item(it, RULES)
    if s:
        it["scored"] = s
        items.append(it)
buckets = {"investigate": [], "significant": [], "detected": []}
for it in items:
    buckets[collect.classify(it["scored"], RULES)].append(it)
health = [{"name": "Fixture press feed", "tier": 1, "ok": True, "count": 6,
           "error": "", "newest": NOW - dt.timedelta(days=5), "age": 5,
           "undated": 0, "stale": False},
          {"name": "Dead feed", "tier": 1, "ok": True, "count": 20, "error": "",
           "newest": NOW - dt.timedelta(days=70), "age": 70, "undated": 0,
           "stale": True},
          {"name": "Broken feed", "tier": 2, "ok": False, "count": 0,
           "error": "returned HTML, not a feed", "newest": None, "age": None,
           "undated": 0, "stale": False}]
stats = {"detected": len(items), "significant": len(buckets["investigate"]) + len(buckets["significant"]),
         "investigate": len(buckets["investigate"]), "sources_ok": 2,
         "sources_total": 3, "sources_stale": 1, "undated_dropped": 0}
out = collect.render(buckets, health, RULES, 14, NOW, stats)

check("digest renders the dashboard banner", "EU MONITOR — 14 DAYS" in out)
check("digest renders all three flag tiers",
      all(x in out for x in ("Worth investigating", "Potentially significant",
                             "Also detected")))
check("digest prints why each item was flagged", "**Why flagged:**" in out)
check("digest carries the editorial worksheet",
      "Why should a young person care?" in out)
check("digest warns about stale sources", "sources are stale" in out)
check("digest reports failed sources", "FAILED" in out)
check("digest names the human step", "your call" in out)

print("─" * 60)
print(f"{len(PASS)} passed, {len(FAIL)} failed\n")
if FAIL:
    for f in FAIL:
        print(f"  FAILED: {f}")
    print()
raise SystemExit(1 if FAIL else 0)
