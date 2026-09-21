"""
Self-editing article loop, version 2.

The first version (self_editing_loop.py) made a draft worse before handing it
to a human. Four fixes:

  1. The rewriter gets NOTES: facts from the author. It may use only those.
     Asking a model for "specifics" without supplying any invites fabrication.
  2. Jev checks the draft AGAINST those notes. It can't check facts against the
     world, but it can check a draft against source material you give it.
     This replaces the old "needs_fact_check" option, which could never lose.
  3. Feedback is driven by what is actually wrong. If nothing is, the loop
     stops instead of sending a vague "tighten it" that degrades a good draft.
  4. The loop keeps the best draft it has seen, and returns that one.

Requires TYPESAFE_API_KEY and ANTHROPIC_API_KEY.
  pip install typesafe-sdk anthropic
  python self_editing_loop_v2.py
"""

from __future__ import annotations

import anthropic
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

jev = TypeSafeClient()  # reads TYPESAFE_API_KEY
claude = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY

# State is now an object, so questions refer to `draft` and `notes` by name.
QUESTIONS = {
    "has_specific_hook": Noul(
        instructions="The opening 1-2 sentences of `draft` make a specific, concrete claim or observation, not a generic statement anyone could write about this topic."
    ),
    "makes_real_argument": Noul(
        instructions="`draft` stakes out an actual opinion or takeaway, rather than just describing or surveying the topic neutrally."
    ),
    "has_filler": Noul(
        instructions="`draft` contains noticeable padding, repetition, or throat-clearing that doesn't add new information."
    ),
    "sounds_templated": Noul(
        instructions="The phrasing of `draft` reads like generic AI output: hedge-y language, cliche transitions ('in today's fast-paced world', 'it's important to note'), or list-heavy structure without real substance."
    ),
    "matches_audience": Noul(
        instructions="`draft` speaks to a technically literate reader's actual level and concerns, rather than a generic reader."
    ),
    # New: a grounded check. Jev compares the draft to the notes it was given.
    "unsupported_claims": Noul(
        instructions="`draft` contains a specific fact, number, quote, person, company, or anecdote that is not supported by `notes`."
    ),
    "insight_density": Score(
        instructions="How much non-obvious insight does `draft` contain, beyond describing the topic?",
        criteria=[
            "Purely descriptive -- no insight beyond restating the topic",
            "One genuinely useful insight or example",
            "Several useful insights or examples",
            "Dense with non-obvious insight throughout",
        ],
    ),
    "structural_clarity": Score(
        instructions="How well organized and scannable is `draft`?",
        criteria=[
            "Disorganized -- hard to follow the throughline",
            "Loosely organized",
            "Clearly organized with a visible throughline",
            "Tight, well-sequenced, nothing out of place",
        ],
    ),
    "primary_blocker": Choice(
        instructions="What is the single biggest thing holding `draft` back from being published as-is?",
        criteria={
            "ready": "Nothing significant; it can be published as-is",
            "needs_stronger_hook": "The opening is generic and doesn't earn attention",
            "needs_more_specificity": "Too vague or generic; lacks concrete detail",
            "needs_cutting": "Padding or repetition should be cut",
        },
    ),
}

WEIGHTS = {
    "has_specific_hook": 0.20,
    "makes_real_argument": 0.20,
    "has_filler": -0.15,
    "sounds_templated": -0.15,
    "matches_audience": 0.10,
    "insight_density": 0.20,  # normalized to /3
    "structural_clarity": 0.10,  # normalized to /3
}

PASS_THRESHOLD = 0.75
MAX_UNSUPPORTED = 0.30  # a hard condition, kept out of the weighted score on purpose
MAX_ITERATIONS = 3


def evaluate(draft: str, notes: str) -> dict:
    return jev.system_one(state={"notes": notes, "draft": draft}, questions=QUESTIONS).answers


def composite_score(answers: dict) -> float:
    score = 0.0
    for name, weight in WEIGHTS.items():
        a = answers[name]
        score += weight * (a.score / 3 if a.type == "score" else a.noul)
    return max(0.0, min(1.0, (score + 0.3) / 1.1))  # rescale the -0.3..0.8 range onto 0..1


def passes(answers: dict) -> bool:
    return (
        composite_score(answers) >= PASS_THRESHOLD
        and answers["primary_blocker"].choice == "ready"
        and answers["unsupported_claims"].noul <= MAX_UNSUPPORTED
    )


