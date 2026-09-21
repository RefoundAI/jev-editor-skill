#!/usr/bin/env python3
"""
Jev Editor: an editorial gate for markdown/MDX drafts.

Three layers, each doing what it is good at:
  1. lint.py      deterministic code. Anything countable: punctuation, word lists,
                  lengths, links, headings, metadata, rhythm. Free and exact.
  2. Jev          fast typed judgments on SMALL states (the opening, one section,
                  the title, the closing). Only questions that passed calibration.
  3. the agent    the reasoning model running this skill. Gets the whole-post
                  judgments Jev failed calibration on (see AGENT_REVIEW below).

Usage:
  export TYPESAFE_API_KEY=...
  python jev_editor.py draft.md --voice-samples post1.md post2.md post3.md
  python jev_editor.py draft.md --keyword "claude code" --json

Requires: pip install typesafe-sdk
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics as st
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

from typesafe_sdk import TypeSafeClient

from lint import lint, split_frontmatter
from questions import ADVISORY, BANK, PRIMARY_BLOCKER, VALIDATED, VOICE_MATCH, active

PASS_BAR = 70            # each area needs this percent of its checks passing
VOICE_AREA_BAR = 60      # percent of sections that must match the reference voice. A strong published post scored 69 to 72; a raw draft 30
LONG_POST_WORDS = 6000   # above this, whole-post Jev answers were not sensitive in testing, so they inform but never fail a post
VOICE_BAR = 0.60         # voice_match / 3. Held-out posts by the same author scored 0.63 to 0.82; other writers 0.00 to 0.12
PRICE_PER_MTOK = 0.042   # USD per million input tokens on TypeSafe's API. Output is free. Check the live price.
AI_TELL_SECTION_SHARE = 0.34  # an AI tell fails the post when it is over threshold in more than a third of sections

# Judgments Jev could not make reliably on a long post. The agent does these by reading.
AGENT_REVIEW = [
    "Fact-check every external claim, number, name, and quote against its source. Jev cannot know what is true.",
    "Promise and payoff: list what the intro promises, then confirm each item is delivered.",
    "First-hand experience: is the author's own use of the thing on the page, with real output? Jev cannot tell real experience from invented, so never add any yourself. Ask the author.",
    "Replicability: could a newcomer follow this and get it working? Prerequisites, exact commands, expected output, one likely error and its fix.",
    "Limitations: does it name where the approach is a poor fit?",
    "Internal references: every 'earlier', 'above', 'later', 'at the end' must point at something that exists.",
    "Repetition across sections, and whether every section serves one main idea.",
]


# ---------------------------------------------------------------- parsing


def strip_code(text: str, placeholder: str = "") -> tuple[str, list[str]]:
    """Remove fenced code blocks line by line. Handles nested fences (a 4-backtick
    block wrapping 3-backtick ones), which a regex can't."""
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


def clean(text: str) -> str:
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)                 # frontmatter
    text = re.sub(r"^import .*$", "", text, flags=re.M)                         # mdx imports
    text = re.sub(r"\{/\*.*?\*/\}|<!--.*?-->", "", text, flags=re.S)            # comments: notes to self, not prose
    text, _ = strip_code(text, placeholder="[code block]")
    text = re.sub(r"^<[A-Z][^>]*/>\s*$", "[interactive component]", text, flags=re.M)
    text = re.sub(r"^<(video|audio|img|iframe|source)\b[^>]*>\s*$", "[embedded media]", text, flags=re.M | re.I)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def build_whole_state(frontmatter: dict, text: str) -> dict:
    words = text.split()
    if len(words) > 15000:  # Jev's context is 32k tokens; leave headroom for the questions
        text = " ".join(words[:15000])
    return {"title": frontmatter.get("title", ""), "description": frontmatter.get("description", ""), "body": text}


def split_sections(text: str) -> list[tuple[str, str]]:
    parts = re.split(r"^## +(.+)$", text, flags=re.M)
    sections = [("Opening", parts[0].strip())]
    for title, body in zip(parts[1::2], parts[2::2]):
        sections.append((title.strip(), body.strip()))
    return [(t, b) for t, b in sections if len(b.split()) >= 40]


REFERENCE_TITLE = re.compile(r"^(sources?|references?|further reading|resources|links|footnotes|credits)\b", re.I)


def is_reference_section(title: str, body: str) -> bool:
    """A list of links is not prose. Don't score it, and don't mistake it for the closing."""
    lines = [l for l in body.split("\n") if l.strip()]
    link_lines = sum(1 for l in lines if re.match(r"^\s*[-*\d.]+\s*\[", l))
    return bool(REFERENCE_TITLE.match(title)) or (len(lines) > 2 and link_lines / len(lines) > 0.6)


