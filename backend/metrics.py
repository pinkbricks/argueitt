"""
Rubric scoring via Gemini.

Takes: the level's prompt/question, the transcript, and the already-computed
delivery metrics (from delivery_metrics.py), and asks Gemini to judge the
things that need understanding — not the things we already counted.

The model must return evidence (a quote/paraphrase) before each score, so
disagreements later are diagnosable: was the rubric wrong, or the model.
"""

import json
from google import genai
from google.genai import types
import os

from dotenv import load_dotenv


load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')

MODEL = "gemini-3.6-flash"  # fast + cheap; move to a stronger model if scores feel unreliable
MODEL_VERSION_TAG = "rubric-v1"  # bump this whenever the rubric/prompt changes — store alongside scores

client = genai.Client(api_key=api_key)

"""
Rubric scoring via Gemini.

Takes: the level's prompt/question, the transcript, and the already-computed
delivery metrics (from delivery_metrics.py), and asks Gemini to judge the
things that need understanding — not the things we already counted.

The model must return evidence (a quote/paraphrase) before each score, so
disagreements later are diagnosable: was the rubric wrong, or the model.
"""


# --- Level rubric definitions -------------------------------------------
# Each level lists the criteria the LLM should judge. Keep these short:
# 3-4 criteria per level, each with a plain-language definition and a
# 0/1/2 scale. `gate` = True means a 0 here fails the attempt regardless
# of total score.

LEVEL_RUBRICS = {
    1: {
        "skill": "Directness",
        "criteria": [
            {
                "id": "answered_question",
                "gate": True,
                "definition": (
                    "Did the response directly answer the question asked? "
                    "0 = did not answer it, 1 = partially answered or implied an answer, "
                    "2 = clearly and directly answered it."
                ),
            },
            {
                "id": "on_topic",
                "gate": False,
                "definition": (
                    "0 = mostly wandered off the question, 1 = some tangents but returned to the point, "
                    "2 = stayed relevant throughout."
                ),
            },
            {
                "id": "no_circling",
                "gate": False,
                "definition": (
                    "0 = repeated the same point 3+ times without adding anything new, "
                    "1 = repeated the point once, 2 = each sentence added something new."
                ),
            },
        ],
    },
    2: {
        "skill": "Clarity",
        "criteria": [
            {
                "id": "understandable_to_novice",
                "gate": True,
                "definition": (
                    "Could someone with no background in the topic follow this explanation? "
                    "0 = confusing or assumes background knowledge, 1 = mostly clear with some jumps, "
                    "2 = clear and easy to follow for a novice."
                ),
            },
            {
                "id": "jargon_control",
                "gate": False,
                "definition": (
                    "0 = heavy unexplained jargon, 1 = some jargon but mostly explained, "
                    "2 = plain language or jargon is defined when used."
                ),
            },
            {
                "id": "logical_flow",
                "gate": False,
                "definition": (
                    "0 = ideas presented out of order or disconnected, 1 = mostly logical with minor jumps, "
                    "2 = clear logical progression from one idea to the next."
                ),
            },
        ],
    },
    3: {
        "skill": "Developing an idea",
        "criteria": [
            {
                "id": "clear_position",
                "gate": True,
                "definition": (
                    "0 = no clear position stated, 1 = position is implied but not stated plainly, "
                    "2 = position is stated plainly and early."
                ),
            },
            {
                "id": "reasoning",
                "gate": False,
                "definition": (
                    "0 = no reason given for the position, 1 = a reason is given but weak or vague, "
                    "2 = a clear, specific reason supports the position."
                ),
            },
            {
                "id": "supporting_example",
                "gate": False,
                "definition": (
                    "0 = no example or evidence, 1 = a vague or generic example, "
                    "2 = a specific, concrete example or piece of evidence."
                ),
            },
            {
                "id": "structure",
                "gate": False,
                "definition": (
                    "Does the answer roughly follow Position -> Reason -> Example? "
                    "0 = no discernible structure, 1 = elements present but disordered, "
                    "2 = clear structure, easy to follow."
                ),
            },
        ],
    },
    4: {
        "skill": "Spontaneous response",
        "criteria": [
            {
                "id": "coherent_answer",
                "gate": True,
                "definition": (
                    "0 = froze, gave up, or answer doesn't hold together, "
                    "1 = produced an answer but it wanders or loses the thread, "
                    "2 = coherent answer that holds together start to finish."
                ),
            },
            {
                "id": "answered_actual_question",
                "gate": True,
                "definition": (
                    "0 = answered a different question than the one asked, "
                    "1 = partially addressed the actual question, "
                    "2 = clearly addressed the actual question asked."
                ),
            },
            {
                "id": "recovered_quickly",
                "gate": False,
                "definition": (
                    "Judge using both the transcript and the pause data provided. "
                    "0 = long search for an answer before starting, 1 = brief hesitation then recovered, "
                    "2 = started promptly and kept moving."
                ),
            },
        ],
    },
}


