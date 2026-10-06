"""
Function-based scoring via Gemini.

Takes: the challenge type, the prompt/question, the transcript, and the
already-computed delivery metrics (from delivery_metrics.py), and asks
Gemini to judge whether the response served the underlying COMMUNICATION
FUNCTIONS of the relevant framework (from frameworks.py) — not whether it
matched a rigid template. See frameworks.py for the function definitions.

The model must return evidence (a quote/paraphrase) before each score, so
disagreements later are diagnosable: was the framework wrong, or the model.
"""

import json
from google import genai
from google.genai import types

from framework import get_framework

MODEL = "gemini-3.6-flash"  # fast + cheap; move to a stronger model if scores feel unreliable
MODEL_VERSION_TAG = "framework-v4-outside-knowledge-guard"  # bump whenever framework defs or prompt change

PASS_THRESHOLD = 70


SYSTEM_INSTRUCTIONS = """You are a communication coach scoring a spoken response for a
skills-training app. Your job is not just to grade the answer — it's to make the person
visibly better next time. Someone who reads your feedback should know exactly what to say
differently, not just what they did wrong.

You are evaluating whether the response served the underlying COMMUNICATION FUNCTIONS of
a framework — not whether it followed a rigid template. Follow these rules exactly:

- Evaluate the underlying communication functions, not exact structural ordering.
- Functions may be combined, reordered, or expressed implicitly. A function can be served
  in one word or one clause — it doesn't need its own sentence.
- Do not penalize the speaker for not explicitly labeling or separating each function.
- Only mark a function as missing/weak when its absence makes the answer MATERIALLY
  weaker — not just structurally incomplete. If the answer works fine without it, don't
  ding it.
- Every criticism must be supported by evidence from the transcript — a direct quote or
  close paraphrase. Do not write generic evidence like "this part was unclear."
- Do not infer events, actions, reasoning, or outcomes the speaker did not actually state.
  If something is ambiguous, treat it as not established — don't give credit for what they
  probably meant.
- Do not count filler words, pace, or pauses yourself — that's already computed and given
  to you for context only (e.g. to judge whether a pause reflects genuine hesitation).
- You may recognize the framework name from general knowledge (e.g. STAR, elevator pitch).
  Ignore any conventions you associate with that name if they are not in the function
  definitions given below — for example, if you know STAR is often taught as requiring a
  quantified result, but this task's Result function does not require a number, do not
  penalize a qualitative outcome. Score only against the functions and their definitions
  as given here, not against outside conventions for that framework's name.

For each function, return:
- "evidence": a direct quote or close paraphrase showing how (or whether) it was served.
  If genuinely absent, say so plainly rather than stretching for a quote.
- "score": 0 (missing and it matters), 1 (present but weak/thin), or 2 (clearly served).

Also return:
- "strongest_moment": one short quote/paraphrase of the best part of the answer, and
  briefly why it worked. People need to know what to repeat, not just what to stop doing.
- "weakest_function_id": the id of the lowest-scoring function (pick one if tied).
- "feedback_pointer": coaching on the weakest function, written as three short parts —
  1) what happened, quoting their actual words,
  2) why it matters for this framework, one clause,
  3) a concrete rewritten version of THEIR OWN sentence or moment that fixes it — an
  actual line they could say instead, built from what they were already trying to say.
  Do not write vague advice like "try to be more direct." Show the fix.
- "next_focus": one short, concrete instruction for the NEXT attempt — not a summary of
  this one (e.g. "State your position in the first sentence, before explaining why.").

Return ONLY valid JSON matching the schema. No prose outside the JSON.
"""


def _build_response_schema(functions: list) -> dict:
    function_props = {
        f["id"]: {
            "type": "object",
            "properties": {
                "evidence": {"type": "string"},
                "score": {"type": "integer"},  # instructed 0/1/2; validated in Python below
            },
            "required": ["evidence", "score"],
        }
        for f in functions
    }
    return {
        "type": "object",
        "properties": {
            "functions": {
                "type": "object",
                "properties": function_props,
                "required": [f["id"] for f in functions],
            },
            "strongest_moment": {"type": "string"},
            "weakest_function_id": {"type": "string"},
            "feedback_pointer": {"type": "string"},
            "next_focus": {"type": "string"},
        },
        "required": [
            "functions", "strongest_moment", "weakest_function_id",
            "feedback_pointer", "next_focus",
        ],
    }


