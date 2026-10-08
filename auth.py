import jwt
import bcrypt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, g
import os

SECRET_KEY = os.getenv("JWT_SECRET", "edusafe-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = 60 * 24
REFRESH_TOKEN_EXPIRE = 60 * 24 * 7

ROLES = {
    "student": {
        "name": "Hoc sinh",
        "permissions": ["chat:create","mood:read","mood:create","report:create","report:read_own","profile:read_own"],
    },
    "teacher": {
        "name": "Giao vien",
        "permissions": ["chat:create","mood:read","report:create","report:read","report:update","student:read","student:note","profile:read_own","alert:read","alert:delete"],
    },
    "parent": {
        "name": "Phu huynh",
        "permissions": ["mood:read_child","report:read_child","student:read_child","profile:read_own"],
    },
    "admin": {
        "name": "Quan tri vien",
        "permissions": ["chat:create","mood:read","report:create","report:read","report:update","student:read","student:note","user:read","user:create","user:update","user:delete","system:update","alert:read","alert:delete"],
    },
}


def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id, role, extra=None):
    payload = {"sub": str(user_id), "role": role, "type": "access", "iat": datetime.utcnow(), "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE)}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id):
    payload = {"sub": str(user_id), "type": "refresh", "iat": datetime.utcnow(), "exp": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE // 60)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except:
        return None


def get_current_user_from_request():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1]
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    return payload


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user_from_request()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
        g.current_user = user
        return f(*args, **kwargs)
    return decorated


def require_role(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = get_current_user_from_request()
            if not user:
                return jsonify({"error": "Unauthorized"}), 401
            if user.get("role") not in roles:
                return jsonify({"error": "Forbidden"}), 403
            g.current_user = user
            return f(*args, **kwargs)
        return decorated
    return decorator


def require_permission(permission):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = get_current_user_from_request()
            if not user:
                return jsonify({"error": "Unauthorized"}), 401
            role = user.get("role")
            role_permissions = ROLES.get(role, {}).get("permissions", [])
            if permission not in role_permissions:
                return jsonify({"error": "Forbidden"}), 403
            g.current_user = user
            return f(*args, **kwargs)
        return decorated
    return decorator


def get_user_permissions(role):
    return ROLES.get(role, {}).get("permissions", [])
