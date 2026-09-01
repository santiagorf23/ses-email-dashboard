import os
import sys
import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

router = APIRouter()

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
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = USERS.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        logger.warning("Login fallido para usuario: %s", form_data.username)
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    logger.info("Login exitoso para usuario: %s", form_data.username)
    token = create_token({"sub": user["username"]})
    return {"access_token": token, "token_type": "bearer", "full_name": user["full_name"]}


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return {"username": current_user["username"], "full_name": current_user["full_name"]}