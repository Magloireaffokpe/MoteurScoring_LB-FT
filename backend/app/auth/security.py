from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

#fonction de hashage du mot de passe 

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

#fonction de verification du mot de passe 

def verify_password(plain:str,hashed:str)->str:
    return pwd_context.verify(plain, hashed)

#fonction de creation du token d'acces

def create_access_token(data:dict)->str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

#decoded token 

def decode_token(token:str)->dict|None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None