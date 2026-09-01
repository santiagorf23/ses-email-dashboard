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

logger = logging.getLogger(__name__)

router = APIRouter()

# Rate limiting - máximo 5 intentos fallidos por IP en 5 minutos
_login_attempts: dict[str, list[float]] = defaultdict(list)
MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 300  # 5 minutos


def _check_rate_limit(ip: str) -> None:
    """Verificar rate limiting para login. Lanza 429 si se excede el límite."""
    now = time.time()
    # Limpiar intentos fuera de la ventana
    _login_attempts[ip] = [
        t for t in _login_attempts[ip]
        if now - t < LOGIN_WINDOW_SECONDS
    ]
    if len(_login_attempts[ip]) >= MAX_LOGIN_ATTEMPTS:
        logger.warning("Rate limit excedido para IP: %s", ip)
        raise HTTPException(
            status_code=429,
            detail="Demasiados intentos de login. Intenta de nuevo en 5 minutos."
        )


def _record_failed_attempt(ip: str) -> None:
    """Registrar un intento fallido de login."""
    _login_attempts[ip].append(time.time())

# Fail fast si faltan secrets críticos
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    print("ERROR: SECRET_KEY no está configurado. Define la variable de entorno SECRET_KEY.", file=sys.stderr)
    sys.exit(1)

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    print("ERROR: ADMIN_PASSWORD no está configurado. Define la variable de entorno ADMIN_PASSWORD.", file=sys.stderr)
    sys.exit(1)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Hardcoded users — reemplazar con DB lookup en producción
USERS = {
    os.getenv("ADMIN_USER", "admin"): {
        "username": os.getenv("ADMIN_USER", "admin"),
        "hashed_password": pwd_context.hash(ADMIN_PASSWORD),
        "full_name": "Administrador",
    }
}


class Token(BaseModel):
    access_token: str
    token_type: str
    full_name: str


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=401,
        detail="No autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None or username not in USERS:
            logger.warning("Token inválido o usuario no encontrado: %s", username)
            raise credentials_exception
        return USERS[username]
    except JWTError as e:
        logger.warning("Error decodificando token: %s", e)
        raise credentials_exception


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)
    
    user = USERS.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        _record_failed_attempt(client_ip)
        logger.warning("Login fallido para usuario: %s (IP: %s)", form_data.username, client_ip)
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    
    # Login exitoso - limpiar intentos
    _login_attempts[client_ip] = []
    logger.info("Login exitoso para usuario: %s (IP: %s)", form_data.username, client_ip)
    token = create_token({"sub": user["username"]})
    return {"access_token": token, "token_type": "bearer", "full_name": user["full_name"]}


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return {"username": current_user["username"], "full_name": current_user["full_name"]}