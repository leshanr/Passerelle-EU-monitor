# Brand templates

## `carousel.html` — the Instagram slide builder

Edit the `SLIDES` array at the top, open the file in a browser, and you have the
carousel. Seven slide types cover everything the format needs:

| Type | Use it for |
|---|---|
| `hook` | Slide 1. Big headline, the monitoring trace, one line of strapline. |
| `text` | Label + headline + paragraph. The workhorse. |
| `compare` | Before → after. Use this constantly — "what changed" is the question most EU coverage skips. |
| `stat` | One enormous number. This is the slide people screenshot. |
| `list` | Numbered items, for "60 seconds" posts. |
| `timeline` | Dated events, last one highlighted, plus the Substack call to action. |

Export at full resolution:

```bash
npm i playwright          # once
node export.js ../../editions/007/assets
```

Or just screenshot each slide in the browser at 1080 × 1350.

## What to change and what not to

**Change freely:** the copy, the slide order, the number of slides (six is fine,
nine is a Substack piece pretending to be a carousel).

**Do not change:** the signal rule at the bottom, the slide counter, the source
line, the type scale. Those four things are what make a slide recognisable as
yours at thumbnail size, and consistency is worth more than variety.

## Fonts

The templates ask for **Space Grotesk** (display), **Inter** (body) and
**JetBrains Mono** (labels), and fall back to system faces if those are not
installed. All three are free — install them locally, or add them to a Canva
brand kit — before exporting anything for publication.

## `substack-header.html`

Export at 1200 × 300 for the Substack publication header, and 1200 × 630 for the
social preview image.
