import asyncio
import json
import logging
import os
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from starlette.middleware.sessions import SessionMiddleware
from google import genai
from google.genai import errors as genai_errors
from pydantic import BaseModel

import auth
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

# Signed, HttpOnly cookie. Vite proxies /api to this server, so dev is
# same-origin and the cookie needs no CORS handling; keep the two behind one
# origin in production and it stays that way.
SESSION_SECRET = os.getenv('SESSION_SECRET')
if not SESSION_SECRET:
    raise RuntimeError('SESSION_SECRET is not set — see backend/.env')

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie='argueitt_session',
    https_only=os.getenv('ENV') == 'production',
    same_site='lax',
    max_age=60 * 60 * 24 * 30,
)


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


class GoogleCredential(BaseModel):
    credential: str


class SessionUser(BaseModel):
    id: str
    email: str
    name: str
    picture: str


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


def current_user_id(request: Request) -> str | None:
    """The signed-in user's id, or None — signing in is optional."""
    return request.session.get('user_id')


@app.post('/api/auth/google', response_model=SessionUser)
async def sign_in_with_google(body: GoogleCredential, request: Request):
    try:
        claims = auth.verify_credential(body.credential)
    except auth.AuthError as exc:
        logger.warning('Google sign-in rejected: %s', exc)
        raise HTTPException(status_code=401, detail=str(exc))

    user = await auth.upsert_user(claims)
    # A fresh session id on sign-in, so a pre-login cookie can't be replayed.
    request.session.clear()
    request.session['user_id'] = user['id']
    return SessionUser(**auth.public_user(user))


@app.get('/api/auth/me')
async def me(request: Request):
    user_id = current_user_id(request)
    if not user_id:
        return {'user': None}
    user = next((u for u in auth.load_users() if u['id'] == user_id), None)
    if user is None:
        request.session.clear()
        return {'user': None}
    return {'user': auth.public_user(user)}


@app.post('/api/auth/sign-out')
async def sign_out(request: Request):
    request.session.clear()
    return {'status': 'ok'}


async def remember_attempt(
    request: Request,
    topic: str,
    side: str,
    transcript: str,
    words: list,
    audio: bytes,
    audio_type: str | None,
    analysis: dict,
) -> None:
    """
    Saves a finished attempt for the Progress page.

    Best-effort on purpose: the feedback has already been produced by the time
    this runs, so a store that can't be written — a read-only filesystem on a
    serverless host, a full disk — costs the user their history, not their
    result. It is logged and swallowed rather than failing the request.
    """
    record = {
        'id': uuid.uuid4().hex,
        'created_at': datetime.now(timezone.utc).isoformat(),
        # None for signed-out attempts; Progress needs this to tell one
        # person's attempts from another's.
        'user_id': current_user_id(request),
        'topic': topic,
        'side': side,
        'transcript': transcript,
        'words': words,
        'audio_bytes': len(audio),
        'audio_type': audio_type,
        'analysis': {**analysis, 'analysed_at': datetime.now(timezone.utc).isoformat()},
    }

    try:
        async with store_lock:
            records = load_records()
            records.append(record)
            save_records(records)
    except OSError as exc:
        logger.warning('Could not save attempt (feedback was still returned): %s', exc)


def attempt_summary(record: dict) -> dict:
    """An attempt as the Progress page needs it — no word timings, no audio."""
    return {
        'id': record['id'],
        'created_at': record['created_at'],
        'topic': record['topic'],
        'side': record['side'],
        'transcript': record.get('transcript', ''),
        'analysis': record.get('analysis'),
    }


@app.get('/api/attempts')
async def attempts(request: Request):
    user_id = current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail='Sign in to see your attempts')

    async with store_lock:
        records = load_records()

    mine = [r for r in records if r.get('user_id') == user_id]
    mine.sort(key=lambda r: r.get('created_at', ''), reverse=True)
    return {'attempts': [attempt_summary(r) for r in mine]}


@app.post('/api/analyze', response_model=AnalyzeResult)
async def analyze(
    request: Request,
    topic: str = Form(...),
    side: str = Form(...),
    audio: UploadFile = File(...),
    previous_next_focus: str = Form(''),
):
    """
    Transcribes and scores one attempt in a single request.

    This used to be two endpoints: /api/transcribe wrote a record, and
    /api/analyze read the word timings back out of it. That handed off state
    through the transcript store, which only works where the two calls share a
    filesystem — on a serverless host they are separate invocations and the
    second one can't find what the first wrote. Keeping it in one request means
    the feedback loop needs no storage at all; saving the attempt afterwards is
    for Progress, and is allowed to fail.
    """
    data = await read_audio(audio)
    client = get_client()
    transcript, words = await with_retries(
        lambda: transcribe_words(client, data, audio.content_type)
    )

    framework_name = get_framework(DEFAULT_CHALLENGE_TYPE)['framework_name']

    if not words:
        empty_metrics = DeliveryMetrics(0, 0.0, 0.0, 0, [], 0, 0.0, [], 0.0)
        empty = {
            'challenge_type': DEFAULT_CHALLENGE_TYPE,
            'framework_name': framework_name,
            'model_version': 'n/a',
            'functions': {},
            'total_score': 0,
            'passed': False,
            'strongest_moment': '',
            'weakest_function_id': '',
            'feedback_pointer': (
                'No speech was detected in the recording — try again and speak '
                'as soon as the countdown ends.'
            ),
            'next_focus': '',
            'delivery_metrics': asdict(empty_metrics),
        }
        await remember_attempt(
            request, topic, side, '', [], data, audio.content_type, empty
        )
        return AnalyzeResult(**{**empty, 'delivery_metrics': DeliveryMetricsOut(**asdict(empty_metrics)), 'transcript': ''})

    delivery_metrics = compute_delivery_metrics(words)
    prompt_text = f"Argue {side.upper()} on: {topic}"
    result = await with_retries(
        lambda: score_response(
            client,
            DEFAULT_CHALLENGE_TYPE,
            prompt_text,
            transcript,
            asdict(delivery_metrics),
            previous_next_focus=previous_next_focus or None,
        )
    )

    analysis = {
        'challenge_type': result['challenge_type'],
        'framework_name': result['framework_name'],
        'model_version': result['model_version'],
        'functions': result['functions'],
        'total_score': result['total_score'],
        'passed': result['passed'],
        'strongest_moment': result['strongest_moment'],
        'weakest_function_id': result['weakest_function_id'],
        'feedback_pointer': result['feedback_pointer'],
        'next_focus': result['next_focus'],
        'delivery_metrics': asdict(delivery_metrics),
    }

    await remember_attempt(
        request, topic, side, transcript, words, data, audio.content_type, analysis
    )

    return AnalyzeResult(
        **{k: v for k, v in analysis.items() if k != 'delivery_metrics'},
        delivery_metrics=DeliveryMetricsOut(**asdict(delivery_metrics)),
        transcript=transcript,
    )
