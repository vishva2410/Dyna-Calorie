from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.database import supabase_client

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Validates the Bearer token against Supabase Auth.
    Returns the user_id if valid, raises 401 otherwise.
    """
    token = credentials.credentials
    try:
        response = supabase_client.auth.get_user(token)
        if hasattr(response, 'user') and response.user:
            return response.user.id
        elif isinstance(response, dict) and 'user' in response:
             return response['user']['id']
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {exc}"
        )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials."
    )