SYSTEM_INSTRUCTIONS = """You are scoring a spoken response for a communication-skills app.
You will be given: the question/prompt the user was responding to, the verbatim transcript
of their spoken answer, some already-computed delivery metrics (filler words, pauses, pace),
and a rubric of criteria to judge.

Rules:
- Score ONLY the criteria listed. Do not invent new criteria.
- For each criterion, first give a short "evidence" string: a direct quote or close paraphrase
  from the transcript that justifies your score. Then give the integer score (0, 1, or 2).
- Do not count filler words, pace, or pauses yourself — that's already computed and provided
  to you for context only (e.g. to judge whether a pause reflects genuine hesitation).
- Be specific in evidence. Do not write generic evidence like "the answer was unclear" —
  quote or closely paraphrase the actual words that show it.
- Also return:
  - "strongest_moment": one short quote/paraphrase of the best part of the answer
  - "weakest_criterion_id": the id of the lowest-scoring criterion (pick one if tied,
    prioritizing gate criteria)
  - "feedback_pointer": ONE sentence of concrete, actionable coaching tied to the
    weakest_criterion_id, quoting or referencing what they actually said. Do not write
    generic advice like "try to be more direct" — ground it in their specific answer.
- Return ONLY valid JSON matching the schema. No prose outside the JSON.
"""


def _build_response_schema(criteria: list) -> dict:
    criterion_props = {
        c["id"]: {
            "type": "object",
            "properties": {
                "evidence": {"type": "string"},
                "score": {"type": "integer"},  # model instructed to use 0/1/2; validated in Python below
            },
            "required": ["evidence", "score"],
        }
        for c in criteria
    }
    return {
        "type": "object",
        "properties": {
            "criteria": {
                "type": "object",
                "properties": criterion_props,
                "required": [c["id"] for c in criteria],
            },
            "strongest_moment": {"type": "string"},
            "weakest_criterion_id": {"type": "string"},
            "feedback_pointer": {"type": "string"},
        },
        "required": ["criteria", "strongest_moment", "weakest_criterion_id", "feedback_pointer"],
    }


