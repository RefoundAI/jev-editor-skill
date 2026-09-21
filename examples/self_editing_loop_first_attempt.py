"""
First attempt at the self-editing article loop. Kept for reference only.

Use self_editing_loop.py instead. This version has no author notes, so when its
feedback asked for "a specific example" the rewriter invented one, and Jev scored
the invention 0.92. It also has a needs_fact_check option that can never lose.

Jev (TypeSafe AI) judges a draft against a fixed battery of questions.
An LLM (Claude, here) revises the draft based on that judgment.
The two hand the draft back and forth until it passes or a max-iteration
guard trips and it escalates to a human.

Requires:
  - TYPESAFE_API_KEY   (https://typesafe.ai)
  - ANTHROPIC_API_KEY  (https://console.anthropic.com)

Install:
  pip install typesafe-sdk anthropic

Run:
  python self_editing_loop_first_attempt.py
"""

from __future__ import annotations

import anthropic
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

jev = TypeSafeClient()  # reads TYPESAFE_API_KEY
claude = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY


QUESTIONS = {
    "has_specific_hook": Noul(
        instructions=(
            "The opening 1-2 sentences make a specific, concrete claim or "
            "observation, not a generic statement anyone could write about this topic."
        )
    ),
    "makes_real_argument": Noul(
        instructions=(
            "The piece stakes out an actual opinion or takeaway, rather than "
            "just describing or surveying the topic neutrally."
        )
    ),
    "has_filler": Noul(
        instructions=(
            "The piece contains noticeable padding, repetition, or throat-clearing "
            "that doesn't add new information."
        )
    ),
    "sounds_templated": Noul(
        instructions=(
            "The phrasing reads like generic AI output: hedge-y language, cliche "
            "transitions ('in today's fast-paced world', 'it's important to note'), "
            "or list-heavy structure without real substance."
        )
    ),
    "matches_audience": Noul(
        instructions=(
            "The piece speaks to a technically literate reader's actual level and "
            "concerns, rather than a generic reader."
        )
    ),
    "insight_density": Score(
        instructions="How much non-obvious insight does this piece contain, beyond describing the topic?",
        criteria=[
            "Purely descriptive -- no insight beyond restating the topic",
            "One genuinely useful insight or example",
            "Several useful insights or examples",
            "Dense with non-obvious insight throughout",
        ],
    ),
    "structural_clarity": Score(
        instructions="How well organized and scannable is this piece?",
        criteria=[
            "Disorganized -- hard to follow the throughline",
            "Loosely organized",
            "Clearly organized with a visible throughline",
            "Tight, well-sequenced, nothing out of place",
        ],
    ),
    "primary_blocker": Choice(
        instructions="If this piece is not ready to publish as-is, what's the single biggest thing holding it back?",
        criteria={
            "ready": "It's ready to publish as-is",
            "needs_stronger_hook": "The opening doesn't earn the reader's attention",
            "needs_more_specificity": "Too vague or generic; needs concrete detail",
            "needs_cutting": "Padding or repetition needs to be cut",
            "needs_fact_check": "Contains a claim that needs verification",
        },
    ),
}

WEIGHTS = {
    "has_specific_hook": 0.20,
    "makes_real_argument": 0.20,
    "has_filler": -0.15,  # penalize
    "sounds_templated": -0.15,  # penalize
    "matches_audience": 0.10,
    "insight_density": 0.20,  # normalized to /3
    "structural_clarity": 0.10,  # normalized to /3
}

PASS_THRESHOLD = 0.75
MAX_ITERATIONS = 3


def evaluate(draft: str) -> dict:
    response = jev.system_one(state=draft, questions=QUESTIONS)
    return response.answers


def composite_score(answers: dict) -> float:
    score = 0.0
    score += WEIGHTS["has_specific_hook"] * answers["has_specific_hook"].noul
    score += WEIGHTS["makes_real_argument"] * answers["makes_real_argument"].noul
    score += WEIGHTS["has_filler"] * answers["has_filler"].noul
    score += WEIGHTS["sounds_templated"] * answers["sounds_templated"].noul
    score += WEIGHTS["matches_audience"] * answers["matches_audience"].noul
    score += WEIGHTS["insight_density"] * (answers["insight_density"].score / 3)
    score += WEIGHTS["structural_clarity"] * (answers["structural_clarity"].score / 3)
    # the negative weights can pull this below zero, so clip into a clean 0-1 range
    return max(0.0, min(1.0, score + 0.3))


def build_feedback(answers: dict) -> str:
    """Jev only returns probabilities -- this is where a typed diagnosis
    becomes plain-language instructions a writer model can act on."""
    issues = []
    if answers["has_specific_hook"].noul < 0.5:
        issues.append("Open with a specific, concrete claim or example, not a generic statement.")
    if answers["makes_real_argument"].noul < 0.5:
        issues.append("Stake out an actual opinion or takeaway instead of surveying the topic neutrally.")
    if answers["has_filler"].noul > 0.5:
        issues.append("Cut padding and repeated phrasing -- every sentence should add something new.")
    if answers["sounds_templated"].noul > 0.5:
        issues.append("Rewrite in a distinct voice -- cut hedge phrases and cliche transitions.")
    if answers["insight_density"].score < 1.5:
        issues.append("Add a specific, non-obvious insight or example, not just a description.")
    if not issues:
        issues.append("Tighten the weakest paragraph and clarify the throughline.")
    return "\n".join(f"- {i}" for i in issues)


def rewrite(draft: str, feedback: str) -> str:
    message = claude.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": (
                    "Revise the draft below to address every issue listed. "
                    "Keep the core point and roughly the same length. "
                    "Return only the revised draft, no commentary.\n\n"
                    f"Issues to fix:\n{feedback}\n\n"
                    f"Draft:\n{draft}"
                ),
            }
        ],
    )
    return message.content[0].text


def self_edit(draft: str) -> tuple[str, str, int]:
    for i in range(1, MAX_ITERATIONS + 1):
        answers = evaluate(draft)
        score = composite_score(answers)
        blocker = answers["primary_blocker"].choice
        print(f"[iteration {i}] score={score:.2f}  blocker={blocker}")

        if score >= PASS_THRESHOLD and blocker == "ready":
            return draft, "ready_to_publish", i

        feedback = build_feedback(answers)
        print(f"[iteration {i}] feedback:\n{feedback}\n")
        draft = rewrite(draft, feedback)

    return draft, "needs_human_review", MAX_ITERATIONS


SLOP_DRAFT = """In today's fast-paced digital landscape, AI agents are revolutionizing
the way businesses operate. These powerful tools leverage cutting-edge technology to
streamline workflows and boost productivity. It's important to note that AI agents
offer a wide range of benefits, from automating repetitive tasks to providing valuable
insights. By harnessing the power of AI agents, companies can unlock new levels of
efficiency and stay ahead of the competition."""


if __name__ == "__main__":
    final_draft, status, iterations = self_edit(SLOP_DRAFT)
    print(f"\nFinal status: {status} after {iterations} iteration(s)\n")
    print(final_draft)
