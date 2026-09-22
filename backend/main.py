import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, Field

load_dotenv()

MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.6-flash')
MAX_AUDIO_BYTES = 10 * 1024 * 1024
TRANSCRIPTS_FILE = Path(__file__).parent / 'data' / 'transcripts.json'

app = FastAPI()
store_lock = asyncio.Lock()


class Filler(BaseModel):
    word: str
    count: int


class StructurePart(BaseModel):
    part: str = Field(description='One of: Opening, Position, Supporting points, Conclusion')
    present: bool
    note: str = Field(description='One short sentence on how well they did it, or what is missing')


class Feedback(BaseModel):
    filler_count: int
    filler_breakdown: list[Filler]
    time_to_first_point_seconds: float = Field(
        description='Seconds from the start of the recording until the speaker first makes an actual claim about the topic'
    )
    first_point: str = Field(description='The first real point they made, quoted or closely paraphrased')
    structure: list[StructurePart]
    structure_summary: str
    score: int = Field(ge=1, le=10, description='Overall score from 1 to 10')
    summary: str
    strengths: list[str]
    improvements: list[str] = Field(description='Concrete, actionable pointers for the next attempt')
    counter_argument: str
    stronger_opening: str


class TranscriptResult(BaseModel):
    id: str
    transcript: str


TRANSCRIBE_PROMPT = """Transcribe only the speech that is actually audible in this recording, in English.
Write exactly what was said, keeping filler words (um, uh, er, ah, like, you know, I mean), repeated words and
false starts. Do not correct grammar, summarise, complete sentences or add commentary.
Never invent or guess content: if a part is unclear write [unclear], and if there is no intelligible speech
return an empty string. Return only the transcript text."""

ANALYSE_PROMPT = """You are a sharp, encouraging debate coach analysing a 60-second spoken argument.
The speaker was randomly assigned the side "{side}" on the topic: "{topic}".

You are given the recording and its verbatim transcript (fillers included):
{transcript}

Analyse the speech yourself, using the transcript for content and the audio for timing and delivery:
1. filler_count and filler_breakdown: count every filler in the transcript. Only count "like", "so",
   "actually" etc. when used as filler, not as real words. The breakdown must sum to filler_count.
2. time_to_first_point_seconds: seconds from the start of the audio until they state their first real claim
   about the topic (greetings, throat clearing, restating the topic and filler do not count). first_point is that claim.
3. structure: assess exactly four parts in this order: Opening, Position, Supporting points, Conclusion.
   Mark whether each is present and add a one-sentence note. structure_summary is a one-sentence overall verdict.
4. score (1-10), summary, strengths, and improvements. improvements are concrete pointers for the next attempt,
   each tied to something specific they said or did. Also judge whether they stayed on their assigned side.
5. counter_argument is the strongest point the opposing side would make. stronger_opening is a rewritten first sentence.
Keep every list item to one or two sentences. If the transcript is empty, say so in summary,
set counts to 0 and score to 1."""


def audio_part(data: bytes, content_type: str | None) -> types.Part:
    mime = (content_type or 'audio/webm').split(';')[0]
    return types.Part.from_bytes(data=data, mime_type=mime)


async def read_audio(audio: UploadFile) -> bytes:
    data = await audio.read()
    if not data:
        raise HTTPException(400, 'Empty audio')
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(413, 'Audio too large')
    return data


async def generate(parts: list, config: types.GenerateContentConfig | None = None):
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise HTTPException(500, 'GEMINI_API_KEY is not set')
    client = genai.Client(api_key=api_key)
    for attempt in range(3):
        try:
            return await client.aio.models.generate_content(
                model=MODEL, contents=parts, config=config
            )
        except genai_errors.ServerError:
            await asyncio.sleep(1 + attempt)
        except Exception as exc:
            raise HTTPException(502, f'Gemini request failed: {type(exc).__name__}') from exc
    raise HTTPException(503, 'Gemini is busy, try again in a moment')


def load_records() -> list[dict]:
    if not TRANSCRIPTS_FILE.exists():
        return []
    return json.loads(TRANSCRIPTS_FILE.read_text())


def save_records(records: list[dict]) -> None:
    TRANSCRIPTS_FILE.parent.mkdir(exist_ok=True)
    tmp = TRANSCRIPTS_FILE.with_suffix('.tmp')
    tmp.write_text(json.dumps(records, indent=2, ensure_ascii=False))
    tmp.replace(TRANSCRIPTS_FILE)


@app.get('/')
def root():
    return {'status': 'ok'}


@app.post('/api/transcribe', response_model=TranscriptResult)
async def transcribe(
    topic: str = Form(...),
    side: str = Form(...),
    audio: UploadFile = File(...),
):
    data = await read_audio(audio)
    response = await generate(
        [TRANSCRIBE_PROMPT, audio_part(data, audio.content_type)],
        types.GenerateContentConfig(temperature=0),
    )
    transcript = (response.text or '').strip()

    record = {
        'id': uuid.uuid4().hex,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'topic': topic,
        'side': side,
        'transcript': transcript,
        'audio_bytes': len(data),
        'audio_type': audio.content_type,
    }
    async with store_lock:
        records = load_records()
        records.append(record)
        save_records(records)
    return TranscriptResult(id=record['id'], transcript=transcript)


@app.post('/api/analyze', response_model=Feedback)
async def analyze(
    transcript_id: str = Form(...),
    audio: UploadFile = File(...),
):
    async with store_lock:
        record = next((r for r in load_records() if r['id'] == transcript_id), None)
    if record is None:
        raise HTTPException(404, 'Transcript not found')

    data = await read_audio(audio)
    prompt = ANALYSE_PROMPT.format(
        topic=record['topic'],
        side=record['side'].upper(),
        transcript=record['transcript'] or '(no speech detected)',
    )
    response = await generate(
        [prompt, audio_part(data, audio.content_type)],
        types.GenerateContentConfig(
            response_mime_type='application/json',
            response_schema=Feedback,
        ),
    )
    if not isinstance(response.parsed, Feedback):
        raise HTTPException(502, 'Gemini returned an unexpected response')
    return response.parsed



from google import genai

client = genai.Client()

YOUTUBE_URL = "https://www.youtube.com/watch?v=ku-N-eS1lgM"

prompt = """
  Process the audio file and generate a detailed transcription.
    Write exactly what was said, keeping filler words (um, uh, er, ah, like, you know, I mean), repeated words and
    false starts. Do not correct grammar, summarise, complete sentences or add commentary.
    Never invent or guess content: if a part is unclear write [unclear], and if there is no intelligible speech
    return an empty string. Return only the transcript text.
"""

response_schema = {
    "type": "object",
    "properties": {
        "transcript": {"type": "string"},
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "speaker": {"type": "string"},
                    "timestamp": {"type": "string"},
                    "content": {"type": "string"},
                    "language": {"type": "string"},
                    "emotion": {
                        "type": "string",
                        "enum": ["happy", "sad", "angry", "neutral"]
                    }
                },
                "required": ["speaker", "timestamp", "content", "emotion"]
            }
        }
    },
    "required": ["summary", "segments"]
}

interaction = client.interactions.create(
    model="gemini-3.8-flash",
    input=[
        {"type": "video", "uri": YOUTUBE_URL, "mime_type": "video/mp4"},
        {"type": "text", "text": prompt}
    ],
    response_format=response_schema,
)

print(interaction.output_text)
