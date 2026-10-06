"""
Google sign-in.

Uses the Google Identity Services ID-token flow: the browser gets a signed JWT
from Google and posts it here. The JWT is the proof of identity — never the
claims inside it until verify_oauth2_token has checked the signature, the
issuer, the expiry, and that the audience is this app's client id.

No client secret is involved; that belongs to the authorization-code flow,
which is only needed when calling Google APIs on the user's behalf.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

USERS_FILE = Path(__file__).parent / 'data' / 'users.json'

users_lock = asyncio.Lock()

ALLOWED_ISSUERS = {'accounts.google.com', 'https://accounts.google.com'}


class AuthError(Exception):
    """Raised when a credential cannot be trusted."""


def get_client_id() -> str:
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    if not client_id:
        raise AuthError('GOOGLE_CLIENT_ID is not set')
    return client_id


def verify_credential(credential: str) -> dict:
    """Verifies a Google ID token and returns its claims."""
    try:
        claims = id_token.verify_oauth2_token(
            credential, google_requests.Request(), get_client_id()
        )
    except ValueError as exc:
        # Covers a bad signature, a wrong audience, and an expired token.
        raise AuthError('Could not verify that Google account') from exc

    if claims.get('iss') not in ALLOWED_ISSUERS:
        raise AuthError('Unexpected token issuer')
    if not claims.get('email_verified'):
        raise AuthError('That Google account has no verified email')

    return claims


def load_users() -> list[dict]:
    if not USERS_FILE.exists():
        return []
    return json.loads(USERS_FILE.read_text())


def save_users(users: list[dict]) -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    USERS_FILE.write_text(json.dumps(users, indent=2))


async def upsert_user(claims: dict) -> dict:
    """
    Finds or creates the user behind a verified token.

    Keyed on Google's 'sub', which is stable for the account. Email is stored
    for display only — people can change theirs, so it is never the key.
    """
    google_id = claims['sub']
    now = datetime.now(timezone.utc).isoformat()

    async with users_lock:
        users = load_users()
        user = next((u for u in users if u['google_id'] == google_id), None)

        if user is None:
            user = {
                'id': uuid.uuid4().hex,
                'google_id': google_id,
                'email': claims.get('email', ''),
                'name': claims.get('name', ''),
                'picture': claims.get('picture', ''),
                'created_at': now,
                'last_seen_at': now,
            }
            users.append(user)
        else:
            user['email'] = claims.get('email', user['email'])
            user['name'] = claims.get('name', user['name'])
            user['picture'] = claims.get('picture', user['picture'])
            user['last_seen_at'] = now

        save_users(users)

    return user


def public_user(user: dict) -> dict:
    """The fields the frontend is allowed to see."""
    return {
        'id': user['id'],
        'email': user['email'],
        'name': user['name'],
        'picture': user['picture'],
    }