def score_response(level_id: int, prompt_text: str, transcript: str, delivery_metrics: dict) -> dict:
    """
    Returns a dict:
    {
        "level_id": int,
        "model_version": str,
        "criteria": {criterion_id: {"evidence": str, "score": int}, ...},
        "gate_passed": bool,
        "total_score": int,          # 0-100, scaled from raw criteria points
        "passed": bool,
        "strongest_moment": str,
        "weakest_criterion_id": str,
        "feedback_pointer": str,
    }
    """
    rubric = LEVEL_RUBRICS[level_id]
    criteria = rubric["criteria"]

    user_content = f"""
QUESTION / PROMPT GIVEN TO USER:
{prompt_text}

TRANSCRIPT (verbatim, includes fillers/false starts — ignore these for judgment, they're not part of what you're scoring):
{transcript}

DELIVERY METRICS (for context only, already computed):
{json.dumps(delivery_metrics, indent=2)}

RUBRIC — skill being tested: {rubric['skill']}
Criteria to score:
{json.dumps(criteria, indent=2)}

Score each criterion as instructed and return the JSON.
"""

    response = client.models.generate_content(
        model=MODEL,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTIONS,
            temperature=0.2,  # low temperature for scoring consistency
            response_mime_type="application/json",
            response_schema=_build_response_schema(criteria),
        ),
    )

    result = json.loads(response.text)

    # --- validate score range (schema can't enforce enum here, so check in Python) ---
    for c in criteria:
        s = result["criteria"][c["id"]]["score"]
        if s not in (0, 1, 2):
            raise ValueError(
                f"Model returned out-of-range score {s} for criterion '{c['id']}'. "
                f"Full response: {result}"
            )

    # --- gate check ---
    gate_ids = [c["id"] for c in criteria if c["gate"]]
    gate_passed = all(result["criteria"][gid]["score"] >= 1 for gid in gate_ids)

    # --- scale to 0-100 ---
    max_possible = len(criteria) * 2
    raw_total = sum(result["criteria"][c["id"]]["score"] for c in criteria)
    total_score = round((raw_total / max_possible) * 100)

    passed = gate_passed and total_score >= 70  # matches roadmap's default pass_threshold

    return {
        "level_id": level_id,
        "model_version": MODEL_VERSION_TAG,
        "criteria": result["criteria"],
        "gate_passed": gate_passed,
        "total_score": total_score,
        "passed": passed,
        "strongest_moment": result["strongest_moment"],
        "weakest_criterion_id": result["weakest_criterion_id"],
        "feedback_pointer": result["feedback_pointer"],
    }


if __name__ == "__main__":
    # Manual test using your cancel-culture transcript + its computed metrics
    sample_transcript = (
        """That's when your mind is at rest. That's why I think um content you can grasp content easily and you know it as a thing in your mind. So and it should start early correctly. Technical work. Because when you you get structure of from morning until So that's why That's good I think."""
    )
    sample_metrics = {

  "word_count": 54,
  "duration_sec": 49.4,
  "words_per_minute": 65.6,
  "filler_word_count": 2,
  "filler_words_found": [
    "um",
    "you know"
  ],
  "long_pause_count": 10,
  "longest_pause_sec": 7.0,
  "pause_details": [
    {
      "after_word": "um",
      "gap_sec": 2.0,
      "at_sec": 11.0
    },
    {
      "after_word": "mind.",
      "gap_sec": 1.8,
      "at_sec": 20.7
    },
    {
      "after_word": "So",
      "gap_sec": 2.3,
      "at_sec": 22.5
    },
    {
      "after_word": "and",
      "gap_sec": 3.9,
      "at_sec": 24.8
    },
    {
      "after_word": "correctly.",
      "gap_sec": 7.0,
      "at_sec": 30.6
    },
    {
      "after_word": "work.",
      "gap_sec": 6.8,
      "at_sec": 37.9
    },
    {
      "after_word": "structure",
      "gap_sec": 1.7,
      "at_sec": 46.0
    },
    {
      "after_word": "of",
      "gap_sec": 1.5,
      "at_sec": 47.7
    },
    {
      "after_word": "until",
      "gap_sec": 2.6,
      "at_sec": 50.2
    },
    {
      "after_word": "why",
      "gap_sec": 2.2,
      "at_sec": 53.1
    }
  ],
  "time_to_first_content_word_sec": 0.0
}


    result = score_response(
        level_id=1,
        prompt_text="Should schools start later in the morning?",
        transcript=sample_transcript,
        delivery_metrics=sample_metrics,
    )
    print(json.dumps(result, indent=2))