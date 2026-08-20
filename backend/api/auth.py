"""
JWT Verification Middleware (TRD 2.2, 3.1)

TRD 7.1 documents a static SUPABASE_JWT_SECRET for HS256 verification, but this
project's Supabase auth signs tokens with ES256 against a rotating key set
published at <SUPABASE_URL>/auth/v1/.well-known/jwks.json (confirmed by querying
it directly -- the endpoint returns an EC P-256 key, not an HS256 setup). That
makes SUPABASE_JWT_SECRET inapplicable here: verification uses the public JWKS
instead, which needs no secret at all. PyJWKClient handles fetching, per-`kid`
key selection, and caching.
"""
import os
from fastapi import Header, HTTPException
import jwt
from jwt import PyJWKClient

_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        if not supabase_url:
            raise RuntimeError("SUPABASE_URL is not set")
        _jwks_client = PyJWKClient(f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json")
    return _jwks_client


def get_current_user(authorization: str = Header(default=None)) -> dict:
    """
    FastAPI dependency: verifies the Supabase-issued JWT from the Authorization
    header and returns {"user_id": ..., "email": ...} extracted from its claims.
    Raises 401 on anything missing, malformed, expired, or badly signed.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")

    token = authorization[len("Bearer "):].strip()

    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {e}")

    return {"user_id": payload["sub"], "email": payload.get("email")}
