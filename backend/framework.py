"""
Communication frameworks, keyed by name.

Each framework defines the underlying FUNCTIONS a strong answer needs to
serve — not a fixed step order. The model evaluates whether each function
was served, however it was expressed, not whether the person labeled or
sequenced it a particular way. This is what makes feedback feel like
coaching on real speech instead of grading against a template.

Extra fields per framework (used for retry design and difficulty
progression, not yet wired into scoring):
  - minimum_sufficient_structure: the least a response needs to "work"
  - flexibility_rules: framework-specific notes on how components can
    combine/reorder/go implicit
  - common_failure_modes: typical ways people struggle with this challenge,
    used to pick a targeted retry (see Section 9 of the design doc)

CHALLENGE_TYPES maps a kind of communication challenge to the framework
used to evaluate it. Scoring is called with a challenge_type directly —
there's no level number in between.
"""

FRAMEWORKS = {
    "DIRECT_ANSWER": {
        "purpose": "Help the speaker answer a direct question quickly, without losing the listener in preamble.",
        "functions": [
            {"id": "bottom_line", "name": "Bottom line",
             "question": "Did they state their actual answer early, before the explanation?"},
            {"id": "relevance", "name": "Relevance",
             "question": "Did everything they said relate to the question asked?"},
            {"id": "forward_motion", "name": "Forward motion",
             "question": "Did each part of the answer add something new, rather than restating the same point?"},
        ],
        "minimum_sufficient_structure": "A stated answer, even without a reason, is sufficient if the question only asked for a position.",
        "flexibility_rules": "Answer and reason may be combined in one sentence. A literal 'my answer is...' is never required.",
        "common_failure_modes": ["Buries the answer after long preamble", "Answers a nearby but different question", "Restates the same point instead of adding new information"],
    },
    "WHAT_WHY_EXAMPLE": {
        "purpose": "Help the speaker explain an unfamiliar concept in a way another person can understand.",
        "functions": [
            {"id": "what", "name": "What",
             "question": "Did they clearly state what the thing is, in plain terms a novice could grasp?"},
            {"id": "why", "name": "Why",
             "question": "Did they explain why it matters or why it works the way it does?"},
            {"id": "example", "name": "Example",
             "question": "Did they ground the explanation in a concrete example or comparison?"},
        ],
        "minimum_sufficient_structure": "What + one of (Why or Example) is usually enough for a short explanation.",
        "flexibility_rules": "All three may appear in a single sentence for simple concepts. Do not require all three when the question is adequately answered with fewer.",
        "common_failure_modes": ["Uses jargon without defining it", "Explains why before establishing what", "Gives no concrete example, stays fully abstract"],
    },
    "POINT_REASON_EVIDENCE": {
        "purpose": "Help the speaker develop a single point into a fuller, more convincing idea.",
        "functions": [
            {"id": "point", "name": "Point", "question": "Did they state a clear position or claim?"},
            {"id": "reason", "name": "Reason", "question": "Did they explain why they hold that position?"},
            {"id": "evidence", "name": "Evidence",
             "question": "Did they support the reason with a specific example, fact, or piece of evidence?"},
        ],
        "minimum_sufficient_structure": "Point + Reason is sufficient; Evidence strengthens but a short response can pass without it if the exercise doesn't call for depth.",
        "flexibility_rules": "Evidence may be personal experience, an example, an observation, or data — do not demand statistics.",
        "common_failure_modes": ["States an opinion with no reason attached", "Reason is vague ('it's just better')", "No concrete example, evidence stays abstract"],
    },
    "SPONTANEOUS_ANSWER": {
        "purpose": "Help the speaker produce a coherent, on-topic answer to something they weren't prepared for.",
        "functions": [
            {"id": "coherence", "name": "Coherence",
             "question": "Did the answer hold together as a single line of thought, even if imperfect?"},
            {"id": "on_question", "name": "Answered the actual question",
             "question": "Did they address what was actually asked, not a nearby or easier question?"},
            {"id": "recovery", "name": "Recovery",
             "question": "If they hesitated or stumbled, did they recover and keep going rather than stalling out?"},
        ],
        "minimum_sufficient_structure": "A coherent, on-topic answer, even if short or imperfect, is sufficient — polish is not required.",
        "flexibility_rules": "A thoughtful pause before answering should never be penalized; unnecessary filler during the pause is the actual problem, not the pause itself.",
        "common_failure_modes": ["Freezes and gives up before producing an answer", "Drifts to an easier, related question instead of the one asked", "Long silent search for an answer with no recovery"],
    },
    "ANSWER_REASON": {
        "purpose": "Help a speaker answer a question directly before explaining their thinking (everyday/interview/Q&A version of directness).",
        "functions": [
            {"id": "answer", "name": "Answer", "question": "Did they give the answer or position?"},
            {"id": "reason", "name": "Reason", "question": "Did they explain why?"},
        ],
        "minimum_sufficient_structure": "Answer alone is sufficient for a yes/no or short-fact question; Reason is expected when the question invites explanation.",
        "flexibility_rules": "No formal transition needed between answer and reason ('I chose X because Y' is already both).",
        "common_failure_modes": ["Gives reasoning without ever stating a clear answer", "Answer arrives only after multiple sentences of buildup"],
    },
    "CLAIM_EVIDENCE_REASONING": {
        "purpose": "Help speakers make an argument that is supported rather than simply asserted.",
        "functions": [
            {"id": "claim", "name": "Claim", "question": "What are they arguing?"},
            {"id": "evidence", "name": "Evidence", "question": "What supports the claim?"},
            {"id": "reasoning", "name": "Reasoning", "question": "Why does the evidence support the claim?"},
        ],
        "minimum_sufficient_structure": "Claim + Evidence is sufficient at a basic level; Reasoning (the logical link) is what separates a strong argument from a list of facts next to an opinion.",
        "flexibility_rules": "Evidence may include personal experience, examples, observations, data, or research — don't demand statistical evidence when the exercise doesn't require it.",
        "common_failure_modes": ["States a claim with no evidence at all", "Gives evidence but never explains why it supports the claim (missing Reasoning)", "Evidence doesn't actually relate to the claim made"],
    },
    "COUNTERARGUMENT": {
        "purpose": "Help speakers demonstrate they can recognize an opposing view without losing their own position.",
        "functions": [
            {"id": "position", "name": "Position", "question": "Did they state their position?"},
            {"id": "other_side", "name": "Other side", "question": "Did they acknowledge a credible alternative perspective?"},
            {"id": "response", "name": "Response", "question": "Did they explain why they still hold their position?"},
        ],
        "minimum_sufficient_structure": "All three are needed — without a genuine other side, this isn't a counterargument exercise, it's just Point/Reason again.",
        "flexibility_rules": "Do not reward hollow phrases like 'some people may disagree' — evaluate whether they genuinely engaged with the alternative view, not whether they gestured at its existence.",
        "common_failure_modes": ["Names an opposing view without actually engaging with it", "Concedes so much ground the original position is abandoned", "The 'other side' offered is a strawman, not a credible alternative"],
    },
    "DEFEND_POSITION": {
        "purpose": "Help speakers defend an idea when challenged.",
        "functions": [
            {"id": "position", "name": "Position", "question": "Is the position clear?"},
            {"id": "reason", "name": "Reason", "question": "Is there a reason for the position?"},
            {"id": "evidence", "name": "Evidence", "question": "Is there supporting evidence or an example?"},
            {"id": "response_to_challenge", "name": "Response to challenge", "question": "Did the speaker respond to the challenge raised, rather than repeating their original point unchanged?"},
        ],
        "minimum_sufficient_structure": "Position + Reason + a genuine Response to the challenge; Evidence strengthens but isn't always essential.",
        "flexibility_rules": "Components may appear in a different order than listed — a good response to a challenge often restates position and reason together.",
        "common_failure_modes": ["Repeats the original point verbatim instead of addressing the challenge", "Becomes defensive rather than engaging with the substance", "Abandons the position entirely rather than qualifying or defending it"],
    },
    "STAR": {
        "purpose": "Help speakers answer behavioral interview questions using a specific example.",
        "functions": [
            {"id": "situation", "name": "Situation", "question": "Does the listener understand the relevant context?"},
            {"id": "task", "name": "Task", "question": "Does the listener understand what needed to be done or what responsibility the speaker had?"},
            {"id": "action", "name": "Action", "question": "Does the speaker explain what THEY personally did?"},
            {"id": "result", "name": "Result", "question": "Does the speaker explain what happened because of their actions?"},
        ],
        "minimum_sufficient_structure": "Situation/Task may be combined or brief; Action deserves the most weight since behavioral interviews are primarily interested in what the candidate actually did; Result can be qualitative.",
        "flexibility_rules": "Situation and Task may be combined. Task may be implicit if responsibility is obvious. Never invent a result the speaker didn't state — a qualitative outcome is valid, but an unstated one is not credited.",
        "common_failure_modes": ["Describes what the team did, not what they personally did", "No result given at all", "Spends most of the answer on situation, barely reaches action"],
    },
    "ELEVATOR_PITCH": {
        "purpose": "Help a speaker communicate an idea quickly to someone with limited attention.",
        "functions": [
            {"id": "problem", "name": "Problem", "question": "What problem or opportunity exists?"},
            {"id": "solution", "name": "Solution", "question": "What are they proposing?"},
            {"id": "value", "name": "Value", "question": "Why should the listener care?"},
            {"id": "ask", "name": "Ask", "question": "What do they want the listener to do next?"},
        ],
        "minimum_sufficient_structure": "Problem + Solution + Value; Ask may be unnecessary if the exercise is only practicing a short introduction, not a real request.",
        "flexibility_rules": "Do not require a literal ask when the context doesn't call for one.",
        "common_failure_modes": ["Leads with the solution before establishing why the problem matters", "No clear value stated — the 'so what' is missing", "Runs out of time before stating the ask, when one is expected"],
    },
    "PRODUCT_PITCH": {
        "purpose": "Help someone explain an idea compellingly without drowning the listener in features.",
        "functions": [
            {"id": "problem", "name": "Problem", "question": "Is the problem understandable?"},
            {"id": "solution", "name": "Solution", "question": "Is the solution connected to the problem?"},
            {"id": "differentiator", "name": "Differentiator", "question": "What makes the solution meaningfully different?"},
            {"id": "value", "name": "Value", "question": "Why does that difference matter?"},
        ],
        "minimum_sufficient_structure": "Problem + Solution + Differentiator; Value can be implied by a strong differentiator but is stronger when stated.",
        "flexibility_rules": "Do not reward unnecessary product jargon or feature lists in place of a real differentiator.",
        "common_failure_modes": ["Lists features instead of naming a differentiator", "Differentiator given but never connected back to why it matters", "Solution doesn't clearly map back to the stated problem"],
    },
    "PROBLEM_SOLVING": {
        "purpose": "Help speakers explain how they approached a problem.",
        "functions": [
            {"id": "problem", "name": "Problem", "question": "What was the problem?"},
            {"id": "analysis", "name": "Analysis", "question": "How did they understand or investigate it?"},
            {"id": "action", "name": "Action", "question": "What did they do?"},
            {"id": "outcome", "name": "Outcome", "question": "What happened?"},
        ],
        "minimum_sufficient_structure": "Problem + Action + Outcome; Analysis strengthens but a simple problem may not need visible investigation.",
        "flexibility_rules": "Overlaps with STAR — when both frameworks could apply, don't evaluate the same element twice under two different names.",
        "common_failure_modes": ["Jumps straight to the action with no problem framing", "No outcome given — the story just stops after the action", "Analysis described is generic, not specific to this problem"],
    },
    "PERSUASION": {
        "purpose": "Help a speaker persuade an audience to care about an issue and consider a proposed solution.",
        "functions": [
            {"id": "problem", "name": "Problem", "question": "Is the issue clear?"},
            {"id": "impact", "name": "Impact", "question": "Does the audience understand why it matters?"},
            {"id": "solution", "name": "Solution", "question": "Is there a proposed response?"},
            {"id": "benefit", "name": "Benefit", "question": "Does the speaker explain what improves if the solution is adopted?"},
        ],
        "minimum_sufficient_structure": "All four are typically needed for genuine persuasion — a problem without stakes (Impact) rarely moves anyone.",
        "flexibility_rules": "Do not confuse emotional intensity with persuasive effectiveness — score whether the functions were served, not how passionately.",
        "common_failure_modes": ["States the problem with no impact/stakes attached", "Proposes a solution with no stated benefit", "Relies on emotional appeal with no substantive Impact or Benefit"],
    },
    "OBJECTION_HANDLING": {
        "purpose": "Help speakers respond to disagreement without becoming defensive or ignoring the actual concern.",
        "functions": [
            {"id": "acknowledge", "name": "Acknowledge", "question": "Did they demonstrate they understood the objection?"},
            {"id": "clarify", "name": "Clarify", "question": "Did they clarify the objection where needed?"},
            {"id": "respond", "name": "Respond", "question": "Did they give a real response?"},
            {"id": "support", "name": "Support", "question": "Did they support the response with reasoning, evidence, or an example?"},
        ],
        "minimum_sufficient_structure": "Acknowledge + Respond + Support; Clarify is only needed when the objection was genuinely ambiguous.",
        "flexibility_rules": "Do not reward empty acknowledgment phrases like 'I understand your concern' — the speaker must actually engage with the substance of the objection.",
        "common_failure_modes": ["Acknowledges the objection but then ignores it and repeats the original pitch", "Gets defensive instead of engaging", "Response given with no supporting reasoning or example"],
    },
    "DIFFICULT_QUESTION": {
        "purpose": "Give speakers a structure for answering questions when they need time to think under pressure.",
        "functions": [
            {"id": "identify", "name": "Identify", "question": "Did they correctly identify what was being asked?"},
            {"id": "answer", "name": "Answer", "question": "Did they provide a clear answer?"},
            {"id": "explain", "name": "Explain", "question": "Did they explain their reasoning?"},
            {"id": "bridge", "name": "Bridge", "question": "If appropriate, did they connect the answer to something relevant?"},
        ],
        "minimum_sufficient_structure": "Identify + Answer + Explain; Bridge is optional and situational.",
        "flexibility_rules": "A brief thoughtful pause before answering should never be penalized — it is preferable to filler. Only penalize a pause if it becomes a stall with no answer following.",
        "common_failure_modes": ["Answers a different question than the one actually asked", "Fills the pause with verbal filler instead of just pausing", "Never actually commits to an answer, stays vague throughout"],
    },
    "STORYTELLING": {
        "purpose": "Help speakers tell a story that has a clear progression rather than simply listing events.",
        "functions": [
            {"id": "setup", "name": "Setup", "question": "Does the listener understand the situation?"},
            {"id": "tension", "name": "Tension", "question": "What problem, challenge, uncertainty, or conflict existed?"},
            {"id": "action", "name": "Action", "question": "What did the person do?"},
            {"id": "change", "name": "Change", "question": "What happened or what changed?"},
        ],
        "minimum_sufficient_structure": "All four — a story without Tension is just a sequence of events, and without Change it has no point.",
        "flexibility_rules": "Do not require dramatic conflict — a small challenge can still make an effective story.",
        "common_failure_modes": ["Lists events in order with no real tension or stakes", "No change/resolution — the story just trails off", "Setup takes up most of the time, story never really gets going"],
    },
    "TEACHING_COMPLEX_IDEA": {
        "purpose": "Help speakers make complex ideas understandable.",
        "functions": [
            {"id": "simple_idea", "name": "Simple idea", "question": "Did they establish the basic idea plainly?"},
            {"id": "breakdown", "name": "Breakdown", "question": "Did they break it into understandable pieces?"},
            {"id": "example", "name": "Example", "question": "Did they make it concrete with an example?"},
            {"id": "check", "name": "Check", "question": "Did they check or anticipate whether the listener could follow?"},
        ],
        "minimum_sufficient_structure": "Simple idea + Breakdown + Example; Check may be omitted when the exercise has no interactive listener.",
        "flexibility_rules": "Check is naturally omitted in a one-way recorded response — don't penalize its absence in that context.",
        "common_failure_modes": ["Jumps into complexity before establishing the simple version", "Breaks it down but never grounds it in a concrete example", "Uses jargon while explaining, undermining the simplification"],
    },
    "EXECUTIVE_COMMUNICATION": {
        "purpose": "Help speakers communicate efficiently when the listener has limited time.",
        "functions": [
            {"id": "bottom_line", "name": "Bottom line", "question": "Did they give the conclusion first?"},
            {"id": "key_points", "name": "Key points", "question": "Did they provide the most important supporting points?"},
            {"id": "implication", "name": "Implication", "question": "Did they explain what the listener should understand, decide, or do as a result?"},
        ],
        "minimum_sufficient_structure": "All three, but briefly — length is not a virtue here.",
        "flexibility_rules": "Do not reward length or thoroughness for its own sake. A short answer containing all three functions outscores a long one that buries them.",
        "common_failure_modes": ["Conclusion arrives last instead of first", "Supporting detail given with no implication — 'so what should I do with this'", "Too many key points, none land clearly"],
    },
    "ANSWER_FOLLOWUP": {
        "purpose": "Help speakers extend their thinking when asked a follow-up, without restarting from scratch or repeating their first answer.",
        "functions": [
            {"id": "answer", "name": "Answer", "question": "Did they directly address the follow-up itself, not just repeat their earlier answer?"},
            {"id": "explanation", "name": "Explanation", "question": "Did they explain their reasoning for this follow-up answer?"},
            {"id": "example", "name": "Example", "question": "Did they ground it with an example where useful?"},
        ],
        "minimum_sufficient_structure": "Answer + Explanation is sufficient; Example strengthens but isn't always necessary for a quick follow-up.",
        "flexibility_rules": "The follow-up answer should connect to and build on the first answer, not contradict it without acknowledgment or restart the topic from zero.",
        "common_failure_modes": ["Repeats the original answer instead of engaging with the new question", "Restarts from scratch as if the first answer didn't happen", "Contradicts the earlier answer with no acknowledgment of the shift"],
    },
}

