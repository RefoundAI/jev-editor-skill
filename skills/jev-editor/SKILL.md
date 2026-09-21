---
name: jev-editor
description: Editorial gate for blog posts and articles. Scores a markdown/MDX draft on four areas (AI-writing tells, match to the author's own voice, editorial quality, SEO and AI-search readiness) using deterministic lint plus TypeSafe's Jev for fast typed judgments, then hands the reasoning-heavy checks to you. Use when asked to review, edit, tighten, or de-slop a draft, check it against the author's voice, or decide whether a post is ready to publish.
---

# Jev Editor

Three layers. Each does only what it proved it can do.

| Layer | Does | Why |
| --- | --- | --- |
| `scripts/lint.py` (code) | Anything countable: em-dashes, intensifiers, AI vocabulary, stock phrases, sentence and paragraph rhythm, title and description length, links, headings, alt text, TODO markers | Jev is unreliable at counting. Code is exact and free. |
| Jev (`scripts/jev_editor.py`) | Narrow typed judgments on small states: the opening, each section, the title and description, the closing. Voice match against the author's own writing. | Fast and cheap enough to ask about 12 questions per section, every pass. Only questions that passed calibration are used. |
| You, the agent | Fact-checking, promise and payoff, replicability, limitations, internal references, repetition | Jev failed calibration on every one of these for long posts. They need a reader. |

## Setup (once)

```bash
pip install typesafe-sdk
export TYPESAFE_API_KEY=...   # from typesafe.ai. Never write the key into a file in the repo.
```

## The loop

1. Run the gate. Point `--voice-samples` at three or more finished pieces by the same author (files or a folder). Without samples, voice is not scored.
   ```bash
   python scripts/jev_editor.py draft.md --keyword "target phrase" \
     --voice-samples posts/a.md posts/b.md posts/c.md --json
   ```
2. Read `verdict`, `area_scores`, `deal_breakers`, and the failing entries in `checks`. A draft passes when tells, editorial, and SEO are each 70 or higher, voice is 60 or higher, and there are no deal-breakers.
3. Fix in this order:
   1. **Deal-breakers.** TODO markers left in the draft. References to parts of the post that do not exist.
   2. **Your own review list** (`agent_review` in the output). Do these by reading the draft. Fact-check first: nothing else in this skill can.
   3. **AI tells.** Each failing `sections.<tell>` check names the sections. Jev gives you the section, not the sentence, so find the sentences yourself. `lint` checks give exact counts and matches.
   4. **Voice.** For each off-voice section, read two of the author's samples, then rewrite the section the way they would say it. Do not paste in their catchphrases.
   5. **Editorial and SEO.** Work through the failing checks.
4. Run it again. Stop after 3 passes whether or not it passes, and tell the author what is still flagged. Nothing guarantees this loop converges.

## Rules for editing

- Never invent first-hand experience, numbers, or results. If the draft lacks the author's own experience, ask them what happened when they used the thing, and write that in.
- A flagged tell inside a quotation or an example of bad writing is not a problem. Jev cannot tell use from mention. Check before "fixing".
- The author's own habits beat the generic list. If their published writing uses a pattern on purpose, leave it. Thresholds are set from the author's own posts for this reason (see Calibration).
- `primary_blocker` is advisory. On posts over about 6,000 words it is close to noise.
- `whole.dangling_reference` is a deal-breaker, and it has a known false positive: a post that quotes or discusses a broken reference. When it fires, list every "earlier", "above", "below", and "next section" in the draft and confirm each target exists. Only then re-run with `--references-verified`.
- Blockquotes and tables are left out of the per-section tell and voice checks. They hold quoted or example text, which isn't the author's prose.
- Link-list sections (Sources, References, Further reading) are skipped. They are never scored and never treated as the closing.

## What the numbers mean

- Every Jev value is normalized to 0 to 1. For a Noul it is the probability the statement is true, and 0.5 means Jev does not know. For a Score it is the rubric position divided by the top level.
- A check has a polarity. "high is bad" checks fail above their threshold. "high is good" checks fail below it.
- A section-level tell fails the post when it is over threshold in more than a third of sections.
- `voice` is the percent of sections that match the reference voice.
- Area scores are the percent of checks passing in that area. They are a to-do list with a number on it, not a grade.

## Calibration: why these questions and not others

Every Jev question had to earn its place one of two ways:

- **Separation.** It scores known-good writing (4 published posts) differently from known-bad writing (5 raw AI first drafts).
- **Ablation.** Break a good post on exactly one dimension (swap in a clickbait title, replace the ending with an "In conclusion" recap) and the score moves the right way.

54 questions were tried. 21 are used, 3 are shown as advisory, and the other 30 were rejected. `scripts/questions.py` records the evidence for each one, including the rejections. The ones worth knowing about:

| Finding | Evidence |
| --- | --- |
| Structural AI tells separate well | `empty_intensifiers` +0.56, `negative_parallelism` +0.44, `question_then_answer` +0.39, `signposting` +0.37 |
| "Has first-hand experience" is inverted | Published posts 0.60, raw AI drafts 0.81. AI drafts write "I tested this" freely. Jev judges the claim, not whether it happened. |
| "Uses specific figures" is inverted | Published 0.48, AI drafts 0.75. Same reason: confident invented numbers. |
| Whole-post questions go blind on long posts | "Names a limitation" stayed at 0.98 after every limitation paragraph was deleted from a 9,000-word post. "Promise is paid off" did not move when six sections were deleted. |
| Small states are sharp | Clickbait title: `honest_title` 0.77 to 0.14. Summary ending: `gives_next_action` 0.89 to 0.03. |
| Voice needs reference samples | A generic "has a voice" score gave a company launch blog 0.90. With five excerpts of the author's writing in the state, held-out posts by that author scored 0.63 to 0.82 and everyone else 0.00 to 0.12. |
| A "needs fact check" option never loses | It fired on 3 of 4 published posts. Read literally, every factual article "contains a claim that needs verification". |

**Re-calibrate for your own writing.** The thresholds in `questions.py` come from one author's posts. Run this with your own good and bad sets, then update `VALIDATED`:

```bash
python scripts/calibrate.py --good my-best-posts/*.md --bad raw-ai-drafts/*.md
```

Do the same before trusting any question you add. A question that sounds right and does not separate is worse than no question.

## Cost and speed

About two requests per section plus three. A 4,500-word post is roughly 25 requests running four at a time. One request with ten questions returned in about 200 ms. Input is priced per token and output is free, so a full pass costs well under a cent.

See `references/criteria.md` for the full criteria list with sources.
