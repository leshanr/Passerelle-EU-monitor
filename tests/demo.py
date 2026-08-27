#!/usr/bin/env python3
"""
Run the whole pipeline against the offline fixtures.

Useful for two things: seeing what a digest actually looks like without waiting
for a scheduled run, and having something concrete in the repo for anyone who
lands on it. Writes a real digest into digests/ using fixture data only — no
network is touched.

    python3 tests/demo.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
FIX = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(ROOT))

import collect  # noqa: E402

FIXTURE_SOURCES = [
    {"id": "demo-ec", "name": "European Commission — press corner (demo)",
     "url": "fixture:sample_rss.xml", "tier": 1},
    {"id": "demo-govuk", "name": "gov.uk — news and communications (demo)",
     "url": "fixture:sample_atom.xml", "tier": 2},
    {"id": "demo-eurlex", "name": "EUR-Lex — Commission proposals (demo)",
     "url": "fixture:sample_eurlex.xml", "tier": 1, "date_fallback": "channel"},
    {"id": "demo-routine", "name": "Council of the EU — press releases (demo)",
     "url": "fixture:sample_routine.xml", "tier": 1},
    {"id": "demo-dead", "name": "European Parliament — press releases (demo, stale)",
     "url": "fixture:sample_stale.xml", "tier": 1},
    {"id": "demo-broken", "name": "A feed that has quietly moved (demo, broken)",
     "url": "fixture:broken.html", "tier": 2},
]


def fake_fetch(url: str, attempts: int = 3) -> bytes:
    name = url.split(":", 1)[1]
    path = FIX / name
    if not path.exists():
        raise RuntimeError("HTTP Error 404: Not Found")
    return path.read_bytes()


def main() -> int:
    # A stale feed and a broken one, generated so the demo shows the source
    # health table doing its job.
    stale = FIX / "sample_stale.xml"
    if not stale.exists():
        old = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=74)
        stale.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>'
            "<title>Stale institutional feed</title>"
            "<item><title>Parliament adopts resolution on enlargement</title>"
            "<link>https://example.eu/stale</link>"
            "<description>Adopted text.</description>"
            f"<pubDate>{old.strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>"
            "</item></channel></rss>\n"
        )
    broken = FIX / "broken.html"
    if not broken.exists():
        broken.write_text("<!DOCTYPE html><html><body>This feed has moved.</body></html>\n")

    sources_json = json.dumps({"sources": FIXTURE_SOURCES})
    real_read = Path.read_text

    def patched_read(self, *a, **k):
        if self.name == "sources.json":
            return sources_json
        return real_read(self, *a, **k)

    print("Running the pipeline against fixtures — no network.\n")
    with mock.patch.object(collect, "fetch", fake_fetch), \
         mock.patch.object(Path, "read_text", patched_read):
        sys.argv = ["collect.py", "--days", "14", "--no-state"]
        rc = collect.main()

    print("\nNow try:")
    print("    python3 review.py --list")
    print("    python3 review.py --new-edition 1 --select 1,2,3\n")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
