# editions/

**Nothing in this folder is ever written by the automated run.** That is the
point, and the file layout enforces it.

An edition is created by you, from flags you selected:

```bash
python3 review.py --list
python3 review.py --new-edition 7 --select 1,3,4,9,12
```

Each edition folder holds:

| File | What it is |
|---|---|
| `brief.md` | The Substack draft. Every selected development already carries its source link, the reasons it was flagged, and the seven editorial questions as empty headings. |
| `carousel-NN-….md` | One seven-slide Instagram script per development. |
| `checklist.md` | The 14-day production checklist, pre-filled with your selections. |
| `selection.json` | What you chose out of what — so the ratio stays recoverable. |
| `assets/` | Exported graphics. Ignored by git; the real files live in `../workspace/`. |

`000-worked-example/` was produced by the fixture demo run. **Everything in it is
invented** — the Court of Justice rent-cap ruling, the UK–EU youth mobility
agreement and the 12 percent Erasmus+ cut did not happen, and their links point
at `example.eu`. It is kept because it is the clearest demonstration of the
format, and it is numbered `000` so that the first real edition can take `001`
and the archive never opens on fabricated rulings.
