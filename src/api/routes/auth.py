from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.models.schemas import LoginBody, Token, UserCreate, UserOut
from src.api.security import create_access_token, hash_password, verify_password
from src.data.database import get_db
from src.data.models import User
from src.data.repositories import users as users_repo

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut)
def register(body: UserCreate, db: Session = Depends(get_db)) -> User:
    if users_repo.get_by_email(db, body.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    u = User(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
        birth_date=body.birth_date,
        gender=body.gender,
        region=body.region,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@router.post("/login", response_model=Token)
def login(body: LoginBody, db: Session = Depends(get_db)) -> Token:
    user = users_repo.get_by_email(db, body.email)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(sub=user.email, user_id=user.user_id, is_admin=user.is_admin)
    return Token(access_token=token, is_admin=user.is_admin)
