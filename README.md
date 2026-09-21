# Jev Editor

An editorial gate for blog posts and articles, packaged as an agent skill. It scores a markdown or MDX draft on four areas and tells your coding agent what to fix:

- **AI tells**: negative parallelism ("it's not X, it's Y"), empty intensifiers, mic-drop closers, signposting, and other patterns that make writing read as machine-generated
- **Voice**: how closely each section matches samples of your own published writing
- **Editorial**: the hook, the promise, the ending, dangling references, leftover TODOs
- **SEO and AI search**: title, description, links, headings, a front-loaded answer, a quotable definition

It uses [TypeSafe's Jev](https://typesafe.ai) for fast, cheap, typed judgments. A full pass on a 4,500-word post is about 24 requests, takes about a second, and costs around a quarter of a cent.

The background, the testing, and the results are in [Jev: The Complete Guide to TypeSafe's System One Model](https://sidbharath.com/blog/the-complete-guide-to-jev/).

## How it works

Three layers, each doing only what it proved it can do.

| Layer | Does |
| --- | --- |
| `scripts/lint.py` (plain code) | Anything countable: em-dashes, word lists, sentence rhythm, title length, links, headings, alt text. Jev is unreliable at counting, and code is exact and free. |
| Jev (`scripts/jev_editor.py`) | 21 narrow judgments on small inputs: the opening, each section, the title and description, the closing. Plus a voice match against your own writing. |
| Your coding agent | The judgments Jev failed in testing: fact-checking, whether the intro's promises are paid off, replicability, limitations. |

54 candidate questions were tested against published posts and raw AI first drafts. 21 survived. The evidence for every question, including the rejected ones, is recorded in [`scripts/questions.py`](skills/jev-editor/scripts/questions.py).

## Install

You need Python 3.10+ and a TypeSafe API key from [typesafe.ai](https://typesafe.ai).

```bash
git clone https://github.com/RefoundAI/jev-editor-skill.git

# Claude Code, available in every project:
mkdir -p ~/.claude/skills
cp -R jev-editor-skill/skills/jev-editor ~/.claude/skills/

# or for one project only:
mkdir -p .claude/skills
cp -R jev-editor-skill/skills/jev-editor .claude/skills/

pip install typesafe-sdk
export TYPESAFE_API_KEY=your-key-here
```

Other agents that read the [Agent Skills](https://agentskills.io) format work the same way. Copy `skills/jev-editor` into that agent's skills folder.

Keep your key in an environment variable. Don't write it into a file in your repo.

## Use it with your agent

Start a new session so the skill loads, then ask in plain language:

> Review drafts/my-post.md with the jev-editor skill. My published posts are in content/blog, use three of them as voice samples.

The agent runs the gate, reads the results, fixes what's flagged, and runs it again. It stops after three passes and tells you what is still open. It is instructed never to invent first-hand experience or numbers, so expect it to ask you questions.

## Use it from the command line

```bash
cd skills/jev-editor/scripts

# full report
python jev_editor.py path/to/draft.md \
  --keyword "your target phrase" \
  --voice-samples path/to/post1.md path/to/post2.md path/to/post3.md

# machine-readable
python jev_editor.py path/to/draft.md --json

# only the free deterministic checks, no API key needed
python lint.py path/to/draft.md --keyword "your target phrase"
```

A draft passes when tells, editorial, and SEO each score 70 or higher, voice scores 60 or higher, and there are no deal-breakers (a leftover TODO, or a reference to a part of the post that doesn't exist).

## Calibrate it to your own writing

The thresholds ship from one author's posts. Yours will differ, and that's the point: if your published writing uses a pattern on purpose, the tool should learn to leave it alone.

```bash
python calibrate.py --good my-best-posts/*.md --bad raw-ai-drafts/*.md
```

This runs every candidate question over both sets and shows which ones separate them. Update the thresholds in `VALIDATED` inside `questions.py` with your numbers. Do the same before trusting any question you add. A question that sounds right and does not separate is worse than no question.

## What it cannot do

- **Fact-check.** Jev has no idea whether a claim is true. Your agent and you do that.
- **Tell real experience from invented.** In testing, raw AI drafts scored higher on "includes first-hand experience" than real posts did, because they write "I tested this" freely. That question was removed.
- **Judge a whole long post.** On a 9,000-word guide, whole-post questions stopped responding even when entire sections were deleted. That is why almost everything here runs on small inputs.
- **Point at a sentence.** You get the section. Finding the sentence is the agent's job.
- **Tell use from mention.** If your post quotes a bad pattern in order to discuss it, the quote gets flagged.

## License

MIT. Built by [Sid Bharath](https://sidbharath.com) at [Refound AI](https://refoundai.com).
