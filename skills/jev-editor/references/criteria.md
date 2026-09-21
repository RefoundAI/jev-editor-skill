# Criteria and sources

What the editor checks, where each check came from, and which layer runs it. Research done September 2026.

## AI-writing tells

The field has moved. Vocabulary tells ("delve", "tapestry") are fading and differ by model, and only about 45% of tells overlap between consecutive GPT versions. Structural tells persist across every model family. Em-dashes and curly quotes have high false-positive rates and are fading, so they count for little on their own.

| Tell | Layer | Notes |
| --- | --- | --- |
| Negative parallelism ("it's not X, it's Y", "not just X but Y") | Jev + lint regex | Highest measured ratios in 2026 models (105 to 576x human rate). Humans use it for real misconceptions, so allow it about once per post. |
| Empty intensifiers and "magic adverbs" ("genuinely", "quietly", "fundamentally") | Jev + lint count | Best separator in calibration. |
| Rhetorical question, immediately answered ("The result? ...") | Jev + lint regex | A LinkedIn drama register, unusual in technical writing. |
| Signposting and throat-clearing ("Let's break this down") | Jev + lint phrases | Fine when substance follows right away. |
| Superficial analysis (commentary on what a fact "shows" that adds no fact) | Jev | |
| Rule of three | Jev | Noisy alone, strong alongside the others. |
| Significance inflation ("plays a crucial role", "stands as a testament") | Jev + lint phrases | |
| Mic-drop closers (quotable one-line paragraph endings with no information) | Jev | One is style. One per section is mechanical. |
| Trailing participle analysis (", highlighting the importance of...") | Jev | 5.3x human rate in the PNAS study. |
| Cliche opener | Jev | |
| AI vocabulary density, stock phrases, hedging stacks | lint | Score density, never ban single words. |
| Low burstiness (uniform sentence and paragraph length) | lint | Use only as part of a composite. GPTZero dropped it as a core signal. |
| Bulleted lists with bolded lead-ins | lint | Markdown-training residue. Normal in reference docs. |
| Importance flagging ("it's worth noting"), no-tradeoff phrases ("without sacrificing") | lint phrases | Current-generation tells. |

Tried with Jev and rejected for not separating good writing from AI drafts: generic claims, over-balanced framing, invented labels, vague attribution, forced analogy, staccato fragments.

Sources: Wikipedia, "Signs of AI writing" (en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing); tropes.fyi/directory; Graphite, "AI Tells" (graphite.io/five-percent/research/ai-tells); The Economist, "How to spot AI writing" (30 Jul 2026); Reinhart et al., PNAS 2025 (pmc.ncbi.nlm.nih.gov/articles/PMC11874169); Kobak et al., Science Advances 2025 (arxiv.org/abs/2406.07016); Russell et al., ACL 2025 (aclanthology.org/2025.acl-long.267); "The Last Fingerprint" (arxiv.org/html/2603.27006v1); Shreya Shankar (sh-reya.com/blog/ai-writing); Charlie Guo, "Field Guide to AI Slop" (ignorance.ai); Hollis Robbins (Substack).

## Editorial

| Check | Layer |
| --- | --- |
| Opening: specific hook, promise stated, no cliche | Jev (opening state) |
| Closing: gives a next action, is not only a recap, lands with energy | Jev (closing state) |
| Refers to parts of itself that do not exist | Jev on posts under 6,000 words, agent always |
| Paragraphs over 120 words, code fences missing a language, TODO markers, word count | lint |
| At least one call to action, no stretch over 3,000 words without one, and one within the last tenth of the post | lint |
| Promise and payoff, single controlling idea, repetition across sections | agent |
| Claims evidenced, results shown, first-hand experience is real | agent |
| Replicable: prerequisites, exact commands, expected output, one likely error and its fix | agent |
| Names a limitation or a case where the approach is a poor fit | agent |
| Facts are correct | agent |

Sources: Google technical writing courses and developer style guide (developers.google.com/tech-writing, developers.google.com/style); Diataxis on tutorials (diataxis.fr/tutorials); Write the Docs principles; Nielsen Norman Group on how users read on the web and the inverted pyramid (79% of users scan; concise text measured +58% usability, scannable layout +47%, objective language +27%); Poynter on the nut graf; UNC Writing Center on transitions.

## SEO and AI search

| Check | Layer | Notes |
| --- | --- | --- |
| Title 30 to 60 characters | lint | Zyppy: 51 to 60 characters was least rewritten, over 70 rewritten 99.9% of the time. A heuristic, not a Google rule. |
| Title is honest and specific; description gives a reason to click | Jev | Ablation-validated. |
| Meta description 110 to 160 characters | lint | Display convention only. Google often writes its own snippet. |
| Opening names the topic and states the answer in the first 100 words | Jev | 44% of ChatGPT citations come from the first 30% of a page. |
| Central concept defined in one quotable sentence | Jev | Definitive phrasing was about 2x more likely to be cited. |
| Internal links (3+), outbound links to sources (3+) | lint | In the GEO paper, citing sources gave the largest visibility gain for lower-ranked pages. |
| Link text says where the link goes: no "click here", no bare URLs | lint | Also an accessibility basic |
| Internal links point at posts that exist | lint, needs `--content-dir` | |
| Images have alt text, hero image set, single H1, no skipped heading levels | lint | Heading order is an accessibility and parsing check, not a ranking factor. |
| Keyword in title, description, first 100 words, and a heading | lint, needs `--keyword` | |
| Some headings phrased as questions | lint | Single observational study. Low weight. |
| Search intent match, information gain versus what ranks, fan-out coverage | not checked | Need SERP and competitor data this skill does not have. |
| Visible published and updated dates, Article schema with author | not checked | Lives in the site template, not the draft. |

Deliberately excluded because the advice is outdated or unsupported: FAQ rich results (ended May 2026), HowTo rich results (removed), llms.txt (no measured effect on citations across 300k domains, and Google says it neither helps nor harms), keyword density (the only GEO tactic that scored below baseline), word-count targets, and rewriting or "chunking" content for AI (Google: not needed).

Sources: Google Search Central (creating helpful content, SEO starter guide, AI features, AI optimization guide updated 2026-07-10, title links, snippets, publication dates, article structured data); Aggarwal et al., "GEO: Generative Engine Optimization" (arxiv.org/abs/2311.09735); 2026 GEO survey preprint (arxiv.org/html/2607.14035v1); Search Engine Land ChatGPT citation study; Search Engine Journal on AI Overview citations, FAQ rich results, and llms.txt; Ahrefs meta description study; Zyppy title rewrite study.
