import asyncio
import json
import logging
import os
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from google import genai
from google.genai import errors as genai_errors
from pydantic import BaseModel

from framework import get_framework
from metrics import score_response
from stats import DeliveryMetrics, compute_delivery_metrics
from transcript import transcribe_words

load_dotenv()

logger = logging.getLogger('uvicorn.error')

MAX_AUDIO_BYTES = 20 * 1024 * 1024
TRANSCRIPTS_FILE = Path(__file__).parent / 'data' / 'transcripts.json'

# Argueitt gives a random topic + side with zero prep time, so it's scored
# against the "answer_the_unexpected" framework (coherence, on-topic, quick recovery).
DEFAULT_CHALLENGE_TYPE = 'answer_the_unexpected'

app = FastAPI()
store_lock = asyncio.Lock()


class TranscriptResult(BaseModel):
    id: str
    transcript: str


class FunctionResult(BaseModel):
    evidence: str
    score: int


class DeliveryMetricsOut(BaseModel):
    word_count: int
    duration_sec: float
    words_per_minute: float
    filler_word_count: int
    filler_words_found: list[str]
    long_pause_count: int
    longest_pause_sec: float
    pause_details: list[dict]
    time_to_first_content_word_sec: float


class AnalyzeResult(BaseModel):
    challenge_type: str
    framework_name: str
    model_version: str
    functions: dict[str, FunctionResult]
    total_score: int
    passed: bool
    strongest_moment: str
    weakest_function_id: str
    feedback_pointer: str
    next_focus: str
    delivery_metrics: DeliveryMetricsOut
    transcript: str


def get_client() -> genai.Client:
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise HTTPException(500, 'GEMINI_API_KEY is not set')
    return genai.Client(api_key=api_key)


async def with_retries(coro_fn):
    for attempt in range(3):
        try:
            return await coro_fn()
        except genai_errors.ServerError:
            await asyncio.sleep(1 + attempt)
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception('Gemini call failed')
            raise HTTPException(502, f'Gemini request failed: {type(exc).__name__}: {exc}') from exc
    raise HTTPException(503, 'Gemini is busy, try again in a moment')


async def read_audio(audio: UploadFile) -> bytes:
    data = await audio.read()
    if not data:
        raise HTTPException(400, 'Empty audio')
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(413, 'Audio too large')
    return data


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
    client = get_client()
    transcript, words = await with_retries(
        lambda: transcribe_words(client, data, audio.content_type)
    )

    record = {
        'id': uuid.uuid4().hex,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'topic': topic,
        'side': side,
        'transcript': transcript,
        'words': words,
        'audio_bytes': len(data),
        'audio_type': audio.content_type,
    }
    async with store_lock:
        records = load_records()
        records.append(record)
        save_records(records)
    return TranscriptResult(id=record['id'], transcript=transcript)


@app.post('/api/analyze', response_model=AnalyzeResult)
async def analyze(transcript_id: str = Form(...), previous_next_focus: str = Form('')):
    async with store_lock:
        record = next((r for r in load_records() if r['id'] == transcript_id), None)
    if record is None:
        raise HTTPException(404, 'Transcript not found')

    framework_name = get_framework(DEFAULT_CHALLENGE_TYPE)['framework_name']
    words = record.get('words') or []

    if not words:
        empty_metrics = DeliveryMetrics(0, 0.0, 0.0, 0, [], 0, 0.0, [], 0.0)
        return AnalyzeResult(
            challenge_type=DEFAULT_CHALLENGE_TYPE,
            framework_name=framework_name,
            model_version='n/a',
            functions={},
            total_score=0,
            passed=False,
            strongest_moment='',
            weakest_function_id='',
            feedback_pointer='No speech was detected in the recording — try again and speak as soon as the countdown ends.',
            next_focus='',
            delivery_metrics=DeliveryMetricsOut(**asdict(empty_metrics)),
            transcript='',
        )

    delivery_metrics = compute_delivery_metrics(words)
    prompt_text = f"Argue {record['side'].upper()} on: {record['topic']}"
    client = get_client()
    result = await with_retries(
        lambda: score_response(
            client,
            DEFAULT_CHALLENGE_TYPE,
            prompt_text,
            record['transcript'],
            asdict(delivery_metrics),
            previous_next_focus=previous_next_focus or None,
        )
    )

    return AnalyzeResult(
        challenge_type=result['challenge_type'],
        framework_name=result['framework_name'],
        model_version=result['model_version'],
        functions=result['functions'],
        total_score=result['total_score'],
        passed=result['passed'],
        strongest_moment=result['strongest_moment'],
        weakest_function_id=result['weakest_function_id'],
        feedback_pointer=result['feedback_pointer'],
        next_focus=result['next_focus'],
        delivery_metrics=DeliveryMetricsOut(**asdict(delivery_metrics)),
        transcript=record['transcript'],
    )
