#!/usr/bin/env python3
"""
EU MONITOR — automated European politics and policy early-warning system.

Pulls institutional EU (and UK) feeds, drops what has already been seen, and
scores what is left on two independent axes:

    BEAT     what the development is about   -> how the digest is organised
    SIGNALS  why it might matter             -> why an item was flagged

Machine judgement stops here. It produces a ranked flag list with the reasons
attached. A human decides what is actually worth publishing.

Standard library only. No pip install, no API keys, nothing to expire.

Usage:
    python3 collect.py                  # 14-day run, writes digests/YYYY-MM-DD.md
    python3 collect.py --check          # source health only, writes nothing
    python3 collect.py --days 7         # narrow the window
    python3 collect.py --dry-run        # print the digest, save nothing
    python3 collect.py --no-state       # ignore the seen-items store
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE_PATH = ROOT / "state" / "seen.json"
HISTORY_PATH = ROOT / "state" / "history.json"
DIGEST_DIR = ROOT / "digests"

USER_AGENT = (
    "Mozilla/5.0 (compatible; eu-monitor/2.0; personal EU policy monitoring; "
    "+https://github.com/)"
)
TIMEOUT = 30
MAX_STATE = 6000

ATOM = "{http://www.w3.org/2005/Atom}"
DC = "{http://purl.org/dc/elements/1.1/}"

# EUR-Lex titles arrive as "CELEX:52026PC0435: Proposal for a ..." — the useful
# text is everything after the identifier, and the identifier itself is noise to
# a keyword scorer.
CELEX_RE = re.compile(r"^CELEX:\s*[0-9A-Z()_]+\s*:\s*", re.I)


# ---------------------------------------------------------------------------
# fetching
# ---------------------------------------------------------------------------

def fetch(url: str, attempts: int = 3) -> bytes:
    last: Exception | None = None
    for _ in range(attempts):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": (
                        "application/rss+xml, application/atom+xml, "
                        "application/xml;q=0.9, */*;q=0.8"
                    ),
                    "Accept-Encoding": "gzip",
                },
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return raw
        except Exception as e:  # noqa: BLE001 — a dead feed must never kill the run
            last = e
    raise RuntimeError(f"{type(last).__name__}: {last}")


# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------

def _text(el) -> str:
    return "".join(el.itertext()).strip() if el is not None else ""


def strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    for a, b in (
        ("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
        ("&quot;", '"'), ("&#39;", "'"), ("&rsquo;", "'"), ("&ndash;", "-"),
    ):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def parse_date(s: str):
    if not s:
        return None
    s = s.strip()
    try:
        d = parsedate_to_datetime(s)
        if d is not None:
            return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
    except Exception:  # noqa: BLE001
        pass
    iso = s.replace("Z", "+00:00")
    for candidate in (iso, iso[:19], iso[:10]):
        try:
            d = dt.datetime.fromisoformat(candidate)
            return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
        except Exception:  # noqa: BLE001
            continue
    return None


def clean_title(title: str, source: dict) -> str:
    title = CELEX_RE.sub("", title)
    for prefix in source.get("strip_prefixes", []):
        if title.lower().startswith(prefix.lower()):
            title = title[len(prefix):]
    return title.strip(" -–—:")


def parse_feed(raw: bytes, source: dict) -> list[dict]:
    """One parser for RSS 2.0 and Atom.

    Two things here are load-bearing and were learned the hard way:

    * Several EU and UK feeds serve RSS but carry the timestamp in an
      Atom-namespaced <a10:updated> tag rather than <pubDate>. Without the
      fallback chain every one of their items parses undated.
    * Some feeds (EUR-Lex predefined feeds especially) date the channel but not
      the items. Sources can opt into `date_fallback: "channel"` so those items
      inherit the channel date instead of being silently discarded.
    """
    text = raw.decode("utf-8", errors="replace").lstrip()
    head = text[:300].lower()
    if head.startswith("<!doctype html") or "<html" in head:
        raise RuntimeError("returned HTML, not a feed")
    root = ET.fromstring(text)

    channel_date = parse_date(
        _text(root.find("./channel/pubDate"))
        or _text(root.find("./channel/lastBuildDate"))
        or _text(root.find(f"{ATOM}updated"))
    )

    nodes = root.findall(".//item")
    kind = "rss"
    if not nodes:
        nodes = root.findall(f".//{ATOM}entry")
        kind = "atom"

    use_channel_date = source.get("date_fallback") == "channel"
    items: list[dict] = []

    for n in nodes:
        if kind == "rss":
            title = _text(n.find("title"))
            link = _text(n.find("link"))
            summary = _text(n.find("description"))
            date = parse_date(
                _text(n.find("pubDate"))
                or _text(n.find(f"{DC}date"))
                or _text(n.find(f"{ATOM}updated"))
                or _text(n.find(f"{ATOM}published"))
            )
        else:
            title = _text(n.find(f"{ATOM}title"))
            link = ""
            for l in n.findall(f"{ATOM}link"):
                rel = l.get("rel", "alternate")
                if rel == "alternate" or not link:
                    link = l.get("href", "")
                    if rel == "alternate":
                        break
            summary = _text(n.find(f"{ATOM}summary")) or _text(n.find(f"{ATOM}content"))
            date = parse_date(
                _text(n.find(f"{ATOM}published")) or _text(n.find(f"{ATOM}updated"))
            )

        if date is None and use_channel_date:
            date = channel_date

        title = clean_title(strip_html(title), source)
        if not title:
            continue

        items.append({
            "title": title,
            "link": link.strip(),
            "summary": strip_html(summary)[:700],
            "date": date,
            "source": source["name"],
            "source_id": source["id"],
            "tier": source.get("tier", 2),
            "inherited_date": date is not None and use_channel_date,
        })
    return items


# ---------------------------------------------------------------------------
# scoring — two axes
# ---------------------------------------------------------------------------

# Keyword patterns are compiled once and cached. Plain substring matching was
# the original approach and it was quietly wrong: "uk" matched inside "Ukraine",
# "ai" matched inside "said", "chain" and "campaign", and "cap" matched inside
# "capital". Every one of those inflated scores on items that had nothing to do
# with the signal. Matching is now bounded on both sides.
#
# A keyword ending in "*" is a prefix stem: "criticis*" catches "criticise",
# "criticised" and "criticism", which is the one case where a trailing boundary
# is wrong. Shorter stems catch more — prefer "sanction*" over listing four
# inflections, and guard against false positives with the noise list rather
# than with longer phrases.
_PATTERN_CACHE: dict[str, "re.Pattern[str]"] = {}


def keyword_pattern(kw: str) -> "re.Pattern[str]":
    pat = _PATTERN_CACHE.get(kw)
    if pat is None:
        k = kw.lower().strip()
        if k.endswith("*"):
            body = re.escape(k[:-1])
            pat = re.compile(rf"(?<![a-z0-9]){body}[a-z]*", re.I)
        else:
            pat = re.compile(rf"(?<![a-z0-9]){re.escape(k)}(?![a-z0-9])", re.I)
        _PATTERN_CACHE[kw] = pat
    return pat


def _match(keywords: dict, title: str, body: str) -> tuple[int, list[str]]:
    """Title matches count double. Returns (score, matched keywords)."""
    score = 0
    hits: list[str] = []
    for kw, weight in keywords.items():
        p = keyword_pattern(kw)
        if p.search(title):
            score += weight * 2
            hits.append(kw)
        elif p.search(body):
            score += weight
            hits.append(kw)
    return score, hits


def score_item(item: dict, rules: dict) -> dict | None:
    """Score one item on both axes. Returns None if the noise filter kills it."""
    title = " " + item["title"].lower() + " "
    body = " " + item["summary"].lower() + " "

    for n in rules.get("noise", []):
        if keyword_pattern(n).search(title):
            return None

    # --- axis 1: beat -------------------------------------------------------
    beat_scores: dict[str, int] = {}
    beat_hits: dict[str, list[str]] = {}
    for beat in rules["beats"]:
        s, h = _match(beat["keywords"], title, body)
        if s:
            beat_scores[beat["id"]] = s
            beat_hits[beat["id"]] = h

    if not beat_scores:
        return None

    primary = max(beat_scores, key=lambda k: beat_scores[k])
    beat_total = sum(beat_scores.values())

    # --- axis 2: significance signals --------------------------------------
    signals: list[str] = []
    signal_total = 0
    signal_hits: dict[str, list[str]] = {}
    for sig in rules["signals"]:
        s, h = _match(sig["keywords"], title, body)
        if s >= sig.get("min_score", 2):
            signals.append(sig["id"])
            # Each signal contributes its weight times a CAPPED intensity. The
            # cap matters: without it a summary that happens to use six words
            # from one signal's list outscores an item that trips four
            # different signals, which is exactly backwards. Breadth of
            # reasons should beat repetition of one reason.
            signal_total += sig.get("weight", 1) * min(s, sig.get("cap", 4))
            signal_hits[sig["id"]] = h[:4]

    # A tier-1 primary institutional source gets a small edge over commentary.
    tier_bonus = rules.get("tier1_bonus", 2) if item.get("tier") == 1 else 0

    # The beat is capped too, for the same reason — a long summary about one
    # subject should not outrank a short one about something that matters.
    total = min(beat_total, rules.get("beat_cap", 30)) + signal_total + tier_bonus

    return {
        "score": total,
        "beat_score": beat_total,
        "signal_score": signal_total,
        "beat": primary,
        "beats": sorted(beat_scores, key=lambda k: -beat_scores[k]),
        "signals": signals,
        "signal_hits": signal_hits,
        "hits": sorted(set(beat_hits.get(primary, [])))[:6],
    }


def classify(scored: dict, rules: dict) -> str:
    """DETECTED -> SIGNIFICANT -> INVESTIGATE. The top tier is what you read first."""
    tiers = rules["flag_tiers"]
    inv = tiers["investigate"]
    sig = tiers["significant"]

    n_sig = len(scored["signals"])
    has_required = bool(set(scored["signals"]) & set(inv.get("requires_any", [])))

    if (scored["score"] >= inv["min_score"]
            and n_sig >= inv["min_signals"]
            and (has_required or not inv.get("requires_any"))):
        return "investigate"
    if scored["score"] >= sig["min_score"] and n_sig >= sig["min_signals"]:
        return "significant"
    return "detected"


# ---------------------------------------------------------------------------
# state
# ---------------------------------------------------------------------------

def item_key(item: dict) -> str:
    basis = item["link"] or item["title"]
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:  # noqa: BLE001
            pass
    return default


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state["seen"] = state["seen"][-MAX_STATE:]
    STATE_PATH.write_text(json.dumps(state, indent=1))


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------

EDITORIAL_QUESTIONS = [
    "What actually happened?",
    "What changed?",
    "Why did it happen?",
    "Who does it affect?",
    "Why should a young person care?",
    "What is the wider political significance?",
    "What happens next?",
]


def signal_label(sid: str, rules: dict) -> str:
    for s in rules["signals"]:
        if s["id"] == sid:
            return s["name"]
    return sid


def beat_label(bid: str, rules: dict) -> str:
    for b in rules["beats"]:
        if b["id"] == bid:
            return b["name"]
    return bid


def fmt_date(d) -> str:
    return f"{d:%d %b}" if d else "undated"


def render(buckets: dict, health: list, rules: dict, window: int,
           now: dt.datetime, stats: dict) -> str:
    out: list[str] = []
    inv = buckets["investigate"]
    sig = buckets["significant"]
    det = buckets["detected"]

    # ---- the dashboard ----------------------------------------------------
    out += [
        f"# EU MONITOR — {window} DAYS",
        "",
        "```",
        f"WINDOW        {now - dt.timedelta(days=window):%d %b %Y} → {now:%d %b %Y}",
        f"SOURCES       {stats['sources_ok']}/{stats['sources_total']} returned a feed"
        + (f"   ({stats['sources_stale']} stale)" if stats["sources_stale"] else ""),
        "",
        f"{stats['detected']:>4}  developments detected",
        f"{stats['significant']:>4}  potentially significant",
        f"{stats['investigate']:>4}  worth investigating",
        f"{'?':>4}  selected for publication   ← your call",
        "```",
        "",
        "*Machine judgement ends at the flag. Everything below is raw material: "
        "what the system thinks might matter, and why it thinks so. What is "
        "actually worth publishing is a human decision.*",
        "",
        "---",
        "",
    ]

    # ---- worth investigating ---------------------------------------------
    out += ["## ① Worth investigating", ""]
    if not inv:
        out += ["*Nothing cleared the investigate threshold this cycle. Read the "
                "significant list below, and check the source health table before "
                "concluding it was a quiet fortnight.*", ""]
    for i, it in enumerate(inv, 1):
        s = it["scored"]
        link = it["link"]
        title = f"[{it['title']}]({link})" if link else it["title"]
        out += [
            f"### {i}. {title}",
            "",
            f"`{beat_label(s['beat'], rules).upper()}`  ·  {it['source']}  ·  "
            f"{fmt_date(it['date'])}  ·  score **{s['score']}**",
            "",
            "**Why flagged:** " + ", ".join(
                signal_label(x, rules) for x in s["signals"]
            ),
            "",
        ]
        if it["summary"]:
            out += [f"> {it['summary'][:400]}", ""]
        out += ["<details><summary>Editorial worksheet</summary>", ""]
        for q in EDITORIAL_QUESTIONS:
            out += [f"**{q}**", "", "", ""]
        out += ["</details>", "", "---", ""]

    # ---- potentially significant -----------------------------------------
    out += ["## ② Potentially significant", "",
            "*Scan these. Promote anything the top tier missed.*", ""]
    if not sig:
        out += ["*None.*", ""]
    by_beat: dict[str, list] = {}
    for it in sig:
        by_beat.setdefault(it["scored"]["beat"], []).append(it)
    for beat in rules["beats"]:
        items = by_beat.get(beat["id"], [])
        if not items:
            continue
        out += [f"**{beat['name']}**", ""]
        for it in items:
            s = it["scored"]
            link = it["link"]
            title = f"[{it['title']}]({link})" if link else it["title"]
            flags = " · ".join(signal_label(x, rules) for x in s["signals"][:4])
            out += [f"- {title}  ",
                    f"  <sub>{it['source']} · {fmt_date(it['date'])} · "
                    f"score {s['score']} · {flags}</sub>"]
        out += [""]

    # ---- everything else --------------------------------------------------
    out += ["## ③ Also detected", "",
            "*Below the significance threshold. Skim the headlines, do not write "
            "them up. If something here should have been promoted, that is a "
            "rules.json problem — log it in `docs/TUNING-LOG.md`.*", ""]
    for it in det:
        link = it["link"]
        title = f"[{it['title']}]({link})" if link else it["title"]
        out += [f"- {title} — {it['source']}, {fmt_date(it['date'])}"]
    if not det:
        out += ["*None.*"]
    out += [""]

    # ---- source health ----------------------------------------------------
    out += ["---", "", "## Source health", ""]
    stale = [h for h in health if h.get("stale")]
    dead = [h for h in health if not h["ok"]]
    if stale:
        out += [
            f"> **{len(stale)} of {len(health)} sources are stale.** They parse "
            f"cleanly and report items, but their newest item is older than the "
            f"{window}-day window, so they contributed nothing. A quiet fortnight "
            "in Brussels and a rotted source list look identical from the digest. "
            "Read this table before you conclude it was quiet.",
            "",
        ]
    if dead:
        out += [f"> **{len(dead)} source(s) failed outright.** See the table.", ""]
    out += ["| Source | Tier | Status | Items | Newest | Age |",
            "|---|---|---|---|---|---|"]
    for h in health:
        if not h["ok"]:
            out.append(f"| {h['name']} | {h['tier']} | FAILED — {h['error']} | 0 | — | — |")
            continue
        status = "**STALE**" if h.get("stale") else "ok"
        newest = fmt_date(h["newest"]) if h.get("newest") else "no dated items"
        age = "—" if h.get("age") is None else f"{h['age']}d"
        und = f" ({h['undated']} undated)" if h.get("undated") else ""
        out.append(
            f"| {h['name']} | {h['tier']} | {status} | {h['count']}{und} | {newest} | {age} |"
        )
    out += [""]
    if stats.get("undated_dropped"):
        out += [
            f"*{stats['undated_dropped']} item(s) carried no readable date and were "
            "treated as out of window. If that number is large for one source, either "
            "its timestamp format is unread or it should be given "
            "`\"date_fallback\": \"channel\"` in sources.json.*",
            "",
        ]

    # ---- what happens next ------------------------------------------------
    out += [
        "---",
        "",
        "## Next step",
        "",
        "Pick the items you actually want to publish, then scaffold the edition:",
        "",
        "```bash",
        "python3 review.py --list                       # numbered flag list",
        "python3 review.py --new-edition 1 --select 1,3,4,7,9",
        "```",
        "",
        "That writes `editions/001/` with a Substack draft and one Instagram "
        "carousel script per selected development, each pre-filled with the "
        "source link and the seven editorial questions.",
        "",
    ]
    return "\n".join(out)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="EU Monitor — collect and flag.")
    ap.add_argument("--days", type=int, default=None, help="lookback window in days")
    ap.add_argument("--check", action="store_true", help="source health only")
    ap.add_argument("--dry-run", action="store_true", help="print, save nothing")
    ap.add_argument("--no-state", action="store_true", help="ignore the seen store")
    args = ap.parse_args()

    sources = json.loads((ROOT / "sources.json").read_text())["sources"]
    sources = [s for s in sources if s.get("enabled", True)]
    rules = json.loads((ROOT / "rules.json").read_text())

    window = args.days or rules.get("window_days", 14)
    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(days=window)
    stale_after = rules.get("stale_after_days", 21)

    all_items: list[dict] = []
    health: list[dict] = []

    for src in sources:
        try:
            items = parse_feed(fetch(src["url"]), src)
            dates = [i["date"] for i in items if i["date"]]
            newest = max(dates) if dates else None
            age = (now - newest).days if newest else None
            health.append({
                "name": src["name"], "tier": src.get("tier", 2), "ok": True,
                "count": len(items), "error": "", "newest": newest, "age": age,
                "undated": sum(1 for i in items if not i["date"]),
                "stale": age is not None and age > stale_after,
            })
            all_items.extend(items)
            flag = "  STALE" if (age is not None and age > stale_after) else ""
            print(f"  ok   {src['id']}: {len(items)} items, newest "
                  f"{age if age is not None else '?'}d old{flag}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            health.append({
                "name": src["name"], "tier": src.get("tier", 2), "ok": False,
                "count": 0, "error": str(e)[:110], "newest": None, "age": None,
                "undated": 0, "stale": False,
            })
            print(f"  FAIL {src['id']}: {e}", file=sys.stderr)

    if args.check:
        working = sum(1 for h in health if h["ok"])
        stale = sum(1 for h in health if h["stale"])
        print(f"\n{working}/{len(health)} sources returned a parseable feed.")
        if stale:
            print(f"{stale} of those have published nothing in over {stale_after} "
                  f"days — they parse, but contribute nothing to a {window}-day digest.")
        print()
        for h in health:
            if not h["ok"]:
                print(f"  FAIL   {h['name']:<52} {h['error']}")
                continue
            age = "no dated items" if h["age"] is None else f"newest {h['age']:>3}d old"
            mark = "STALE" if h["stale"] else "ok   "
            und = f"  ({h['undated']} undated)" if h["undated"] else ""
            print(f"  {mark}  {h['name']:<52} {h['count']:>3} items, {age}{und}")
        return 0 if working else 1

    state = {"seen": []} if args.no_state else load_json(STATE_PATH, {"seen": []})
    seen = set(state.get("seen", []))

    fresh: list[dict] = []
    undated_dropped = 0
    for it in all_items:
        # An undated item used to skip the window check and always qualify as
        # fresh, which let an entire static feed in on every run. Undated now
        # means out of window; sources that legitimately date only the channel
        # opt into date_fallback instead.
        if it["date"] is None:
            undated_dropped += 1
            continue
        if it["date"] < cutoff:
            continue
        key = item_key(it)
        if key in seen:
            continue
        it["key"] = key
        fresh.append(it)

    # The same story lands on several feeds. Keep the highest-tier copy.
    unique, run_seen = [], set()
    for it in sorted(fresh, key=lambda x: (x.get("tier", 2), x["title"])):
        norm = re.sub(r"[^a-z0-9]+", "", it["title"].lower())[:70]
        if norm in run_seen:
            continue
        run_seen.add(norm)
        unique.append(it)

    buckets = {"investigate": [], "significant": [], "detected": []}
    for it in unique:
        s = score_item(it, rules)
        if s is None:
            continue
        it["scored"] = s
        buckets[classify(s, rules)].append(it)

    for k in buckets:
        buckets[k].sort(key=lambda x: -x["scored"]["score"])

    caps = rules.get("caps", {})
    buckets["investigate"] = buckets["investigate"][: caps.get("investigate", 10)]
    buckets["significant"] = buckets["significant"][: caps.get("significant", 25)]
    buckets["detected"] = buckets["detected"][: caps.get("detected", 40)]

    n_inv, n_sig, n_det = (len(buckets[k]) for k in ("investigate", "significant", "detected"))
    stats = {
        "detected": n_inv + n_sig + n_det,
        "significant": n_inv + n_sig,
        "investigate": n_inv,
        "sources_ok": sum(1 for h in health if h["ok"]),
        "sources_total": len(health),
        "sources_stale": sum(1 for h in health if h["stale"]),
        "undated_dropped": undated_dropped,
    }

    digest = render(buckets, health, rules, window, now, stats)

    if args.dry_run:
        print(digest)
        return 0

    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DIGEST_DIR / f"{now:%Y-%m-%d}.md"
    out_path.write_text(digest)

    # A machine-readable sidecar next to every digest. review.py reads this
    # rather than parsing the markdown back out — the digest is for a human,
    # the sidecar is for the tooling, and neither has to compromise for the other.
    sidecar = {
        "generated": now.isoformat(),
        "window_days": window,
        "stats": stats,
        "flags": [
            {
                "n": n,
                "tier": tier,
                "title": it["title"],
                "link": it["link"],
                "source": it["source"],
                "date": it["date"].strftime("%Y-%m-%d") if it["date"] else None,
                "summary": it["summary"],
                "beat": it["scored"]["beat"],
                "beat_name": beat_label(it["scored"]["beat"], rules),
                "score": it["scored"]["score"],
                "signals": it["scored"]["signals"],
                "signal_names": [signal_label(x, rules) for x in it["scored"]["signals"]],
            }
            for n, (tier, it) in enumerate(
                [("investigate", i) for i in buckets["investigate"]]
                + [("significant", i) for i in buckets["significant"]],
                start=1,
            )
        ],
    }
    (DIGEST_DIR / f"{now:%Y-%m-%d}.json").write_text(json.dumps(sidecar, indent=1))
    print(f"\nwrote {out_path} — {n_inv} investigate, {n_sig} significant, "
          f"{n_det} detected", file=sys.stderr)

    if not args.no_state:
        state["seen"] = list(state.get("seen", [])) + [it["key"] for it in unique]
        state["last_run"] = now.isoformat()
        save_state(state)

        # A run log makes the system's own behaviour a thing you can chart —
        # useful for the brief, and honest about how much noise it filters.
        history = load_json(HISTORY_PATH, {"runs": []})
        history["runs"].append({
            "date": f"{now:%Y-%m-%d}", "window": window,
            **{k: stats[k] for k in
               ("detected", "significant", "investigate", "sources_ok",
                "sources_total", "sources_stale")},
        })
        history["runs"] = history["runs"][-200:]
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        HISTORY_PATH.write_text(json.dumps(history, indent=1))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
