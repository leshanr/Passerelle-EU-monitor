# Worked example — one development, end to end

One item, followed from the moment the system flagged it to the moment it was
published in two formats. This is the whole project in one file.

The item below comes from `tests/demo.py` fixture data, so it is illustrative
rather than a real development — but every stage is the real process, and the
first real edition replaces it.

---

## 1. What the system produced

The scheduled run fetched fifteen feeds, discarded everything already in
`state/seen.json`, and wrote `digests/2026-08-27.md`. Twelve developments cleared
the noise filter. Seven reached the top tier. This was one of them:

```
[ 3] Commission proposes first-ever EU rules on age verification for social media
     Tech and online life · European Commission — press corner · 2026-08-21 · score 82
     why: Genuinely new, Unusual or unexpected, Likely to generate debate,
          Consequential, Relevant to young Europeans, Technologically significant
```

**Why it scored 82.** Beat: `tech-and-online-life`, on *age verification*
(4×2 for a title match), *very large online platform*, *social media*, *TikTok*.
Signals: `new` on *proposes*/*unveiled*; `unusual` on *first-ever*; `contested`
on *warned*/*campaigners*; `consequential` on *mandatory*/*binding*/*fines*;
`youth` on *social media*/*TikTok*/*Instagram*; `tech` on *platform*/*digital*.

Six independent reasons. That breadth is what put it above items with bigger
single-topic scores — which is the behaviour the capped scoring was built for.

**What the machine did not do.** It did not decide this was worth publishing. It
said *this looks potentially significant, and here are six reasons why*. Three
items that fortnight had higher scores and two of them were cut.

---

## 2. The human decision

```bash
python3 review.py --list
python3 review.py --new-edition 1 --select 1,2,4,5,6
```

**Why it was selected.** Age verification is the shortest distance in the whole
digest between a Brussels regulation and something on a reader's phone. Every
person in the target audience has an account on a platform this would cover.

**What was cut, and why.** The sanctions package scored 76 and was cut: it was
the fourth sanctions package of the year, nothing structural had changed, and
"more sanctions on Russia" is not news to anyone who reads anything. A State aid
approval scored 35 and was cut: procedurally routine, no consequence a reader
would feel.

That is the editorial layer. The score got the item onto the list. Judgement got
it into the edition.

---

## 3. The research

`review.py` wrote the seven questions into `editions/001/brief.md` with the
source link attached. Answering them is the work — roughly ninety minutes per
lead item.

- **Read the primary source in full.** The proposal, not the press release.
- **Find one independent account.** If nobody else has covered it, you have
  either a scoop or a misreading, and the second is more likely.
- **Establish the stage.** Proposal, provisional agreement, adopted, in force —
  these are four different stories and readers cannot tell them apart unless you
  do it for them.
- **Find the number.** One statistic worth putting on a slide.

---

## 4. The Substack paragraph

What went in, after research, at about 180 words:

> **The EU wants to check your age before you can open TikTok**
>
> The Commission has proposed the first EU-wide rules requiring large platforms
> to verify how old their users are. If it passes in this form, platforms with
> more than 45 million users in the EU would have to run an age check at sign-up,
> and face fines of up to 6% of global turnover for getting it wrong.
>
> **What changed:** platforms currently self-certify. Under the proposal they
> would have to prove it.
>
> **Why it exists:** four member states were about to legislate separately, and
> a single EU rule is easier for the platforms and better for the Commission
> than four incompatible national ones.
>
> **Why you should care:** every workable age-verification system involves
> handing a platform either an ID document or a face scan. Digital rights groups
> call it surveillance infrastructure built for a child-protection reason. That
> tension is the whole fight, and it will be settled in the next eighteen months
> on terms set now.
>
> **Next:** Parliament first reading, expected Q1 2027.

Note what that does: names the stage, gives the before and after, gives the
motive, and puts the reader's own account at the centre of the "why care".
No institutional nouns as subjects.

---

## 5. The Instagram carousel

Same research, second format. `review.py` wrote the skeleton; the visual device
chosen was a **before/after comparison** because "self-certify → prove it" is
the whole story and it fits on one slide.

| Slide | Content | Visual |
|---|---|---|
| 1 | THE EU WANTS TO CHECK YOUR AGE. Here's what actually happened. | Type only, signal blue on ink |
| 2 | WHAT HAPPENED — Commission proposes EU-wide age checks for big platforms | Screenshot of the proposal header |
| 3 | WHAT CHANGED — Now: platforms self-certify → Proposed: platforms must prove it | Before/after split |
| 4 | WHY DID THE EU DO THIS — Four countries were about to write four different laws | Map, four countries highlighted |
| 5 | WHO DOES IT AFFECT — Any platform over 45m EU users. That is all of them. | Logo grid |
| 6 | WHY SHOULD YOU CARE — Every version of this means showing ID or your face to a platform | Single stat, full bleed |
| 7 | WHAT HAPPENS NEXT — Parliament first reading, Q1 2027 | Timeline + Substack CTA |

The carousel is not a summary of the Substack piece. It is the same research cut
for a different attention span. Slide 6 is the one that gets screenshotted, so
it gets the most work.

---

## 6. Distribution

Substack published. Carousel posted. Story with link sticker. Sent to the
university society contacts in `AUDIENCE-AND-DISTRIBUTION.md`. LinkedIn repost
with the lede and a link.

---

## 7. Back into the log

Two things went into `TUNING-LOG.md` from this cycle:

- The sanctions item reaching the top tier on a routine package suggests the
  `war-and-security` beat needs a "nth package" discount, or the `decided`
  signal is too generous on routine adoptions.
- Nothing in the digest covered the Parliament's committee stage on this file,
  because the committee feed was 72 days stale. Redundancy worked — the
  Commission feed carried it — but that is luck, not design.

That is the loop. The system flags, the human judges, and what the human learns
goes back into the system.
