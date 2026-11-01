from datetime import datetime, timedelta, timezone
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
import secrets
import jwt
from novaaltairapi.config import settings
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader


http_bearer = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_access(credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
                        api_key: str | None = Depends(api_key_header)):
    if api_key and secrets.compare_digest(api_key, settings.bot_api_key):
        return {
            "auth_type": "bot",
            "identity": "telegram_bot"
        }
    if credentials:
        try:
            token = credentials.credentials
            paylaod = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

            if paylaod.get("type") != "access":
                raise HTTPException(status_code=401, detail="Не верный тип токена")

            username = paylaod.get("sub")
            if username:
                return {
                    "auth_type": "user",
                    "identity": username
                }
            
        except (jwt.InvalidTokenError, Exception):
            pass

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Needed autorization")

def create_tokens(username: str) -> tuple[str, str]:
    now = datetime.now(timezone.utc)

    access_expire = now + timedelta(minutes=20)
    access_payload = {
        "sub": username,
        "type": "access",
        "exp": access_expire
    }
    access_token = jwt.encode(access_payload, settings.secret_key, algorithm=settings.algorithm)

    refresh_expire = now + timedelta(days=180)
    refresh_payload = {
        "sub": username,
        "type": "refresh",
        "exp": refresh_expire
    }
    refresh_token = jwt.encode(refresh_payload, settings.secret_key, algorithm=settings.algorithm)

    return access_token, refresh_token


_hasher = PasswordHasher()

def hash_password(password: str) -> str:
    return _hasher.hash(password)

def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError): 
        return False