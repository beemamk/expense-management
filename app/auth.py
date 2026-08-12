import hashlib
import os
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.database import get_db
from app import models

SECRET_KEY = "SUPER_SECRET_PASSPHRASE_CHANGE_ME"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_password_hash(password: str) -> str:
    """Securely hash a password using standard SHA-256 with a unique salt."""
    salt = os.urandom(16)
    db_string = salt + hashlib.sha256(salt + password.encode('utf-8')).digest()
    return db_string.hex()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify an incoming password against the saved hexadecimal salt and hash."""
    try:
        db_bytes = bytes.fromhex(hashed_password)
        salt = db_bytes[:16]
        expected_hash = salt + hashlib.sha256(salt + plain_password.encode('utf-8')).digest()
        return db_bytes == expected_hash
    except Exception:
        return False

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user