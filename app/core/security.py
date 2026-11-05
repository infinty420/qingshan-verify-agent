"""JWT（HMAC-SHA256，标准库实现，避免额外依赖）与密码哈希（PBKDF2）。"""
import base64
import hashlib
import hmac
import json
import secrets
import time

from app.core.config import settings


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_dec(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def hash_password(password: str, iterations: int = 60000) -> str:
    salt = secrets.token_hex(8)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations)
    return f"pbkdf2${iterations}${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, it, salt, digest = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), int(it))
        return hmac.compare_digest(dk.hex(), digest)
    except Exception:
        return False


def _sign(msg: str) -> str:
    return _b64url(
        hmac.new(settings.secret_key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).digest()
    )


def create_token(user_id: int, role: str) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + settings.token_expire_hours * 3600,
    }
    h = _b64url(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    return f"{h}.{p}.{_sign(f'{h}.{p}')}"


def decode_token(token: str) -> dict | None:
    try:
        h, p, s = token.split(".")
        if not hmac.compare_digest(s, _sign(f"{h}.{p}")):
            return None
        payload = json.loads(_b64url_dec(p))
        if int(payload.get("exp", 0)) < time.time():
            return None
        return payload
    except Exception:
        return None
