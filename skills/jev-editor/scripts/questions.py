"""
Question bank for the Jev Editor.

Every entry is one narrow judgment. Fields:
  level     "section" (state = one section, heading included), "whole" (state = the
            full piece as {title, description, body}), "opening", or "closing"
  area      "ai_tells" | "editorial" | "seo" | "voice"
  polarity  "bad"  = a high value is a problem
            "good" = a low value is a problem
  q         the typesafe_sdk question object

Nothing here is trusted until calibrate.py has shown it separates known-good
writing from known-bad writing. See references/calibration.md for the results.
"""

from typesafe_sdk import Choice, Noul, Score


def N(level, area, polarity, text):
    return {"level": level, "area": area, "polarity": polarity, "q": Noul(instructions=text)}


def S(level, area, text, criteria):
    return {"level": level, "area": area, "polarity": "good", "q": Score(instructions=text, criteria=criteria)}


BANK = {
    # ------------------------------------------------------------ AI tells, per section
    "negative_parallelism": N("section", "ai_tells", "bad",
        "The text uses the construction 'it's not X, it's Y', 'not just X but Y', or 'isn't X. It's Y' (negating one framing in order to assert another)."),
    "rule_of_three": N("section", "ai_tells", "bad",
        "The text repeatedly groups things in threes for rhythm: three adjectives, three parallel phrases, or three short parallel sentences in a row."),
    "trailing_participle": N("section", "ai_tells", "bad",
        "At least one sentence ends with an -ing clause that comments on significance rather than adding a fact (for example ', highlighting the importance of...', ', underscoring the need for...', ', making it ideal for...')."),
    "significance_inflation": N("section", "ai_tells", "bad",
        "The text asserts that something is important, crucial, powerful, or significant without giving a concrete fact that shows why."),
    "mic_drop_closer": N("section", "ai_tells", "bad",
        "One or more paragraphs end with a short, quotable one-line sentence that restates the point for effect without adding new information."),
    "generic_claims": N("section", "ai_tells", "bad",
        "Most sentences in the text would still be true if the specific product or topic were swapped for a different one."),
    "vague_attribution": N("section", "ai_tells", "bad",
        "The text attributes a claim to unnamed sources such as 'experts', 'studies', 'many developers', or 'observers' without naming or linking them."),
    "question_then_answer": N("section", "ai_tells", "bad",
        "The text poses a short rhetorical question and immediately answers it itself (for example 'The result? ...' or 'Why does this matter? Because...')."),
    "staccato_fragments": N("section", "ai_tells", "bad",
        "The text uses a run of very short sentences or sentence fragments in a row for dramatic effect."),
    "signposting": N("section", "ai_tells", "bad",
        "The text announces what it is about to say instead of saying it (for example 'Let's break this down', 'In this section we'll explore', 'Here's what you need to know')."),
    "superficial_analysis": N("section", "ai_tells", "bad",
        "The text includes commentary on what a fact 'means', 'shows', or 'reflects' that adds no new fact or reasoning."),
    "over_balanced": N("section", "ai_tells", "bad",
        "Every position the text takes is immediately softened or countered, so that it never commits to a claim a reader could disagree with."),
    "invented_labels": N("section", "ai_tells", "bad",
        "The text coins its own catchy name for a concept (for example 'the supervision paradox' or 'the context tax') and treats it as an established term."),
    "forced_analogy": N("section", "ai_tells", "bad",
        "The text explains something with an analogy that is generic or does not add understanding (for example 'think of it as a highway for data')."),
    "empty_intensifiers": N("section", "ai_tells", "bad",
        "The text uses intensifier words that add no meaning, such as 'genuinely', 'truly', 'actually', 'really', 'incredibly', or 'real' used for emphasis."),

    # ------------------------------------------------------------ editorial, per section
    "first_hand": N("section", "editorial", "good",
        "The text includes something the author personally did, measured, observed, or concluded from their own use."),
    "concrete_example": N("section", "editorial", "good",
        "The text includes at least one concrete example, real number, command, or piece of output, not only abstract description."),
    "claims_evidenced": N("section", "editorial", "good",
        "Every significant factual or performance claim in the text is backed by a number, a named source, or the author's own result."),
    "paragraph_leads": N("section", "editorial", "good",
        "Most paragraphs open with a sentence that states the paragraph's main point."),
    "heading_informative": N("section", "editorial", "good",
        "The heading tells the reader what the section contains, rather than teasing or being clever."),
    "jargon_defined": N("section", "editorial", "good",
        "Every specialized term or acronym in the text is either defined, expanded, or would already be familiar to a working software developer."),
    "insight_density": S("section", "editorial",
        "How much non-obvious insight does this text contain, beyond describing the topic?",
        ["Purely descriptive; restates what source material says", "One useful insight or example",
         "Several useful insights or examples", "Dense with non-obvious insight throughout"]),

    # ------------------------------------------------------------ SEO / AI search, per section
    "answer_first": N("section", "seo", "good",
        "The first one or two sentences under the heading directly address what the heading says the section is about."),
    "entity_clarity": N("section", "seo", "good",
        "Tools, products, versions, and people are referred to by their specific names rather than vague references like 'the tool' or 'some frameworks'."),
    "specific_figures": N("section", "seo", "good",
        "The text uses specific figures (numbers, prices, durations, versions) instead of vague quantifiers like 'many', 'significantly', or 'a lot'."),
    "self_contained_passage": N("section", "seo", "good",
        "The text contains at least one passage of one to three sentences that would make complete sense if quoted on its own, out of context."),

    # ------------------------------------------------------------ whole piece: editorial
    "promise_stated": N("opening", "editorial", "good",
        "The text explicitly states what the reader will learn or be able to do by the end of the article."),
    "promise_payoff": N("whole", "editorial", "good",
        "Every outcome promised in the introduction of `body` is delivered later in `body`."),
    "controlling_idea": N("whole", "editorial", "good",
        "All major sections of `body` serve one main idea."),
    "makes_real_argument": N("whole", "editorial", "good",
        "`body` stakes out an actual opinion or recommendation, rather than describing or surveying the topic neutrally."),
    "names_limitation": N("whole", "editorial", "good",
        "`body` names at least one limitation, trade-off, or case where what it recommends is a poor fit."),
    "shows_results": N("whole", "editorial", "good",
        "`body` shows actual outputs or results (program output, measurements, screenshots described, before and after) rather than only describing them."),
    "replicable": N("whole", "editorial", "good",
        "A reader who has never used the subject of `body` could follow it and get the thing working: setup, exact commands or code, and what success looks like are all present."),
    "troubleshooting": N("whole", "editorial", "good",
        "`body` addresses at least one likely error, pitfall, or gotcha and how to deal with it."),
    "no_repetition": N("whole", "editorial", "bad",
        "At least one section of `body` substantially repeats material already covered in another section."),
    "dangling_reference": N("whole", "editorial", "bad",
        "`body` refers the reader to another part of itself (an earlier section, a later link, a quickstart) that does not appear anywhere in `body`."),
    "transitions": N("whole", "editorial", "good",
        "Major sections of `body` are connected: a section's opening or the previous section's close links the two."),
    "structural_clarity": S("whole", "editorial",
        "How well organized is `body`?",
        ["Disorganized; hard to follow the throughline", "Loosely organized",
         "Clearly organized with a visible throughline", "Tight, well-sequenced, nothing out of place"]),

    # ------------------------------------------------------------ whole piece: SEO / AI search
    "honest_title": N("whole", "seo", "good",
        "`title` accurately describes what `body` delivers, without exaggeration."),
    "title_specific": N("whole", "seo", "good",
        "`title` tells a searcher specifically what they will get (the angle, the outcome, or who it is for), beyond only naming the topic."),
    "description_compelling": N("whole", "seo", "good",
        "`description` gives a searcher a concrete reason to click: a specific outcome, result, or detail from `body`."),
    "front_loaded_answer": N("opening", "seo", "good",
        "Within its first 100 words, the text names the topic and states the main answer or takeaway."),
    "quotable_definition": N("whole", "seo", "good",
        "`body` defines its central concept in a single sentence that would make sense quoted out of context."),
    "original_results": N("whole", "seo", "good",
        "`body` includes original data, code, measurements, or results produced by the author, not only information available from the subject's own documentation."),
    "sourced_claims": N("whole", "seo", "good",
        "Statistics and external factual claims in `body` are attributed to a named source."),
    "covers_adjacent_questions": N("whole", "seo", "good",
        "`body` answers the follow-up questions a reader of this topic would naturally ask next, such as cost, limitations, alternatives, and how to get started."),

    # ------------------------------------------------------------ opening / closing
    "specific_hook": N("opening", "editorial", "good",
        "The first two sentences make a specific, concrete claim or observation that could only be written about this exact topic."),
    "cliche_opener": N("opening", "ai_tells", "bad",
        "The opening uses a stock phrase or cliche (for example 'making waves', 'in today's world', 'game-changer', 'taking the world by storm')."),
    "author_present": N("opening", "editorial", "good",
        "The opening includes the author's own first-hand experience, such as something they built, tested, measured, or were surprised by."),
    "background_first": N("opening", "editorial", "bad",
        "The opening spends its first paragraph on general background or history before getting to a specific problem, result, or claim."),
    "gives_next_action": N("closing", "editorial", "good",
        "The closing tells the reader one specific thing to go and do next."),
    "summary_ending": N("closing", "ai_tells", "bad",
        "The closing mainly summarizes or repeats what the piece already said."),
    "lands_with_energy": S("closing", "editorial",
        "How strongly does the final paragraph land?",
        ["Trails off; reads like the author ran out of things to say", "Functional but forgettable",
         "Ends on a clear, confident note", "Memorable final line that a reader would quote"]),
}

