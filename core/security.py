from passlib.context import CryptContext
from datetime import datetime, timezone, timedelta
from jose import jwt
from core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str):
    return pwd_context.hash(password)


def create_acess_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    sp = timezone("America/Sao_Paulo")
    if expires_delta:
        expire = datetime.now(tz=sp) + expires_delta
    else:
        expire = datetime.now(tz=sp) + timedelta(minutes=15)
    to_encode.update({"exp": expire, "iat": datetime.now(tz=sp)})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.ALGORITHM)
