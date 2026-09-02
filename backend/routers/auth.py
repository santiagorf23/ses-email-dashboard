import os
import sys
import time
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext
from db.database import get_conn

logger = logging.getLogger(__name__)

router = APIRouter()

# Rate limiting
_login_attempts: dict[str, list[float]] = defaultdict(list)
MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 300

def _check_rate_limit(ip: str) -> None:
    now = time.time()
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < LOGIN_WINDOW_SECONDS]
    if len(_login_attempts[ip]) >= MAX_LOGIN_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Demasiados intentos. Intenta en 5 minutos.")

def _record_failed_attempt(ip: str) -> None:
    _login_attempts[ip].append(time.time())

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    print("ERROR: SECRET_KEY no configurado.", file=sys.stderr)
    sys.exit(1)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class Token(BaseModel):
    access_token: str
    token_type: str
    full_name: str
    tenant_id: int


class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    tenant_id: int
    role: str = "admin"


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(status_code=401, detail="No autenticado")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        tenant_id: int = payload.get("tenant_id")
        if username is None or tenant_id is None:
            raise credentials_exception
        return {"username": username, "tenant_id": tenant_id, "role": payload.get("role", "admin")}
    except JWTError:
        raise credentials_exception


@router.post("/login", response_model=Token)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    async for conn in get_conn():
        row = await conn.fetchrow(
            "SELECT id, email, password_hash, full_name, tenant_id, role FROM app_users WHERE email = $1 AND is_active = TRUE",
            form_data.username
        )

    if not row or not verify_password(form_data.password, row["password_hash"]):
        _record_failed_attempt(client_ip)
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    _login_attempts[client_ip] = []
    token = create_token({"sub": row["email"], "tenant_id": row["tenant_id"], "role": row["role"]})
    return {"access_token": token, "token_type": "bearer", "full_name": row["full_name"], "tenant_id": row["tenant_id"]}


@router.post("/register", response_model=Token)
async def register(request: Request, user_data: UserCreate):
    async for conn in get_conn():
        # Check if tenant exists
        tenant = await conn.fetchrow("SELECT id FROM tenants WHERE id = $1", user_data.tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant no encontrado")

        # Check if user already exists
        existing = await conn.fetchrow("SELECT id FROM app_users WHERE email = $1", user_data.email)
        if existing:
            raise HTTPException(status_code=409, detail="Usuario ya existe")

        # Create user
        hashed = pwd_context.hash(user_data.password)
        row = await conn.fetchrow(
            "INSERT INTO app_users (email, password_hash, full_name, tenant_id, role) VALUES ($1, $2, $3, $4, $5) RETURNING id, email, full_name, tenant_id, role",
            user_data.email, hashed, user_data.full_name, user_data.tenant_id, user_data.role
        )

    token = create_token({"sub": row["email"], "tenant_id": row["tenant_id"], "role": row["role"]})
    return {"access_token": token, "token_type": "bearer", "full_name": row["full_name"], "tenant_id": row["tenant_id"]}


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user