PRIMARY_BLOCKER = Choice(
    instructions="What is the single biggest thing holding `body` back from being published as-is?",
    criteria={
        "ready": "Nothing significant; it can be published as-is",
        "needs_stronger_hook": "The opening is generic or cliched and doesn't earn attention",
        "needs_more_specificity": "Too vague or generic; lacks concrete examples, numbers, or detail",
        "needs_cutting": "Padding or repetition should be cut",
        "needs_author_voice": "Reads like neutral documentation; the author's own experience and opinions are missing",
        "internally_inconsistent": "The piece contradicts itself or refers to parts of itself that do not exist",
    },
)

VOICE_MATCH = Score(
    instructions="How closely does the writing voice of `candidate` match the voice of the author who wrote `reference_samples`? Judge tone, sentence rhythm, humor, word choice, and how the author addresses the reader. Ignore topic.",
    criteria=["Clearly a different voice from the reference author", "Some overlap in tone, but reads like a different writer",
              "Plausibly the same author", "Unmistakably the same author"],
)


# Questions the editor actually uses, with the evidence that earned each its place.
#   sep    = separation between 4 published posts and 5 raw AI first drafts (calibrate.py), 0-1 scale
#   ablate = responded correctly when a good post was deliberately broken on that one dimension
#   threshold = midpoint between the good and bad means (or 0.5 for ablation-validated questions)
VALIDATED = {
    # name:                  (threshold, evidence)
    "empty_intensifiers":     (0.54, "sep +0.56 (good 0.25, AI draft 0.82)"),
    "negative_parallelism":   (0.64, "sep +0.44 (good 0.42, AI draft 0.86)"),
    "question_then_answer":   (0.30, "sep +0.39 (good 0.11, AI draft 0.49)"),
    "signposting":            (0.60, "sep +0.37 (good 0.41, AI draft 0.79)"),
    "superficial_analysis":   (0.60, "sep +0.33 (good 0.43, AI draft 0.76)"),
    "rule_of_three":          (0.52, "sep +0.26 (good 0.39, AI draft 0.65)"),
    "significance_inflation": (0.63, "sep +0.26 (good 0.50, AI draft 0.76)"),
    "mic_drop_closer":        (0.58, "sep +0.26 (good 0.45, AI draft 0.71)"),
    "trailing_participle":    (0.33, "sep +0.21 (good 0.22, AI draft 0.43)"),
    "cliche_opener":          (0.50, "sep +0.33; generic filler 0.96"),
    "specific_hook":          (0.50, "generic filler 0.26 vs drafts 0.64; sep only +0.14, treat as advisory"),
    "promise_stated":         (0.50, "asked of the opening only; the whole-post version ignored a deleted intro"),
    "front_loaded_answer":    (0.50, "asked of the opening only"),
    "gives_next_action":      (0.50, "ablate: real closing 0.89, generic summary closing 0.03"),
    "summary_ending":         (0.85, "ablate: real 0.76, generic summary 0.93; many good endings recap a little"),
    "lands_with_energy":      (0.50, "ablate: real 0.78, generic summary 0.40 (normalized)"),
    "honest_title":           (0.50, "ablate: real 0.77, clickbait 0.14"),
    "title_specific":         (0.50, "ablate: real 0.69, generic title 0.12"),
    "description_compelling": (0.50, "ablate: real 0.86, generic 0.12"),
    "quotable_definition":    (0.50, "sep +0.23"),
    "dangling_reference":     (0.50, "responded on a 3.5k-word post (0.89 to 0.79 after fixes); NOT sensitive on a 9k-word post"),
}

