# Editions

One folder per published edition, written by `review.py` - never by hand, and never by the
collector.

```
python3 review.py --list                        # numbered flag list from the newest digest
python3 review.py --new-edition 1 --select 2,5  # scaffold edition 001 from flags 2 and 5
```

That creates `editions/001/` containing:

| file | what it is |
|---|---|
| `brief.md` | the Substack draft, one section per selected development |
| `carousel-NN-*.md` | one Instagram carousel script per development |
| `checklist.md` | the pre-publication checks |
| `selection.json` | what was selected, and what was dropped |

Each is pre-filled with the source link and the editorial questions. Nothing in a scaffold
is publishable as written - it is a worksheet, not a draft.

This folder is empty until the first edition is scaffolded. A demo edition built from test
fixtures used to live here; it was removed on 31 Aug 2026 because it read like real
reporting when it was not. It is still in git history if you want to see the shape of one.
