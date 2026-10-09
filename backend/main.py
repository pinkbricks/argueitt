import asyncio
import hashlib
import json
import logging
import os
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse
from google import genai
from google.genai import errors as genai_errors
from pydantic import BaseModel

import auth
import storage
from database import DatabaseUnavailable
from framework import get_framework
from metrics import score_response
from stats import DeliveryMetrics, compute_delivery_metrics
from transcript import transcribe_words

load_dotenv()

logger = logging.getLogger('uvicorn.error')

MAX_AUDIO_BYTES = 20 * 1024 * 1024

# Argueitt gives a random topic + side with zero prep time, so it's scored
# against the "answer_the_unexpected" framework (coherence, on-topic, quick recovery).
DEFAULT_CHALLENGE_TYPE = 'answer_the_unexpected'

app = FastAPI()

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
    attempt_id: str | None = None
    persistence_status: Literal['saved', 'not_saved', 'guest'] = 'not_saved'
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
            # The detail stays out of the response body on purpose: exception
            # text from the API clients can quote request headers, which carry
            # the API key. It goes to the logs, where it belongs.
            logger.exception('Upstream model call failed')
            raise HTTPException(502, 'The analysis service is unavailable right now.') from exc
    raise HTTPException(503, 'Gemini is busy, try again in a moment')


async def read_audio(audio: UploadFile) -> bytes:
    data = await audio.read()
    if not data:
        raise HTTPException(400, 'Empty audio')
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(413, 'Audio too large')
    return data


@app.exception_handler(DatabaseUnavailable)
async def database_error(request: Request, exc: DatabaseUnavailable):
    logger.warning('Database operation failed (%s)', exc)
    return JSONResponse(status_code=503, content={'detail': 'Saved history is temporarily unavailable. Please try again.'})


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
    # Replace any pre-login session contents with the verified identity.
    request.session.clear()
    request.session['user_id'] = user['id']
    return SessionUser(**auth.public_user(user))


@app.get('/api/auth/me')
async def me(request: Request):
    user_id = current_user_id(request)
    if not user_id:
        return {'user': None}
    user = await storage.get_user(user_id)
    if user is None:
        request.session.clear()
        return {'user': None}
    return {'user': auth.public_user(user)}


@app.post('/api/auth/sign-out')
async def sign_out(request: Request):
    request.session.clear()
    return {'status': 'ok'}


def saved_result(record: dict, request_hash: str) -> AnalyzeResult:
    if record['request_hash'] != request_hash:
        raise HTTPException(409, 'This request ID was already used for a different recording.')
    return AnalyzeResult(**record['analysis'], transcript=record['transcript'],
                         attempt_id=record['id'], persistence_status='saved')


async def remember_attempt(record: dict) -> AnalyzeResult:
    result = AnalyzeResult(**record['analysis'], transcript=record['transcript'])
    if not record['user_id']:
        return result.model_copy(update={'persistence_status': 'guest'})
    if record.get('unverified_previous'):
        # Preserve feedback, but do not silently save a retry without its link
        # when ownership could not be checked during a database outage.
        return result
    try:
        saved = await storage.save_attempt(record)
        return saved_result(saved, record['request_hash'])
    except DatabaseUnavailable as exc:
        logger.warning('Could not save attempt; feedback still returned (%s)', exc)
        return result


@app.get('/api/attempts')
async def attempts(request: Request, limit: int = Query(20, ge=1, le=100),
                   cursor: str | None = Query(None, max_length=512)):
    user_id = current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail='Sign in to see your attempts')
    try:
        return await storage.list_attempts(user_id, limit, cursor)
    except ValueError:
        raise HTTPException(400, 'Invalid history cursor') from None


@app.get('/api/streak')
async def streak(request: Request, timezone: str = Query('UTC', min_length=1, max_length=100)):
    user_id = current_user_id(request)
    if not user_id:
        raise HTTPException(401, 'Sign in to track your practice streak')
    try:
        return await storage.get_streak(user_id, timezone)
    except ValueError:
        raise HTTPException(400, 'Invalid timezone') from None


@app.post('/api/analyze', response_model=AnalyzeResult)
async def analyze(
    request: Request,
    topic: str = Form(..., min_length=1, max_length=2000),
    side: Literal['for', 'against'] = Form(...),
    audio: UploadFile = File(...),
    previous_next_focus: str = Form('', max_length=2000),
    request_id: UUID = Form(...),
    previous_attempt_id: str | None = Form(None, max_length=128),
):
    """Generate feedback, then persist it without losing feedback on a DB outage."""
    data = await read_audio(audio)
    user_id = current_user_id(request)
    request_hash = hashlib.sha256(json.dumps(
        [topic, side, previous_attempt_id, previous_next_focus, audio.content_type],
        separators=(',', ':'),
    ).encode() + b'\0' + data).hexdigest()
    # Never hold a database transaction open during Gemini requests.
    verified_previous_id = None
    if user_id:
        try:
            existing = await storage.get_request(user_id, request_id)
            if existing:
                return saved_result(existing, request_hash)
            if previous_attempt_id:
                previous = await storage.get_attempt(user_id, previous_attempt_id)
                if previous is None:
                    raise HTTPException(404, 'Previous attempt not found')
                if previous['topic'] != topic or previous['side'] != side:
                    raise HTTPException(400, 'A retry must use the same topic and side')
                verified_previous_id = previous['id']
                previous_next_focus = (previous['analysis'] or {}).get('next_focus', '')
        except DatabaseUnavailable as exc:
            logger.warning('History lookup unavailable; continuing practice (%s)', exc)
    record = {
        'user_id': user_id, 'request_id': request_id, 'request_hash': request_hash,
        'previous_attempt_id': verified_previous_id, 'topic': topic, 'side': side,
        'unverified_previous': bool(user_id and previous_attempt_id and not verified_previous_id),
        'audio_bytes': len(data), 'audio_type': audio.content_type,
    }
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
            'analysed_at': datetime.now(timezone.utc).isoformat(),
        }
        return await remember_attempt({**record, 'transcript': '', 'words': [],
                                       'analysis': empty})

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

    analysis['analysed_at'] = datetime.now(timezone.utc).isoformat()
    return await remember_attempt({**record, 'transcript': transcript,
                                   'words': words, 'analysis': analysis})