CHALLENGE_TYPES = {
    "answer_direct_question": "DIRECT_ANSWER",
    "explain_an_idea": "WHAT_WHY_EXAMPLE",
    "make_a_point": "POINT_REASON_EVIDENCE",
    "answer_the_unexpected": "SPONTANEOUS_ANSWER",
    "answer_a_question": "ANSWER_REASON",
    "make_an_argument": "CLAIM_EVIDENCE_REASONING",
    "acknowledge_other_side": "COUNTERARGUMENT",
    "defend_your_position": "DEFEND_POSITION",
    "answer_interview_question": "STAR",
    "give_elevator_pitch": "ELEVATOR_PITCH",
    "pitch_a_product": "PRODUCT_PITCH",
    "explain_problem_solving": "PROBLEM_SOLVING",
    "persuade_someone": "PERSUASION",
    "handle_an_objection": "OBJECTION_HANDLING",
    "answer_a_difficult_question": "DIFFICULT_QUESTION",
    "answer_a_followup": "ANSWER_FOLLOWUP",
    "tell_a_story": "STORYTELLING",
    "teach_something_complex": "TEACHING_COMPLEX_IDEA",
    "communicate_like_an_executive": "EXECUTIVE_COMMUNICATION",
}


def get_framework(challenge_type: str) -> dict:
    framework_name = CHALLENGE_TYPES[challenge_type]
    framework = FRAMEWORKS[framework_name]
    return {
        "challenge_type": challenge_type,
        "framework_name": framework_name,
        **framework,
    }