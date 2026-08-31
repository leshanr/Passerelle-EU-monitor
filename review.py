#!/usr/bin/env python3
"""
PASSERELLE — the human layer.

collect.py stops at "this looks potentially significant". This is the other
half: you read the flags, you decide what is actually worth publishing, and
this scaffolds the edition around your choices.

The distinction matters enough to be enforced in the file layout. Nothing in
`editions/` is ever written by the automated run.

Usage:
    python3 review.py --list                          # numbered flags, newest digest
    python3 review.py --list --signals youth,unusual  # only flags carrying these
    python3 review.py --new-edition 1 --select 1,3,4,7,9
    python3 review.py --status                        # where you are in the cycle
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIGEST_DIR = ROOT / "digests"
EDITIONS = ROOT / "editions"

QUESTIONS = [
    ("What actually happened?",
     "Two sentences, no jargon. If you cannot write it without the word 'framework', you do not understand it yet."),
    ("What changed?",
     "The before and the after. This is the sentence most EU coverage skips."),
    ("Why did it happen?",
     "Who pushed for it and what were they trying to fix or win."),
    ("Who does it affect?",
     "Name them. 'Stakeholders' is not a person."),
    ("Why should a young person care?",
     "The whole publication lives or dies here. If the honest answer is 'they shouldn't', cut the item."),
    ("What is the wider political significance?",
     "What this tells you about where European politics is going."),
    ("What happens next?",
     "A date if there is one. Readers remember things that have a next step."),
]


def latest_sidecar() -> Path | None:
    files = sorted(DIGEST_DIR.glob("*.json"))
    return files[-1] if files else None


def load_flags(path: Path) -> dict:
    return json.loads(path.read_text())


def cmd_list(args) -> int:
    path = latest_sidecar()
    if not path:
        print("No digest found. Run:  python3 collect.py", file=sys.stderr)
        return 1
    data = load_flags(path)
    wanted = set(x.strip() for x in args.signals.split(",")) if args.signals else None

    s = data["stats"]
    print(f"\n  PASSERELLE — {data['window_days']} DAYS   (digest {path.stem})")
    print(f"  {s['detected']} detected · {s['significant']} potentially significant "
          f"· {s['investigate']} worth investigating")
    if s.get("sources_stale"):
        print(f"  ⚠  {s['sources_stale']} of {s['sources_total']} sources stale — "
              f"check the health table before trusting a thin list")
    print()

    current = None
    shown = 0
    for f in data["flags"]:
        if wanted and not (wanted & set(f["signals"])):
            continue
        if f["tier"] != current:
            current = f["tier"]
            label = ("① WORTH INVESTIGATING" if current == "investigate"
                     else "② POTENTIALLY SIGNIFICANT")
            print(f"  {label}\n  " + "─" * 72)
        title = f["title"][:88] + ("…" if len(f["title"]) > 88 else "")
        print(f"  [{f['n']:>2}] {title}")
        print(f"       {f['beat_name']} · {f['source']} · {f['date'] or 'undated'} "
              f"· score {f['score']}")
        print(f"       why: {', '.join(f['signal_names'])}")
        print()
        shown += 1

    if not shown:
        print("  Nothing matched.\n")
    else:
        print(f"  Select with:  python3 review.py --new-edition N --select "
              f"{','.join(str(f['n']) for f in data['flags'][:5])}\n")
    return 0


def slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:60]


def cmd_new_edition(args) -> int:
    path = latest_sidecar()
    if not path:
        print("No digest found. Run:  python3 collect.py", file=sys.stderr)
        return 1
    data = load_flags(path)
    by_n = {f["n"]: f for f in data["flags"]}

    try:
        picked = [int(x) for x in args.select.split(",") if x.strip()]
    except ValueError:
        print("--select takes numbers, e.g. --select 1,3,4", file=sys.stderr)
        return 1

    missing = [n for n in picked if n not in by_n]
    if missing:
        print(f"No flag numbered {missing} in {path.stem}. "
              f"Valid range is 1–{len(data['flags'])}.", file=sys.stderr)
        return 1

    items = [by_n[n] for n in picked]
    num = f"{args.new_edition:03d}"
    ed = EDITIONS / num
    if ed.exists() and not args.force:
        print(f"editions/{num}/ already exists. Use --force to overwrite.", file=sys.stderr)
        return 1
    (ed / "assets").mkdir(parents=True, exist_ok=True)

    today = dt.date.today()
    publish = today + dt.timedelta(days=3)

    # ---- the Substack draft ------------------------------------------------
    b = [
        f"# PASSERELLE #{num}",
        "",
        f"### The last two weeks in European politics, without the Brussels-induced headache.",
        "",
        f"*{today:%d %B %Y} · {len(items)} developments · about a 10-minute read*",
        "",
        "<!-- ─────────────────────────────────────────────────────────────",
        "     THE OPENER — 60 words. One paragraph. What the fortnight was",
        "     actually about. Write this LAST, once you know what the issue",
        "     turned out to be about.",
        "     ───────────────────────────────────────────────────────────── -->",
        "",
        "TK opener.",
        "",
        "---",
        "",
    ]
    for i, f in enumerate(items, 1):
        lead = "**THE BIG ONE**" if i == 1 else f"**{i}.**"
        b += [
            f"## {lead} {f['title']}",
            "",
            f"<sub>{f['beat_name']} · {f['source']} · {f['date'] or 'undated'} · "
            f"[primary source]({f['link']})</sub>",
            "",
            f"<!-- flagged because: {', '.join(f['signal_names'])} -->",
            f"<!-- feed summary: {f['summary'][:300]} -->",
            "",
        ]
        for q, hint in QUESTIONS:
            b += [f"**{q}**", f"<!-- {hint} -->", "", "TK", ""]
        b += ["---", ""]

    b += [
        "## 📊 One number",
        "",
        "<!-- One statistic, chart or map per issue. It is the most shared thing",
        "     you will publish and it takes twenty minutes. Source it. -->",
        "",
        "TK",
        "",
        "---",
        "",
        "## 🃏 And finally",
        "",
        "<!-- One lighter or genuinely odd European development. Not filler —",
        "     it is what makes people forward the email. -->",
        "",
        "TK",
        "",
        "---",
        "",
        "*Passerelle is written by Leshan and built on an automated monitoring",
        "pipeline that watches EU institutional sources continuously. The code is",
        "open: github.com/leshanr/Passerelle-EU-monitor*",
        "",
        f"*This issue was selected from {data['stats']['detected']} developments the",
        f"system detected over {data['window_days']} days, of which",
        f"{data['stats']['investigate']} were flagged as worth investigating.*",
        "",
    ]
    (ed / "brief.md").write_text("\n".join(b))

    # ---- one Instagram carousel script per selected development ------------
    SLIDES = [
        ("HOOK", "THE EU JUST {VERB} {THING}.\nHere's what actually happened.",
         "Six words maximum on the top line. If it needs a comma it is too long."),
        ("WHAT HAPPENED", "", "Two sentences. The news, plainly."),
        ("WHAT CHANGED", "", "Before → after. Use the arrow. This is the slide people screenshot."),
        ("WHY DID THE EU DO THIS", "", "The motive. Who pushed, what they wanted."),
        ("WHO DOES IT AFFECT", "", "Named groups and a number if you have one. Consider a map here."),
        ("WHY SHOULD YOU CARE", "", "The single most important slide. Concrete, personal, no hedging."),
        ("WHAT HAPPENS NEXT", "", "A date. Then the source link and the Substack call to action."),
    ]
    for i, f in enumerate(items, 1):
        c = [
            f"# CAROUSEL {i:02d} — {f['title'][:70]}",
            "",
            f"**Edition:** #{num}  ·  **Beat:** {f['beat_name']}  ·  "
            f"**Publish:** {publish:%d %b}",
            f"**Source:** {f['source']}, {f['date'] or 'undated'} — {f['link']}",
            f"**Flagged because:** {', '.join(f['signal_names'])}",
            "",
            "**Visual device for this one:** <!-- map / timeline / bar chart / "
            "before-after / comparison table / screenshot / metaphor — pick ONE "
            "and build the carousel around it -->",
            "",
            "---",
            "",
        ]
        for n, (label, draft, hint) in enumerate(SLIDES, 1):
            c += [
                f"## Slide {n} — {label}",
                "",
                f"> {draft}" if draft else "> TK",
                "",
                f"<!-- {hint} -->",
                "",
                "`visual:` ",
                "",
            ]
        c += [
            "---",
            "",
            "## Caption",
            "",
            "TK — two sentences plus the Substack link. Front-load the payoff; "
            "Instagram truncates at about 125 characters.",
            "",
            "## Hashtags",
            "",
            "#EUpolitics #Europe #EuropeanUnion #politics #explainer",
            "",
            "## Alt text",
            "",
            "<!-- One line per slide. Not optional. -->",
            "",
        ]
        (ed / f"carousel-{i:02d}-{slugify(f['title'])}.md").write_text("\n".join(c))

    # ---- production checklist ---------------------------------------------
    chk = [
        f"# EDITION #{num} — production checklist",
        "",
        f"Digest: `digests/{path.stem}.md`  ·  Selected {len(items)} of "
        f"{data['stats']['detected']} detected  ·  Target publish: {publish:%A %d %B}",
        "",
        "## Day 11 — review",
        "- [x] Read the flag list",
        f"- [x] Selected {len(items)} developments",
        "- [ ] Checked the source health table (a thin list may be a broken feed)",
        "- [ ] Logged anything the system missed in the tuning log",
        "",
        "## Day 11–12 — research",
    ]
    for i, f in enumerate(items, 1):
        chk.append(f"- [ ] **{i}.** {f['title'][:75]}")
        chk.append(f"      - [ ] Read the primary source in full")
        chk.append(f"      - [ ] Found one independent account of it")
        chk.append(f"      - [ ] Answered all seven questions in `brief.md`")
    chk += [
        "",
        "## Day 12–13 — produce",
        "- [ ] Substack draft complete, 1,200–1,800 words total",
        "- [ ] Opener written last",
        "- [ ] One statistic / chart / map",
        "- [ ] One lighter item",
        "- [ ] Every claim linked to a primary source",
        f"- [ ] {len(items)} carousel scripts written",
        "- [ ] Carousels designed and exported to `assets/`",
        "- [ ] Alt text on every slide",
        "",
        "## Day 14 — publish and distribute",
        "- [ ] Substack published",
        "- [ ] Instagram carousel 1 posted",
        "- [ ] Story with link sticker",
        "- [ ] Sent to university society contacts",
        "- [ ] LinkedIn repost with the lede",
        "- [ ] Remaining carousels scheduled across the next fortnight",
        "",
        "## After",
        "- [ ] Note what performed and what did not",
        "- [ ] Any flag that turned out to be nothing → the tuning log",
        "",
    ]
    (ed / "checklist.md").write_text("\n".join(chk))

    (ed / "selection.json").write_text(json.dumps({
        "edition": num,
        "created": today.isoformat(),
        "digest": path.stem,
        "selected": picked,
        "detected": data["stats"]["detected"],
        "items": items,
    }, indent=1))

    print(f"\n  editions/{num}/ created — {len(items)} developments selected "
          f"from {data['stats']['detected']} detected\n")
    print(f"    brief.md                 Substack draft, seven questions per item")
    for i, f in enumerate(items, 1):
        print(f"    carousel-{i:02d}-….md        {f['title'][:52]}")
    print(f"    checklist.md             14-day production checklist")
    print(f"    assets/                  put exported graphics here")
    print(f"\n  Start with brief.md. Write the opener last.\n")
    return 0


def cmd_status(args) -> int:
    sidecars = sorted(DIGEST_DIR.glob("*.json"))
    eds = sorted(p for p in EDITIONS.glob("[0-9][0-9][0-9]") if p.is_dir())
    print()
    if not sidecars:
        print("  No digest yet. Run:  python3 collect.py")
        print()
        return 0
    last = load_flags(sidecars[-1])
    gen = dt.datetime.fromisoformat(last["generated"])
    age = (dt.datetime.now(dt.timezone.utc) - gen).days
    print(f"  Latest digest   {sidecars[-1].stem}  ({age} days ago)")
    print(f"  Flags waiting   {last['stats']['investigate']} to investigate, "
          f"{last['stats']['significant']} significant")
    print(f"  Editions built  {len(eds)}" + (f"  (latest #{eds[-1].name})" if eds else ""))
    day = min(age + 1, 14)
    stage = ("monitoring — the system is running, leave it alone" if day <= 10
             else "review the flags" if day == 11
             else "research and select" if day == 12
             else "write and design" if day == 13
             else "publish and distribute")
    print(f"  Cycle position  day {day} of 14 — {stage}")
    print()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Passerelle — human editorial layer.")
    ap.add_argument("--list", action="store_true", help="show the numbered flag list")
    ap.add_argument("--signals", default="", help="filter --list to these signals")
    ap.add_argument("--new-edition", type=int, help="edition number to scaffold")
    ap.add_argument("--select", default="", help="comma-separated flag numbers")
    ap.add_argument("--status", action="store_true", help="where you are in the cycle")
    ap.add_argument("--force", action="store_true", help="overwrite an existing edition")
    args = ap.parse_args()

    if args.status:
        return cmd_status(args)
    if args.new_edition is not None:
        if not args.select:
            print("--new-edition needs --select, e.g. --select 1,3,4", file=sys.stderr)
            return 1
        return cmd_new_edition(args)
    return cmd_list(args)


if __name__ == "__main__":
    raise SystemExit(main())
