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

`001/` was produced by the fixture demo run. Delete it when you build a real one.
