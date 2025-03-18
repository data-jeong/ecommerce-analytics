from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from .database import get_db
from .schemas import User, TokenData
from .config import Settings

settings = Settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate a user."""
    user = get_user(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

def get_user(db: Session, username: str) -> Optional[User]:
    """Get user by username."""
    query = """
        SELECT 
            id,
            email,
            full_name,
            hashed_password,
            is_active,
            is_superuser
        FROM users
        WHERE email = :username
    """
    result = db.execute(query, {"username": username}).first()
    if result:
        return User(**result)
    return None

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Get current superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges"
        )
    return current_user

def create_user(
    db: Session,
    email: str,
    password: str,
    full_name: str,
    is_superuser: bool = False
) -> User:
    """Create a new user."""
    hashed_password = get_password_hash(password)
    query = """
        INSERT INTO users (
            email,
            hashed_password,
            full_name,
            is_active,
            is_superuser
        ) VALUES (
            :email,
            :hashed_password,
            :full_name,
            true,
            :is_superuser
        )
        RETURNING id, email, full_name, is_active, is_superuser
    """
    result = db.execute(
        query,
        {
            "email": email,
            "hashed_password": hashed_password,
            "full_name": full_name,
            "is_superuser": is_superuser
        }
    ).first()
    db.commit()
    return User(**result)

def update_user_password(db: Session, user_id: int, new_password: str) -> bool:
    """Update user password."""
    hashed_password = get_password_hash(new_password)
    query = """
        UPDATE users
        SET hashed_password = :hashed_password
        WHERE id = :user_id
    """
    db.execute(query, {"hashed_password": hashed_password, "user_id": user_id})
    db.commit()
    return True

def deactivate_user(db: Session, user_id: int) -> bool:
    """Deactivate a user."""
    query = """
        UPDATE users
        SET is_active = false
        WHERE id = :user_id
    """
    db.execute(query, {"user_id": user_id})
    db.commit()
    return True 