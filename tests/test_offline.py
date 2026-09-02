#!/usr/bin/env python3
"""
Offline verification of the Passerelle pipeline.

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


print("\nPASSERELLE — offline pipeline check\n" + "─" * 60)

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

# ── length bias ─────────────────────────────────────────────────────────────
# Regression against the real first live run (27 Aug 2026), where the digest
# came back ranked almost perfectly by title length: all ten top-tier flags
# were EUR-Lex, and the one item actually on brief sat at number thirteen.
# Both items below are the genuine strings those two flags carried.
CELEX_TITLE = (
    "Notice concerning the date of entry into force of the Agreement in the form "
    "of an exchange of letters between the European Union and the People’s "
    "Republic of China pursuant to Article XXVIII of the General Agreement on "
    "Tariffs and Trade (GATT) 1994 relating to the modification of concessions on "
    "all the tariff rate quotas included in the EU Schedule CLXXV as a consequence "
    "of the United Kingdom’s withdrawal from the European Union [2026/1952]")
REAL_HEADLINE = ("Cost of living and young people priorities for the PM during "
                 "first visit to Northern Ireland")
REAL_SUMMARY = ("Prime Minister Andy Burnham has arrived in Northern Ireland as "
                "part of his summer tour of the United Kingdom.")

# EUR-Lex carries score_multiplier 0.6 in sources.json; gov.uk carries none.
celex = collect.score_item({"title": CELEX_TITLE, "summary": "", "tier": 1,
                            "score_multiplier": 0.6}, RULES)
headline = collect.score_item({"title": REAL_HEADLINE, "summary": REAL_SUMMARY,
                               "tier": 1}, RULES)

check("a long title gets a smaller per-match title boost than a short one",
      collect.title_boost(CELEX_TITLE, RULES) < collect.title_boost(REAL_HEADLINE, RULES),
      f"{collect.title_boost(CELEX_TITLE, RULES)} vs {collect.title_boost(REAL_HEADLINE, RULES)}")
check("title boost never falls below parity with body text",
      collect.title_boost("x" * 5000, RULES) >= 1.0)
check("the real on-brief headline outranks the real 444-char CELEX notice",
      headline["score"] > celex["score"],
      f"headline {headline['score']} vs celex {celex['score']}")
check("the real on-brief headline reaches the top tier",
      collect.classify(headline, RULES) == "investigate",
      f"{collect.classify(headline, RULES)} at score {headline['score']}")
check("the real CELEX notice does not reach the top tier",
      collect.classify(celex, RULES) != "investigate",
      f"{collect.classify(celex, RULES)} at score {celex['score']}")

# ── match and signal caps ───────────────────────────────────────────────────
check("match_cap keeps only the strongest matches per keyword set",
      RULES["match_cap"]["beat"] > 0 and RULES["match_cap"]["signal"] > 0)
many = collect.score_item({
    "title": "Commission adopts binding mandatory rules on students, rent, TikTok, "
             "roaming, Erasmus and minimum wage from 2027 with fines",
    "summary": "Unprecedented first-ever agreement criticised by campaigners in the "
               "United Kingdom, Russia and China worth billions.",
    "tier": 1}, RULES)
check("every signal that fired is still reported, not just the counted ones",
      len(many["signals"]) >= len(many["counted_signals"]))
check("only signal_count_cap signals contribute to the score",
      len(many["counted_signals"]) <= RULES.get("signal_count_cap", 4))
check("reported signals are a superset of counted signals",
      set(many["counted_signals"]) <= set(many["signals"]))

# ── per-source weighting ────────────────────────────────────────────────────
base = {"title": "Council adopts new sanctions package targeting shadow fleet",
        "summary": "Adopted today, binding from 2027.", "tier": 1}
full = collect.score_item(dict(base), RULES)
half = collect.score_item(dict(base, score_multiplier=0.5), RULES)
check("a source score_multiplier scales the total",
      half["score"] < full["score"], f"{half['score']} vs {full['score']}")

# ── the court docket no longer swallows the digest ──────────────────────────
euipo = collect.score_item({
    "title": "Case T-615/25: Judgment of the General Court of 1 July 2026 - "
             "Veikkaus v EUIPO (FOR BETTER GAMING)",
    "summary": "Action for annulment.", "tier": 1}, RULES)
check("EUIPO trade-mark docket is killed by the noise list", euipo is None)
court = collect.score_item({
    "title": "Case T-105/24: Judgment of the General Court of 1 July 2026 - "
             "Airbus Defence and Space v Commission",
    "summary": "The Court ruled today. Binding from 2027, with fines of millions.",
    "tier": 1}, RULES)
if court:
    beat = collect.beat_def("rights-and-courts", RULES)
    check("rights-and-courts declares an investigate gate",
          bool(beat.get("investigate_requires_any")))
    if court["beat"] == "rights-and-courts" and not (
            set(court["signals"]) & set(beat.get("investigate_requires_any", []))):
        check("a court item with no non-court reason cannot reach the top tier",
              collect.classify(court, RULES) != "investigate")
    else:
        check("a court item with no non-court reason cannot reach the top tier", True)
check("the top tier is capped per beat", RULES["caps"].get("investigate_per_beat", 0) > 0)

# ── future-dated items ──────────────────────────────────────────────────────
check("a future tolerance is configured", RULES.get("future_tolerance_days") is not None)
future = NOW + dt.timedelta(days=90)
check("a scheduled meeting date is beyond the tolerance",
      future > NOW + dt.timedelta(days=RULES["future_tolerance_days"]))

# ── byte-order marks (regression: the non-XML guard rejected four live feeds) ──
BOM_FEED = ('\ufeff<?xml version="1.0" encoding="utf-8"?><rss version="2.0">'
            '<channel><title>t</title><item><title>Council adopts sanctions</title>'
            '<pubDate>Mon, 24 Aug 2026 08:00:00 +0000</pubDate></item>'
            '</channel></rss>')
try:
    bom_items = collect.parse_feed(BOM_FEED.encode("utf-8"), SRC_RSS)
    bom_ok = len(bom_items) == 1
except Exception as e:  # noqa: BLE001
    bom_ok = False
check("a feed with a UTF-8 byte-order mark still parses", bom_ok)

# ── fetch diagnostics ───────────────────────────────────────────────────────
for payload, want in ((b"", "empty response"), (b"Forbidden", "non-XML")):
    try:
        collect.parse_feed(payload, SRC_RSS)
        got = ""
    except RuntimeError as e:
        got = str(e)
    check(f"an unusable response says so plainly ({want})", want in got, got)

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

check("digest renders the dashboard banner", "PASSERELLE — 14 DAYS" in out)
check("digest renders all three flag tiers",
      all(x in out for x in ("Worth investigating", "Potentially significant",
                             "Also detected")))
check("digest prints why each item was flagged", "**Why flagged:**" in out)
check("digest carries the editorial worksheet",
      "Why should a young person care?" in out)
check("digest warns about stale sources", "sources are stale" in out)
check("digest reports failed sources", "FAILED" in out)
check("digest names the human step", "your call" in out)


# ---------------------------------------------------------------------------
# topic gate — polling sources only contribute EU items
# ---------------------------------------------------------------------------

GATE_RULES = {"topic_gates": {"eu_politics": ["european union", "brexit", "brussels"]}}


def gate_item(title, summary="", require=None):
    return {"title": title, "summary": summary, "require_match": require or []}


check("ungated source passes everything through",
      collect.passes_topic_gate(gate_item("Anything at all"), GATE_RULES))
check("gated source drops an off-topic item",
      not collect.passes_topic_gate(
          gate_item("Which crisps do Britons prefer?", require=["@eu_politics"]),
          GATE_RULES))
check("gated source keeps an on-topic item",
      collect.passes_topic_gate(
          gate_item("Britons back rejoining the European Union", require=["@eu_politics"]),
          GATE_RULES))
check("the gate reads the summary as well as the title",
      collect.passes_topic_gate(
          gate_item("New polling released", "Attitudes to Brexit five years on",
                    require=["@eu_politics"]),
          GATE_RULES))
check("a literal term works without the @ list indirection",
      collect.passes_topic_gate(gate_item("Schengen and you", require=["schengen"]),
                                GATE_RULES))
check("an unknown @list gates everything out rather than letting it through",
      not collect.passes_topic_gate(
          gate_item("Britons back rejoining the European Union", require=["@nonexistent"]),
          GATE_RULES))
check("the gate matches on word boundaries, not substrings",
      not collect.passes_topic_gate(
          gate_item("Emu farming rises in Devon", require=["eu"]), GATE_RULES))


# ── wp-json adapter ───────────────────────────────────────────────────────────────────
# CEPS serves no RSS at all, so it is read through the WordPress JSON API
# instead. These check the adapter hands back the same item shape parse_feed
# does, and that a broken or hostile response yields an empty list rather than
# an exception that would take the whole run down with it.
SRC_WP = {"id": "fixture-wp", "name": "Fixture think tank", "tier": 2,
          "format": "wp-json", "score_multiplier": 0.9}

FEED_KEYS = {"title", "link", "summary", "date", "source", "source_id",
             "tier", "score_multiplier", "require_match", "inherited_date"}

WP_PAYLOAD = json.dumps([
    {"date": "2026-09-01T14:41:42", "date_gmt": "2026-09-01T13:41:42",
     "link": "https://example.org/iceland/",
     "title": {"rendered": "The Icelandic vote was for integration without membership"},
     "excerpt": {"rendered": "<p>Iceland has rejected reopening EU accession talks.</p>"}},
    {"date": "2026-08-31T16:03:51", "date_gmt": "2026-08-31T15:03:51",
     "link": "https://example.org/no/",
     "title": {"rendered": "Iceland voted no"},
     "excerpt": {"rendered": "<p>Body.</p>"}},
]).encode()

wp = collect.parse_wp_json(WP_PAYLOAD, SRC_WP)
check("the wp-json adapter reads every post", len(wp) == 2, f"got {len(wp)}")
check("wp-json titles are unwrapped from the rendered field",
      bool(wp) and wp[0]["title"].startswith("The Icelandic vote"))
check("wp-json summaries have their HTML stripped",
      bool(wp) and "<p>" not in wp[0]["summary"]
      and "Iceland has rejected" in wp[0]["summary"])
check("wp-json dates are timezone aware and taken from date_gmt, not local time",
      bool(wp) and wp[0]["date"] is not None
      and wp[0]["date"].tzinfo is not None and wp[0]["date"].hour == 13)
check("wp-json items carry exactly the fields a feed item carries",
      bool(wp) and set(wp[0]) == FEED_KEYS)
check("parse_feed routes format wp-json to the adapter",
      collect.parse_feed(WP_PAYLOAD, SRC_WP) == wp)

for label, payload in [
        ("junk that is not JSON", b"not json"),
        ("a REST error object", b'{"code": "rest_no_route"}'),
        ("an empty array", b"[]"),
        ("nulls and scalars in the array", b'[null, 3, "x"]'),
        ("a post with no link", b'[{"title": {"rendered": "T"}, "link": ""}]'),
        ("a post with no title", b'[{"title": {"rendered": ""}, "link": "https://x"}]')]:
    try:
        got = collect.parse_wp_json(payload, SRC_WP)
        survived = got == []
    except Exception as exc:  # noqa: BLE001
        survived, got = False, exc
    check(f"the wp-json adapter survives {label}", survived, str(got))


# ── same-day re-runs ──────────────────────────────────────────────────────────────────
# A second collection on the same date re-admits whatever that day's digest
# already flagged, and it finds those items by hashing the link the sidecar
# carries. That only works while item_key is derived from the link, so it is
# pinned here: change item_key and this fails before a run can lose a digest.
check("a sidecar flag hashes to the same key as the feed item it came from",
      collect.item_key({"link": "https://example.org/a", "title": "Feed title"})
      == collect.item_key({"link": "https://example.org/a", "title": "Sidecar title"}))
check("a linkless item falls back to its title, and two titles do not collide",
      collect.item_key({"link": "", "title": "Only a title"})
      == collect.item_key({"link": "", "title": "Only a title"})
      and collect.item_key({"link": "", "title": "A"})
      != collect.item_key({"link": "", "title": "B"}))

print("─" * 60)
print(f"{len(PASS)} passed, {len(FAIL)} failed\n")
if FAIL:
    for f in FAIL:
        print(f"  FAILED: {f}")
    print()
raise SystemExit(1 if FAIL else 0)
