"""
Google sign-in.

Uses the Google Identity Services ID-token flow: the browser gets a signed JWT
from Google and posts it here. The JWT is the proof of identity — never the
claims inside it until verify_oauth2_token has checked the signature, the
issuer, the expiry, and that the audience is this app's client id.

No client secret is involved; that belongs to the authorization-code flow,
which is only needed when calling Google APIs on the user's behalf.
"""

import os

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from storage import upsert_user

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


def public_user(user: dict) -> dict:
    """The fields the frontend is allowed to see."""
    return {
        'id': user['id'],
        'email': user['email'],
        'name': user['name'],
        'picture': user['picture'],
    }
