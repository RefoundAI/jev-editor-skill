#!/usr/bin/env python3
"""
Calibrate the question bank: which questions separate writing you consider
good from writing you consider bad?

  python calibrate.py --good path/to/good/*.md --bad path/to/bad/*.md [--json out.json]

"good" = finished pieces you're proud of. "bad" = raw AI drafts, or anything you
would not publish. For each question it reports the mean answer on each set and
the separation between them. Keep questions with clear separation in the right
direction; drop or reword the rest. Re-run whenever you add or change a question.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics as st
from concurrent.futures import ThreadPoolExecutor

from typesafe_sdk import TypeSafeClient

from jev_editor import build_whole_state, clean, split_sections
from lint import split_frontmatter
from questions import BANK, by_level

KEEP_MARGIN = 0.20  # minimum normalized separation, in the expected direction, to keep a question


def value(name: str, answer) -> float:
    """Normalize every answer to 0-1."""
    if answer.type == "noul":
        return answer.noul
    return answer.score / (len(BANK[name]["q"].criteria) - 1)


def ask(client, state, questions) -> dict:
    answers = client.system_one(state=state, questions=questions).answers
    return {k: value(k, a) for k, a in answers.items()}


def jobs_for(path: str, per_doc_sections: int, rng: random.Random) -> list[tuple[str, object]]:
    raw = open(path, encoding="utf-8").read()
    fm, _ = split_frontmatter(raw)
    text = clean(raw)
    sections = split_sections(text)
    body_sections = [s for s in sections[1:] if 120 <= len(s[1].split()) <= 900] or sections
    picked = rng.sample(body_sections, min(per_doc_sections, len(body_sections)))
    out = [("whole", build_whole_state(fm, text)), ("opening", sections[0][1]), ("closing", sections[-1][1])]
    out += [("section", b) for t, b in picked]
    return out


def run(paths: list[str], per_doc_sections: int, seed: int) -> dict[str, list[float]]:
    client, rng = TypeSafeClient(), random.Random(seed)
    work = [(lvl, state) for p in paths for lvl, state in jobs_for(p, per_doc_sections, rng)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda w: ask(client, w[1], by_level(w[0])), work))
    collected: dict[str, list[float]] = {}
    for r in results:
        for k, v in r.items():
            collected.setdefault(k, []).append(v)
    return collected


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--good", nargs="+", required=True)
    ap.add_argument("--bad", nargs="+", required=True)
    ap.add_argument("--sections-per-doc", type=int, default=4)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--json")
    a = ap.parse_args()

    good, bad = run(a.good, a.sections_per_doc, a.seed), run(a.bad, a.sections_per_doc, a.seed)
    rows = []
    for name, meta in BANK.items():
        if name not in good or name not in bad:
            continue
        g, b = st.mean(good[name]), st.mean(bad[name])
        sep = (b - g) if meta["polarity"] == "bad" else (g - b)  # positive = separates in the expected direction
        verdict = "KEEP" if sep >= KEEP_MARGIN else ("weak" if sep >= 0.08 else ("DROP" if sep > -0.08 else "INVERTED"))
        rows.append({"question": name, "level": meta["level"], "area": meta["area"], "polarity": meta["polarity"],
                     "good_mean": round(g, 2), "bad_mean": round(b, 2), "separation": round(sep, 2),
                     "n_good": len(good[name]), "n_bad": len(bad[name]), "verdict": verdict})
    rows.sort(key=lambda r: (r["area"], -r["separation"]))
    if a.json:
        json.dump(rows, open(a.json, "w"), indent=1)
    print(f"{'question':28s} {'level':8s} {'area':10s} {'pol':5s} {'good':>5s} {'bad':>5s} {'sep':>6s}  verdict   (n good/bad)")
    for r in rows:
        print(f"{r['question']:28s} {r['level']:8s} {r['area']:10s} {r['polarity']:5s} {r['good_mean']:5.2f} {r['bad_mean']:5.2f} {r['separation']:+6.2f}  {r['verdict']:9s} ({r['n_good']}/{r['n_bad']})")