def voice_references(paths: list[str], exclude: str) -> list[str]:
    """Up to five ~230-word prose excerpts from the author's own finished writing."""
    files = []
    for p in paths:
        if os.path.isdir(p):
            files += [os.path.join(p, f) for f in sorted(os.listdir(p)) if f.endswith((".md", ".mdx", ".txt"))]
        else:
            files.append(p)
    refs = []
    for f in files:
        if os.path.abspath(f) == os.path.abspath(exclude):
            continue
        words = re.sub(r"^\|.*$|^#+ .*$|\[code block\]|!\[.*?\]\(.*?\)", "", clean(open(f, encoding="utf-8").read()), flags=re.M).split()
        refs.append(" ".join(words[:230]))
        if len(words) > 1200:
            refs.append(" ".join(words[len(words) // 2: len(words) // 2 + 230]))
    return refs[:5]


# ---------------------------------------------------------------- Jev


def norm(name: str, answer) -> float:
    if answer.type == "noul":
        return round(answer.noul, 3)
    return round(answer.score / (len(BANK[name]["q"].criteria) - 1), 3)


USAGE = {"requests": 0, "input_tokens": 0}
_usage_lock = threading.Lock()


def call(client, state, questions: dict):
    """One Jev request, with token accounting."""
    response = client.system_one(state=state, questions=questions)
    with _usage_lock:
        USAGE["requests"] += 1
        USAGE["input_tokens"] += response.usage.input_tokens
    return response.answers


def ask(client, state, questions: dict) -> dict:
    return {k: norm(k, a) for k, a in call(client, state, questions).items()}


def evaluate(path: str, keyword: str | None, voice_paths: list[str], references_verified: bool = False) -> dict:
    raw = open(path, encoding="utf-8").read()
    fm, _ = split_frontmatter(raw)
    text = clean(raw)
    sections = [s for s in split_sections(text) if not is_reference_section(*s)]
    refs = voice_references(voice_paths, exclude=path) if voice_paths else []
    client = TypeSafeClient()

    def section_job(title, body):
        out = ask(client, body, active("section"))
        if refs:
            a = call(client, {"reference_samples": refs, "candidate": " ".join(body.split()[:400])}, {"voice_match": VOICE_MATCH})["voice_match"]
            out["voice_match"] = round(a.score / 3, 3)
        return out

    def whole_job():
        state = build_whole_state(fm, text)
        out = ask(client, state, active("whole"))
        b = call(client, state, {"primary_blocker": PRIMARY_BLOCKER})["primary_blocker"]
        return out, {"value": b.choice, "confidence": round(b.confidence, 2), "probabilities": {k: round(v, 2) for k, v in b.probabilities.items()}}

    with ThreadPoolExecutor(max_workers=4) as pool:
        f_open = pool.submit(ask, client, sections[0][1], active("opening"))
        f_close = pool.submit(ask, client, sections[-1][1], active("closing"))
        f_whole = pool.submit(whole_job)
        f_secs = {t: pool.submit(section_job, t, b) for t, b in sections}
        opening, closing = f_open.result(), f_close.result()
        whole, blocker = f_whole.result()
        per_section = {t: f.result() for t, f in f_secs.items()}

    return score({"file": path, "words": len(text.split()), "lint": lint(path, keyword), "opening": opening, "closing": closing,
                  "whole": whole, "primary_blocker": blocker, "sections": per_section, "voice_samples": len(refs),
                  "references_verified": references_verified})


# ---------------------------------------------------------------- scoring


def failed(name: str, value: float) -> bool:
    threshold, _ = VALIDATED[name]
    return value > threshold if BANK[name]["polarity"] == "bad" else value < threshold


def score(r: dict) -> dict:
    checks = [{"area": c["area"], "check": c["check"], "pass": c["pass"], "detail": c["detail"], "source": "lint"} for c in r["lint"]["checks"]]

    def add(area, name, ok, detail):
        checks.append({"area": area, "check": name, "pass": bool(ok), "detail": detail, "source": "jev"})

    for block in ("opening", "closing", "whole"):
        for name, v in r[block].items():
            if name in VALIDATED:
                add(BANK[name]["area"], f"{block}.{name}", not failed(name, v), f"{v:.2f} (threshold {VALIDATED[name][0]}, high is {BANK[name]['polarity']})")

    n = len(r["sections"])
    for name in [k for k in VALIDATED if BANK[k]["level"] == "section"]:
        hits = [t for t, a in r["sections"].items() if name in a and failed(name, a[name])]
        mean = st.mean(a[name] for a in r["sections"].values() if name in a)
        add("ai_tells", f"sections.{name}", len(hits) / n <= AI_TELL_SECTION_SHARE, f"over threshold in {len(hits)} of {n} sections (mean {mean:.2f}): {hits}")

    voice_pct = None
    if r["voice_samples"]:
        vm = {t: a["voice_match"] for t, a in r["sections"].items() if "voice_match" in a}
        off = [t for t, v in vm.items() if v < VOICE_BAR]
        voice_pct = round(100 * (len(vm) - len(off)) / len(vm))  # share of sections that sound like the reference author
        add("voice", "sections_in_voice", voice_pct >= VOICE_AREA_BAR,
            f"{len(vm) - len(off)} of {len(vm)} sections match the reference voice (mean {st.mean(vm.values()):.2f}); off-voice: {off}")

    areas = {}
    for area in ("ai_tells", "voice", "editorial", "seo"):
        mine = [c for c in checks if c["area"] == area]
        if mine:
            areas[area] = round(100 * sum(c["pass"] for c in mine) / len(mine))
    if voice_pct is not None:
        areas["voice"] = voice_pct

    breaker_names = {"todo_markers"}
    if r["words"] <= LONG_POST_WORDS and not r.get("references_verified"):
        breaker_names.add("whole.dangling_reference")
    breakers = [c["check"] for c in checks if not c["pass"] and c["check"] in breaker_names]
    bars = {"voice": VOICE_AREA_BAR}

    r.update({"checks": checks, "area_scores": areas, "deal_breakers": breakers,
              "verdict": "PASS" if not breakers and all(v >= bars.get(a, PASS_BAR) for a, v in areas.items()) else "NEEDS WORK",
              "agent_review": AGENT_REVIEW,
              "usage": {**USAGE, "cost_usd": round(USAGE["input_tokens"] / 1e6 * PRICE_PER_MTOK, 5)}})
    del r["lint"]
    return r


# ---------------------------------------------------------------- report


def report(r: dict) -> str:
    L = [f"JEV EDITOR  {r['file']}  ({r['words']} words)", f"VERDICT: {r['verdict']}   (tells, editorial, seo >= {PASS_BAR}; voice >= {VOICE_AREA_BAR}; no deal-breakers)", ""]
    L.append("  ".join(f"{a}: {v}" for a, v in r["area_scores"].items()))
    u = r["usage"]
    L.append(f"Jev usage: {u['requests']} requests, {u['input_tokens']:,} input tokens, ${u['cost_usd']:.4f}")
    if r["deal_breakers"]:
        L.append(f"DEAL-BREAKERS: {r['deal_breakers']}")
    b = r["primary_blocker"]
    L += [f"Jev's single biggest blocker (advisory only; unreliable on long posts): {b['value']} {b['probabilities']}", ""]
    for area in r["area_scores"]:
        fails = [c for c in r["checks"] if c["area"] == area and not c["pass"]]
        L.append(f"{area.upper()}: {len(fails)} failing")
        L += [f"  [{c['source']:4s}] {c['check']:36s} {c['detail'][:170]}" for c in fails]
    L += ["", "PER SECTION (values over threshold only)"]
    for t, a in r["sections"].items():
        flags = [f"{k} {v:.2f}" for k, v in a.items() if k in VALIDATED and failed(k, v)]
        if "voice_match" in a and a["voice_match"] < VOICE_BAR:
            flags.append(f"voice_match {a['voice_match']:.2f}")
        adv = "  ".join(f"{k} {a[k]:.2f}" for k in sorted(ADVISORY) if k in a)
        L.append(f"- {t}: {', '.join(flags) or 'clean'}    [advisory: {adv}]")
    L += ["", "FOR THE AGENT TO REVIEW BY READING (Jev failed calibration on these):"] + [f"  {i}. {x}" for i, x in enumerate(r["agent_review"], 1)]
    return "\n".join(L)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--keyword", help="target search phrase, enables keyword placement checks")
    ap.add_argument("--voice-samples", nargs="*", default=[], help="files or a folder of the author's own finished writing")
    ap.add_argument("--references-verified", action="store_true",
                    help="pass ONLY after checking by hand that every 'earlier', 'above', 'below', 'next section' points at something real. "
                         "Jev can't tell a dangling reference from a post that quotes or discusses one.")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    try:
        result = evaluate(args.file, args.keyword, args.voice_samples, args.references_verified)
    except Exception as e:  # surface API and auth errors plainly for the calling agent
        sys.exit(f"jev_editor failed: {type(e).__name__}: {e}")
    print(json.dumps(result, indent=2) if args.json else report(result))
