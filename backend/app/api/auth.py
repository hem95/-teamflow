from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, TokenResponse, UserResponse, RefreshRequest
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.dependencies import get_current_user
import re

router = APIRouter(prefix="/auth", tags=["Authentication"])

# A pre-computed hash we verify against when the email doesn't exist.
# Running a real (failing) bcrypt check keeps the response time the same
# whether or not the email is registered — closing a timing side-channel
# that would otherwise let an attacker enumerate which emails have accounts.
_DUMMY_HASH = hash_password("timing-attack-mitigation-placeholder")


def slugify(text: str) -> str:
    """Turn 'My Cool Name' into 'my-cool-name' for use in URLs."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new account.
    1. Check email & username aren't taken
    2. Hash the password
    3. Save user to database
    4. Return two tokens so the user is immediately logged in
    """
    # Check for duplicates
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        email=body.email,
        username=body.username,
        display_name=body.display_name,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    await db.flush()        # flush assigns the auto-generated id without committing
    await db.refresh(user)  # re-read from DB so we have created_at etc.

    return TokenResponse(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token({"sub": str(user.id)}),
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Log in with email + password.
    Returns a fresh pair of tokens on success.
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    # Always run a password verification — against the real hash if the user
    # exists, or a dummy hash if not — so the response takes the same time
    # either way. This prevents attackers from discovering which emails are
    # registered by timing the response.
    if user:
        password_ok = verify_password(body.password, user.password_hash)
    else:
        verify_password(body.password, _DUMMY_HASH)
        password_ok = False

    if not user or not password_ok:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    # Mark user as online
    await db.execute(update(User).where(User.id == user.id).values(is_online=True))

    return TokenResponse(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token({"sub": str(user.id)}),
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """
    Exchange a refresh token for a new access token.
    Called automatically by the frontend when the access token expires.
    """
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == int(payload["sub"])))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    return TokenResponse(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token({"sub": str(user.id)}),
        user=UserResponse.model_validate(user),
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Mark user as offline. Token invalidation is handled client-side."""
    await db.execute(update(User).where(User.id == current_user.id).values(is_online=False))
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the profile of whoever is currently logged in."""
    return current_user
