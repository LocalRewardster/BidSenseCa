from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# TODO: Import models and services when created
# from app.services.auth_service import AuthService

router = APIRouter()


class MagicLinkRequest(BaseModel):
    email: str


@router.post("/magic-link")
async def send_magic_link(request: MagicLinkRequest) -> dict:
    """Send magic link for passwordless authentication."""
    # TODO: Implement magic link logic with Supabase Auth
    return {
        "message": "Magic link sent successfully",
        "email": request.email,
    }


@router.post("/verify")
async def verify_token(token: str) -> dict:
    """Verify authentication token."""
    # TODO: Implement token verification logic
    return {
        "valid": True,
        "user_id": "user-id",
    }


@router.post("/logout")
async def logout() -> dict:
    """Logout current user."""
    # TODO: Implement logout logic
    return {"message": "Logged out successfully"} 