BLOCKER_INSTRUCTIONS = {
    "needs_stronger_hook": "Rewrite the first two sentences so they open on the most specific fact in the notes.",
    "needs_more_specificity": "Replace general statements with concrete details from the notes.",
    "needs_cutting": "Cut any sentence that restates an earlier one.",
}


def build_feedback(answers: dict) -> list[str]:
    """Turn Jev's numbers into instructions. An empty list means there is
    nothing concrete to ask for, and the loop should stop rather than guess."""
    issues = []
    if answers["unsupported_claims"].noul > MAX_UNSUPPORTED:
        issues.append("Remove every fact, number, person, company, or anecdote that is not in the notes. Do not replace it with another invented one.")
    if answers["has_specific_hook"].noul < 0.5:
        issues.append("Open with a specific, concrete claim taken from the notes, not a generic statement.")
    if answers["makes_real_argument"].noul < 0.5:
        issues.append("Stake out an actual opinion or takeaway instead of surveying the topic neutrally.")
    if answers["has_filler"].noul > 0.5:
        issues.append("Cut padding and repeated phrasing. Every sentence should add something new.")
    if answers["sounds_templated"].noul > 0.5:
        issues.append("Rewrite in a plain, direct voice. Cut hedge phrases and cliche transitions.")
    if answers["insight_density"].score < 1.5:
        issues.append("Build the paragraph around the most non-obvious point in the notes.")
    blocker = answers["primary_blocker"].choice
    if blocker in BLOCKER_INSTRUCTIONS and BLOCKER_INSTRUCTIONS[blocker] not in issues:
        issues.append(BLOCKER_INSTRUCTIONS[blocker])
    return issues


def rewrite(draft: str, issues: list[str], notes: str) -> str:
    feedback = "\n".join(f"- {i}" for i in issues)
    message = claude.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": (
                    "Revise the draft below to address every issue listed. "
                    "Keep roughly the same length.\n\n"
                    "Rules:\n"
                    "- Use only facts that appear in the author's notes. Never invent an example, "
                    "number, person, company, or anecdote.\n"
                    "- If an issue can't be fixed with what's in the notes, leave it unfixed.\n"
                    "- Return only the revised draft. No commentary, no notes to the editor.\n\n"
                    f"Author's notes:\n{notes}\n\n"
                    f"Issues to fix:\n{feedback}\n\n"
                    f"Draft:\n{draft}"
                ),
            }
        ],
    )
    return message.content[0].text


def self_edit(draft: str, notes: str) -> tuple[str, str, int]:
    best = (-1.0, draft)  # (score, draft) among drafts with no unsupported claims

    for i in range(1, MAX_ITERATIONS + 1):
        answers = evaluate(draft, notes)
        score = composite_score(answers)
        unsupported = answers["unsupported_claims"].noul
        print(f"[iteration {i}] score={score:.2f}  blocker={answers['primary_blocker'].choice}  unsupported={unsupported:.2f}")

        if unsupported <= MAX_UNSUPPORTED and score > best[0]:
            best = (score, draft)
        if passes(answers):
            return draft, "ready_to_publish", i

        issues = build_feedback(answers)
        if not issues:
            # Jev has no concrete complaint left. Another rewrite would be a guess.
            return best[1], "needs_human_review", i
        print("\n".join(f"    - {x}" for x in issues))
        if i < MAX_ITERATIONS:
            draft = rewrite(draft, issues, notes)

    return best[1], "needs_human_review", MAX_ITERATIONS


SLOP_DRAFT = """In today's fast-paced digital landscape, AI agents are revolutionizing
the way businesses operate. These powerful tools leverage cutting-edge technology to
streamline workflows and boost productivity. It's important to note that AI agents
offer a wide range of benefits, from automating repetitive tasks to providing valuable
insights. By harnessing the power of AI agents, companies can unlock new levels of
efficiency and stay ahead of the competition."""

# What the author actually knows. Replace with your own.
NOTES = """- I build production AI agents for clients.
- Most of the LLM calls inside those agents make a decision. Few of them write anything.
- Example: one agent reads every inbound customer email for an e-commerce brand and decides what kind of email it is before anything else happens.
- Example: another agent scans social media and decides whether each brand it finds meets a VC firm's investment criteria.
- Today each of those decisions is a full LLM call. That is slow, and it adds up at volume.
- When an LLM says it is "confident" in a classification, that number is not calibrated.
- These decisions are closed-ended: a fixed set of categories, or a list of yes/no criteria."""


if __name__ == "__main__":
    final_draft, status, iterations = self_edit(SLOP_DRAFT, NOTES)
    print(f"\nFinal status: {status} after {iterations} iteration(s)\n")
    print(final_draft)
