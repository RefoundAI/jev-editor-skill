#!/usr/bin/env python3
"""
Deterministic checks for a markdown/MDX draft. No model calls.

Jev is unreliable at counting and exact matching, and these checks are free,
so anything countable lives here rather than in a Jev question: punctuation,
word lists, lengths, links, headings, metadata, and rhythm statistics.

Usage:
  python lint.py draft.md [--keyword "target phrase"] [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import statistics as st

# Words that add emphasis without meaning.
INTENSIFIERS = ["genuinely", "truly", "absolutely", "incredibly", "seriously", "really", "actually", "literally", "simply", "very"]

# Vocabulary that large-scale studies and editors' catalogs flag as overused by LLMs.
AI_VOCAB = [
    "delve", "tapestry", "testament", "underscore", "underscores", "pivotal", "crucial", "intricate", "intricacies",
    "landscape", "realm", "multifaceted", "nuanced", "foster", "garner", "showcase", "showcasing", "boasts",
    "leverage", "utilize", "seamless", "seamlessly", "robust", "cutting-edge", "game-changer", "game-changing",
    "revolutionize", "revolutionizing", "unlock", "unleash", "harness", "elevate", "empower", "streamline",
    "ever-evolving", "fast-paced", "navigate", "navigating", "embark", "vibrant", "meticulous", "comprehensive",
]

STOCK_PHRASES = [
    r"it'?s important to note", r"it'?s worth noting", r"in today'?s", r"in the world of", r"when it comes to",
    r"at the end of the day", r"in conclusion", r"in summary", r"to sum up", r"without further ado",
    r"let'?s explore", r"as we delve", r"in this (comprehensive )?(guide|article|post),? we", r"plays? a (crucial|key|vital|pivotal) role",
    r"stands? as a testament", r"a testament to", r"making waves", r"look no further", r"the world of", r"needless to say",
    r"in order to", r"not only .{3,60} but also", r"whether you'?re .{3,60} or ", r"worth (noting|sitting with|taking)",
]

HEDGES = ["arguably", "perhaps", "possibly", "potentially", "it seems", "one might", "could potentially", "somewhat", "to some extent"]


def strip_code(text: str, placeholder: str = "") -> tuple[str, list[str]]:
    """Remove fenced code blocks line by line. Handles nested fences (a 4-backtick
    block wrapping 3-backtick ones), which a regex can't. Returns the text without
    code and the language hint of each top-level block ("" when missing)."""
    out, langs, fence = [], [], None
    for line in text.split("\n"):
        m = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
        if fence is None and m:
            fence = m.group(1)
            langs.append(m.group(2).strip().split(" ")[0])
            if placeholder:
                out.append(placeholder)
        elif fence is not None:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not m.group(2).strip():
                fence = None
        else:
            out.append(line)
    return "\n".join(out), langs


def split_frontmatter(raw: str) -> tuple[dict, str]:
    m = re.match(r"\A---\n(.*?)\n---\n", raw, flags=re.S)
    if not m:
        return {}, raw
    fm_text, body = m.group(1), raw[m.end():]
    fm: dict = {}
    for key in ("title", "description", "heroImage", "pubDate", "updatedDate"):
        k = re.search(rf"^{key}:\s*(.*(?:\n[ \t]+.*)*)", fm_text, flags=re.M)
        if k:
            v = re.sub(r"^[>|][-+]?\s*", "", k.group(1).strip())
            fm[key] = re.sub(r"\s+", " ", v).strip().strip("'\"")
    return fm, body


def prose_only(body: str) -> str:
    t, _ = strip_code(body)
    t = re.sub(r"\{/\*.*?\*/\}|<!--.*?-->", "", t, flags=re.S)
    t = re.sub(r"^import .*$|^<[A-Z][^>]*/>\s*$|^\|.*$|^>.*$", "", t, flags=re.M)  # imports, components, tables, quotes
    return re.sub(r"`[^`]*`", "", t)


def count_terms(text: str, terms: list[str]) -> dict:
    low = text.lower()
    out = {t: len(re.findall(rf"\b{re.escape(t)}\b", low)) for t in terms}
    return {k: v for k, v in out.items() if v}


def lint(path: str, keyword: str | None = None) -> dict:
    raw = open(path, encoding="utf-8").read()
    fm, body = split_frontmatter(raw)
    prose = prose_only(body)
    words = prose.split()
    n_words = len(words)
    per_1k = lambda n: round(n / max(n_words, 1) * 1000, 1)

    sentences = [s for s in re.split(r"(?<=[.!?])\s+", re.sub(r"^#+ .*$", "", prose, flags=re.M)) if len(s.split()) >= 2]
    sent_lens = [len(s.split()) for s in sentences]
    paragraphs = [p for p in re.split(r"\n\s*\n", prose) if len(p.split()) >= 8 and not p.lstrip().startswith(("#", "-", "*", "1."))]
    para_lens = [len(p.split()) for p in paragraphs]

    no_code, code_blocks = strip_code(body)  # "# comment" lines inside code are not headings
    h1 = re.findall(r"^# (.+)$", no_code, flags=re.M)
    h2 = re.findall(r"^## (.+)$", no_code, flags=re.M)
    h3 = re.findall(r"^### (.+)$", no_code, flags=re.M)
    links = re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", body)
    internal = [l for l in links if l.startswith("/") or "sidbharath.com" in l]
    external = [l for l in links if l.startswith("http") and l not in internal]
    images = re.findall(r"!\[([^\]]*)\]\([^)]+\)", body)

    intens, vocab, hedges = count_terms(prose, INTENSIFIERS), count_terms(prose, AI_VOCAB), count_terms(prose, HEDGES)
    stock = {p: len(re.findall(p, prose, flags=re.I)) for p in STOCK_PHRASES}
    stock = {k: v for k, v in stock.items() if v}
    contrast = re.findall(r"\b(?:isn'?t|aren'?t|wasn'?t|not|doesn'?t|don'?t)\b[^.?!\n]{0,80}[,;.]\s+(?:it'?s|they'?re|it is|that'?s)\b", prose, flags=re.I)
    q_then_a = re.findall(r"(?:^|\. )(?:The|And the|So the)? ?[A-Z][\w' ]{0,30}\?\s+[A-Z][^.?!]{0,60}[.!]", prose)
    fragments_runs = len(re.findall(r"(?:(?:^|(?<=[.!?])\s)[A-Z][^.!?\n]{0,28}[.!?]){3,}", prose))

    title, desc = fm.get("title", ""), fm.get("description", "")
    first100 = " ".join(words[:100]).lower()
    kw = (keyword or "").lower()

    checks = []
    add = lambda area, name, ok, detail: checks.append({"area": area, "check": name, "pass": bool(ok), "detail": detail})

    # --- AI tells (countable)
    add("ai_tells", "em_dashes", raw.count("—") == 0, f"{raw.count(chr(0x2014))} found")
    add("ai_tells", "intensifiers_per_1k", per_1k(sum(intens.values())) <= 3, f"{per_1k(sum(intens.values()))}/1k words: {intens}")
    add("ai_tells", "ai_vocabulary_per_1k", per_1k(sum(vocab.values())) <= 2, f"{per_1k(sum(vocab.values()))}/1k words: {vocab}")
    add("ai_tells", "stock_phrases", not stock, f"{stock} (check whether each is your own prose or a quoted example)")
    add("ai_tells", "hedges_per_1k", per_1k(sum(hedges.values())) <= 1.5, f"{per_1k(sum(hedges.values()))}/1k words: {hedges}")
    add("ai_tells", "contrast_scaffold_regex", len(contrast) <= max(1, n_words // 1500), f"{len(contrast)} candidate(s): {[c[:70] for c in contrast[:6]]}")
    add("ai_tells", "question_then_answer", len(q_then_a) <= 2, f"{len(q_then_a)} found")
    add("ai_tells", "staccato_fragment_runs", fragments_runs <= 2, f"{fragments_runs} run(s) of 3+ very short sentences")
    if len(sent_lens) > 20:
        cv = round(st.pstdev(sent_lens) / st.mean(sent_lens), 2)
        add("ai_tells", "sentence_length_variation", cv >= 0.55, f"coefficient of variation {cv} (mean {st.mean(sent_lens):.0f} words); low = monotone rhythm")
    if len(para_lens) > 8:
        cvp = round(st.pstdev(para_lens) / st.mean(para_lens), 2)
        add("ai_tells", "paragraph_length_variation", cvp >= 0.45, f"coefficient of variation {cvp} (mean {st.mean(para_lens):.0f} words)")
    bold_leads = len(re.findall(r"^\s*[-*] \*\*[^*]+\*\*[:.]", body, flags=re.M))
    add("ai_tells", "bulleted_bold_lead_ins", bold_leads <= 10, f"{bold_leads} bullets start with a bolded label")

    # --- editorial (countable)
    add("editorial", "word_count", n_words >= 1500, f"{n_words} words of prose")
    add("editorial", "long_paragraphs", sum(l > 120 for l in para_lens) == 0, f"{sum(l > 120 for l in para_lens)} paragraph(s) over 120 words")
    add("editorial", "section_length_balance", True, f"{len(h2)} H2 sections, {len(h3)} H3")
    add("editorial", "code_blocks_have_language", all(code_blocks) if code_blocks else True, f"{sum(1 for c in code_blocks if not c)} of {len(code_blocks)} fenced blocks missing a language hint")
    add("editorial", "has_table_or_list", bool(re.search(r"^\|.*\|$", body, flags=re.M)) or bool(re.search(r"^\s*[-*] ", body, flags=re.M)), "comparison table or list present")
    add("editorial", "todo_markers", not re.search(r"TODO[(:]|TKTK|\bTK\b|[Ll]orem ipsum", raw), f"{len(re.findall(r'TODO[(:]|TKTK', raw))} TODO marker(s) left in the draft")

    # --- SEO (countable)
    add("seo", "title_length", 30 <= len(title) <= 60, f"{len(title)} chars: {title!r}")
    add("seo", "meta_description_length", 110 <= len(desc) <= 160, f"{len(desc)} chars")
    add("seo", "single_h1", len(h1) <= 1, f"{len(h1)} H1 in body (the layout renders the title as H1)")
    add("seo", "heading_hierarchy", not re.search(r"^## .*\n(?:(?!^## ).*\n)*?^#### ", body, flags=re.M) or bool(h3), "no skipped heading levels")
    add("seo", "internal_links", len(internal) >= 3, f"{len(internal)} internal link(s)")
    add("seo", "external_links", len(external) >= 3, f"{len(external)} outbound link(s) to sources")
    add("seo", "images_have_alt", all(a.strip() for a in images) if images else True, f"{len(images)} image(s), {sum(1 for a in images if not a.strip())} missing alt text")
    add("seo", "hero_image", bool(fm.get("heroImage")), "heroImage set in frontmatter" if fm.get("heroImage") else "no heroImage")
    if kw:
        add("seo", "keyword_in_title", kw in title.lower(), f"{keyword!r} in title")
        add("seo", "keyword_in_description", kw in desc.lower(), f"{keyword!r} in meta description")
        add("seo", "keyword_in_first_100_words", kw in first100, f"{keyword!r} in first 100 words")
        add("seo", "keyword_in_a_heading", any(kw in h.lower() for h in h2 + h3), f"{keyword!r} in an H2/H3")
    question_h = [h for h in h2 + h3 if h.strip().endswith("?") or re.match(r"(what (is|are)|how (to|do|does)|why|when to|should|can|is|does)\b", h.strip(), flags=re.I)]
    add("seo", "question_style_headings", len(question_h) >= 2, f"{len(question_h)} of {len(h2) + len(h3)} headings phrased as a question a reader would search or ask an AI")

    return {"file": path, "words": n_words, "checks": checks,
            "failed": [f"{c['area']}.{c['check']}" for c in checks if not c["pass"]]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("file"); ap.add_argument("--keyword"); ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = lint(a.file, a.keyword)
    if a.json:
        print(json.dumps(r, indent=2))
    else:
        print(f"LINT {r['file']} ({r['words']} words): {len(r['failed'])} of {len(r['checks'])} checks failed")
        for c in r["checks"]:
            print(f"  [{'ok' if c['pass'] else 'FAIL'}] {c['area']:9s} {c['check']:28s} {c['detail'][:150]}")
