from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt as _bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from loguru import logger
import os
import uuid

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-to-a-long-random-secret")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# In-memory user store keyed by username; swap for a real DB in production.
_users_by_username: dict = {}
_users_by_id: dict = {}


class UserCreate(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    username: str


class TokenData(BaseModel):
    user_id: Optional[str] = None


class User(BaseModel):
    user_id: str
    username: str
    role: str = "student"


def _hash_password(password: str) -> str:
    # bcrypt hard-limits at 72 bytes; encode then truncate explicitly
    secret = password.encode("utf-8")[:72]
    return _bcrypt.hashpw(secret, _bcrypt.gensalt()).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    secret = plain.encode("utf-8")[:72]
    return _bcrypt.checkpw(secret, hashed.encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise exc
    except JWTError:
        raise exc

    record = _users_by_id.get(user_id)
    if record is None:
        raise exc

    return User(user_id=record["user_id"], username=record["username"], role=record.get("role", "student"))


def register_user(username: str, password: str) -> User:
    username = username.strip().lower()
    if not username or len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if username in _users_by_username:
        raise HTTPException(status_code=409, detail="Username already taken")

    user_id = str(uuid.uuid4())
    record = {
        "user_id": user_id,
        "username": username,
        "hashed_password": _hash_password(password),
        "role": "student",
    }
    _users_by_username[username] = record
    _users_by_id[user_id] = record
    logger.info(f"New user registered: {username} ({user_id})")
    return User(user_id=user_id, username=username)


def authenticate_user(username: str, password: str) -> Optional[User]:
    username = username.strip().lower()
    record = _users_by_username.get(username)
    if not record or not _verify_password(password, record["hashed_password"]):
        return None
    return User(user_id=record["user_id"], username=record["username"], role=record.get("role", "student"))
