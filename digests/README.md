# digests/

One digest per run, written by the scheduled workflow. Each has a companion
`.json` sidecar that `review.py` reads — the markdown is for you, the JSON is for
the tooling, and neither has to compromise for the other.

**The files currently here came from `tests/demo.py`**, which runs the whole
pipeline against the fixture feeds in `tests/fixtures/` with no network. Their
sources are labelled `(demo)`. They exist so that anyone landing on this repo can
see what the output actually looks like before the first real run.

Delete them once real digests start arriving — or leave them, and let the source
labels do the work.
