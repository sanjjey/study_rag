from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from backend.security.auth import (
    register_user,
    authenticate_user,
    create_access_token,
    get_current_user,
    UserCreate,
    Token,
    User,
)
from fastapi import HTTPException

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/register")
async def register(user: UserCreate):
    new_user = register_user(user.username, user.password)
    return {"message": "Registration successful", "user_id": new_user.user_id, "username": new_user.username}


@auth_router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    token = create_access_token(data={"sub": user.user_id})
    return Token(
        access_token=token,
        token_type="bearer",
        user_id=user.user_id,
        username=user.username,
    )


@auth_router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
