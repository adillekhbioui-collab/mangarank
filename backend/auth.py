"""
JWT verification middleware for FastAPI.

Verifies Supabase-issued JWTs on protected endpoints.
Public endpoints (manga listing, search, detail) do NOT need this.
"""

import os
from typing import Optional

from fastapi import Depends, HTTPException, Header
from jose import jwt, JWTError


# Supabase JWT secret — found in Dashboard → Settings → API → JWT Secret
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

# Supabase URL for issuer validation
SUPABASE_URL = os.getenv("SUPABASE_URL", "")


def _decode_token(token: str) -> dict:
    """Decode and verify a Supabase JWT. Raises on any failure."""
    if not SUPABASE_JWT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Auth not configured. Set SUPABASE_JWT_SECRET.",
        )

    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid or expired token: {exc}",
        )

    return payload


def get_current_user(
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """
    FastAPI dependency — extracts and verifies the user from the
    Authorization header. Returns the decoded JWT payload.

    Usage:
        @app.get("/protected", dependencies=[Depends(get_current_user)])
    or:
        @app.get("/protected")
        async def handler(user: dict = Depends(get_current_user)):
            user_id = user["sub"]
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header.")

    # Accept "Bearer <token>" format
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization format.")

    return _decode_token(parts[1])


def get_optional_user(
    authorization: Optional[str] = Header(default=None),
) -> Optional[dict]:
    """
    Like get_current_user but returns None if no token is provided.
    Useful for endpoints that work for both anonymous and logged-in users.
    """
    if not authorization:
        return None

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    try:
        return _decode_token(parts[1])
    except HTTPException:
        return None


async def require_admin(
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """
    FastAPI dependency — verifies the user is authenticated AND is in
    the admin_users table. Replaces the old plaintext password check.

    Falls back to ADMIN_PASSWORD env var if JWT auth is not yet configured,
    so existing dashboard continues working during migration.
    """
    # Fallback: support legacy password header during transition
    admin_pw = os.getenv("ADMIN_PASSWORD", "").strip()

    # Try JWT-based admin check first
    if authorization and SUPABASE_JWT_SECRET:
        user = get_current_user(authorization)
        user_id = user.get("sub")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no user ID.")

        # Check admin_users table via the imported sb_get (lazy import to avoid circular)
        from backend.main import sb_get

        r = await sb_get(
            "admin_users",
            params={"user_id": f"eq.{user_id}", "select": "user_id", "limit": "1"},
        )

        if r.status_code not in (200, 206) or not r.json():
            raise HTTPException(status_code=403, detail="Not an admin user.")

        return user

    # Legacy fallback: plain password header
    x_admin_password = None
    if authorization and not authorization.startswith("Bearer"):
        x_admin_password = authorization

    # Also check the dedicated header  
    if not x_admin_password:
        # This will be removed once JWT admin is fully deployed
        pass

    if admin_pw and x_admin_password and x_admin_password == admin_pw:
        return {"sub": "legacy-admin", "role": "admin"}

    raise HTTPException(status_code=401, detail="Unauthorized.")