# Reported but never scored: weak separation. Useful as a hint, not as a gate.
ADVISORY = {"insight_density", "paragraph_leads", "entity_clarity"}

# Tried and rejected. Kept here so nobody re-adds them without new evidence.
REJECTED = {
    "first_hand":        "INVERTED (good 0.60, AI draft 0.81). AI drafts write 'I tested this' freely; Jev judges the claim, not whether it happened.",
    "specific_figures":  "INVERTED (good 0.48, AI draft 0.75). AI drafts are full of confident numbers, some invented.",
    "author_present":    "No separation (0.94 vs 0.95), same reason as first_hand.",
    "generic_claims":    "No separation (0.63 vs 0.62).",
    "over_balanced":     "No separation; near zero on everything.",
    "invented_labels":   "No separation.",
    "names_limitation":  "Saturated at 0.98 and stayed there after every limitation paragraph was deleted.",
    "troubleshooting":   "Saturated at 0.99; same.",
    "promise_payoff":    "Did not respond when six sections were deleted from a 9k-word post.",
    "replicable":        "About 0.5 with or without the code blocks visible.",
    "shows_results":     "0.16 on a post full of real output (0.42 with code visible). Unreliable.",
    "concrete_example, claims_evidenced, heading_informative, answer_first, self_contained_passage, controlling_idea, transitions, structural_clarity, makes_real_argument, original_results, covers_adjacent_questions, no_repetition, background_first, staccato_fragments, vague_attribution, forced_analogy, jargon_defined":
                         "No useful separation between published posts and raw AI drafts.",
    "needs_fact_check (blocker option)": "Fired on 3 of 4 published posts. Read literally, every factual article 'contains a claim that needs verification'.",
}


def by_level(level: str, names: set | None = None) -> dict:
    """Questions for one level. With names=None, returns every candidate (calibrate.py uses this)."""
    return {k: v["q"] for k, v in BANK.items() if v["level"] == level and (names is None or k in names)}


def active(level: str) -> dict:
    """Only the questions that earned their place."""
    return by_level(level, set(VALIDATED) | ADVISORY)
