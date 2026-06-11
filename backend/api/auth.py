from fastapi import APIRouter, Form, Request
from backend.models.schemas import success_response, error_response
from backend.config.settings import settings
from backend.utils.logging_config import logger

router = APIRouter(tags=["Authentication"])

# Simple in-memory session registry (production apps would use Redis or databases)
active_sessions = set()

def cookie_options():
    """Returns cookie settings that work for local HTTP and hosted HTTPS deployments."""
    is_production = settings.ENVIRONMENT == "production"
    return {
        "httponly": True,
        "samesite": "none" if is_production else "lax",
        "secure": is_production,
    }

@router.post("/api/login")
def api_login(email: str = Form(...), password: str = Form(...)):
    """Accepts user login, registers session, and returns cookie/metadata."""
    logger.info(f"Login attempt received for email: {email}")
    
    session_id = email
    active_sessions.add(session_id)
    
    # Create standardized success response
    response = success_response(
        data={
            "redirect": "/dashboard",
            "session_id": session_id
        },
        message="Login completed successfully"
    )
    
    # Configure cookie sharing. Local development runs over HTTP, so Secure cookies
    # would be rejected by the browser and make auth/check appear broken.
    response.set_cookie(
        key="session_id",
        value=session_id,
        max_age=3600 * 24,
        **cookie_options()
    )
    
    logger.info(f"Session registered successfully for {email}.")
    return response

@router.post("/api/logout")
def api_logout(request: Request):
    """Deletes active session cookies and deregisters session registry."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = request.headers.get("x-session-id")
        
    if session_id in active_sessions:
        active_sessions.remove(session_id)
        logger.info(f"Deregistered session: {session_id}")
        
    response = success_response(message="Logout completed successfully")
    response.delete_cookie(
        key="session_id",
        samesite=cookie_options()["samesite"],
        secure=cookie_options()["secure"]
    )
    return response

@router.get("/api/auth/check")
def check_session(request: Request):
    """Utility endpoint for the decoupled frontend to check authentication state."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = request.headers.get("x-session-id")
        
    if session_id and session_id in active_sessions:
        return success_response(
            data={"authenticated": True, "session_id": session_id},
            message="Authenticated successfully"
        )
    return error_response(
        message="Invalid or expired session",
        status_code=401
    )
