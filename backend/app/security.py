import os
import secrets
import hashlib
import hmac
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from .database import get_db
from .models import User, AuditLog

SECRET = os.getenv('JWT_SECRET')
if os.getenv('APP_ENV') == 'production' and (not SECRET or len(SECRET) < 32):
    raise RuntimeError('Production requires JWT_SECRET of at least 32 characters')
SECRET = SECRET or secrets.token_urlsafe(48)
bearer = HTTPBearer(auto_error=False)
attempts = defaultdict(deque)


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return f'scrypt${salt}${digest}'


def verify_password(password, encoded):
    _, salt, digest = encoded.split('$')
    actual = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return hmac.compare_digest(actual, digest)


def token(user):
    return jwt.encode({'sub': user.id, 'exp': datetime.now(timezone.utc) + timedelta(hours=8)}, SECRET, algorithm='HS256')


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db=Depends(get_db)):
    try:
        payload = jwt.decode(credentials.credentials if credentials else '', SECRET, algorithms=['HS256'])
        user = db.get(User, payload['sub'])
        if not user:
            raise ValueError()
        return user
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(401, 'Authentication required')


def editor(user=Depends(current_user)):
    if user.role not in ('admin', 'analyst'):
        raise HTTPException(403, 'Analyst or administrator role required')
    return user


def admin(user=Depends(current_user)):
    if user.role != 'admin':
        raise HTTPException(403, 'Administrator role required')
    return user


def rate_limit(request: Request, category='login', limit=15):
    key = (request.client.host if request.client else 'local', category)
    queue = attempts[key]
    cutoff = time.monotonic() - 60
    while queue and queue[0] < cutoff:
        queue.popleft()
    if len(queue) >= limit:
        raise HTTPException(429, 'Too many requests; retry in one minute')
    queue.append(time.monotonic())


def audit(db, user, action, detail=None):
    db.add(AuditLog(id=str(uuid4()), actor=user.id if user else 'system', action=action, detail=detail or {}))