async def score_response(
    client: genai.Client,
    challenge_type: str,
    prompt_text: str,
    transcript: str,
    delivery_metrics: dict,
    previous_next_focus: str = None,
) -> dict:
    """
    Returns a dict:
    {
        "challenge_type": str,
        "framework_name": str,
        "model_version": str,
        "functions": {function_id: {"evidence": str, "score": int}, ...},
        "total_score": int,      # 0-100, scaled from raw function points
        "passed": bool,
        "strongest_moment": str,
        "weakest_function_id": str,
        "feedback_pointer": str,
        "next_focus": str,
    }

    previous_next_focus: the "next_focus" returned by this user's previous attempt
    at this challenge type, if any. When given, the model checks whether they acted
    on it — this is what makes feedback feel like it's tracking progress across
    attempts, not grading each one in isolation.
    """
    fw = get_framework(challenge_type)
    functions = fw["functions"]

    continuity_block = ""
    if previous_next_focus:
        continuity_block = f"""
PREVIOUS ATTEMPT'S FOCUS FOR THIS USER:
"{previous_next_focus}"
In your feedback_pointer or strongest_moment, briefly note whether they visibly acted on
this or not — this is what makes coaching feel continuous instead of a fresh grade each time.
"""

    user_content = f"""
CHALLENGE TYPE: {fw['challenge_type']}
FRAMEWORK: {fw['framework_name']}
FRAMEWORK PURPOSE: {fw['purpose']}

QUESTION / PROMPT GIVEN TO USER:
{prompt_text}

TRANSCRIPT (verbatim, includes fillers/false starts — ignore these for function judgment):
{transcript}

DELIVERY METRICS (for context only, already computed — do not recompute):
{json.dumps(delivery_metrics, indent=2)}
{continuity_block}
COMMUNICATION FUNCTIONS TO EVALUATE:
{json.dumps(functions, indent=2)}

Score each function per the rules and return the JSON.
"""

    response = await client.aio.models.generate_content(
        model=MODEL,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTIONS,
            temperature=0.2,  # low temperature for scoring consistency
            response_mime_type="application/json",
            response_schema=_build_response_schema(functions),
        ),
    )

    result = json.loads(response.text)

    # --- validate score range (schema can't enforce enum here, so check in Python) ---
    for f in functions:
        s = result["functions"][f["id"]]["score"]
        if s not in (0, 1, 2):
            raise ValueError(
                f"Model returned out-of-range score {s} for function '{f['id']}'. "
                f"Full response: {result}"
            )

    # --- scale to 0-100 (no gates: pass/fail is purely the total score) ---
    max_possible = len(functions) * 2
    raw_total = sum(result["functions"][f["id"]]["score"] for f in functions)
    total_score = round((raw_total / max_possible) * 100)

    passed = total_score >= PASS_THRESHOLD

    return {
        "challenge_type": fw["challenge_type"],
        "framework_name": fw["framework_name"],
        "model_version": MODEL_VERSION_TAG,
        "functions": result["functions"],
        "total_score": total_score,
        "passed": passed,
        "strongest_moment": result["strongest_moment"],
        "weakest_function_id": result["weakest_function_id"],
        "feedback_pointer": result["feedback_pointer"],
        "next_focus": result["next_focus"],
    }


if __name__ == "__main__":
    import asyncio
    import os

    from dotenv import load_dotenv

    load_dotenv()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    sample_transcript = (
        "That's when your mind is at rest. That's why I think um content you can grasp "
        "content easily and you know it as a thing in your mind. So and it should start "
        "early correctly. Technical work. Because when you you get structure of from "
        "morning until So that's why That's good I think."
    )
    sample_metrics = {
        "word_count": 54,
        "duration_sec": 49.4,
        "words_per_minute": 65.6,
        "filler_word_count": 2,
        "filler_words_found": ["um", "you know"],
        "long_pause_count": 10,
        "longest_pause_sec": 7.0,
        "time_to_first_content_word_sec": 0.0,
    }

    result = asyncio.run(score_response(
        client,
        challenge_type="answer_direct_question",
        prompt_text="Should schools start later in the morning?",
        transcript=sample_transcript,
        delivery_metrics=sample_metrics,
    ))
    print(json.dumps(result, indent=2))