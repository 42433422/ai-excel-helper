"""
纯 stdlib 的密码哈希实现，替代 ``werkzeug.security``。

设计目标：
    1. **向前兼容**：生成的 hash 串格式与 werkzeug ``pbkdf2:sha256`` 完全一致，
       DB 里已有的 werkzeug hash 无需迁移。
    2. **向后兼容**：``check_password_hash`` 能识别 werkzeug 的所有历史格式，
       包括 ``pbkdf2:<algo>:<iter>$<salt>$<hex>``、``scrypt:N:r:p$<salt>$<hex>``、
       以及旧的 ``<algo>$<salt>$<hex>`` 和无盐的 ``plain$password`` 形态。
    3. **零外部依赖**：只用 ``hashlib`` / ``secrets`` / ``hmac``，不再拉 werkzeug。

接口签名尽量贴近 werkzeug：

    - ``generate_password_hash(password, method="pbkdf2:sha256:260000", salt_length=16)``
    - ``check_password_hash(pwhash, password)``

说明：
    werkzeug 3.x 把默认方法从 ``pbkdf2:sha256`` 换成了 ``scrypt``。本模块仍以
    ``pbkdf2:sha256`` 为默认，因为它是 stdlib 原生且已是项目历史里存量哈希的
    主要算法；``scrypt`` 仅用于 *校验* 旧有哈希。如未来要生成 scrypt 新哈希，
    扩展 ``_hash_pbkdf2`` 同模可再加 ``_hash_scrypt``。
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import string

SALT_CHARS = string.ascii_letters + string.digits
DEFAULT_PBKDF2_ITERATIONS = 260000

logger = logging.getLogger(__name__)
DEFAULT_METHOD = f"pbkdf2:sha256:{DEFAULT_PBKDF2_ITERATIONS}"


def _gen_salt(length: int) -> str:
    if length < 1:
        raise ValueError("Salt length must be at least 1.")
    return "".join(secrets.choice(SALT_CHARS) for _ in range(length))


def _hash_pbkdf2(
    password: str,
    salt: str,
    algo: str = "sha256",
    iterations: int = DEFAULT_PBKDF2_ITERATIONS,
) -> str:
    digest = hashlib.pbkdf2_hmac(
        algo,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return digest.hex()


def _hash_scrypt(
    password: str,
    salt: str,
    n: int,
    r: int,
    p: int,
    dklen: int = 64,
) -> str:
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt.encode("utf-8"),
        n=n,
        r=r,
        p=p,
        maxmem=132 * 1024 * 1024,
        dklen=dklen,
    )
    return digest.hex()


def generate_password_hash(
    password: str,
    method: str = DEFAULT_METHOD,
    salt_length: int = 16,
) -> str:
    """生成与 werkzeug 兼容的密码哈希串。

    支持的 ``method``：
        - ``pbkdf2:<algo>`` 或 ``pbkdf2:<algo>:<iterations>``
          （如 ``pbkdf2:sha256``、``pbkdf2:sha256:300000``）
        - 任意 ``hashlib`` 支持的裸算法名（如 ``sha256``），生成
          ``<algo>$<salt>$<hex>`` 的 v1 格式
    """
    if not isinstance(password, str):
        raise TypeError("password must be str")

    salt = _gen_salt(salt_length)
    if method.startswith("pbkdf2:"):
        parts = method.split(":")
        algo = parts[1] if len(parts) > 1 else "sha256"
        if algo not in hashlib.algorithms_guaranteed:
            raise ValueError(f"Unsupported PBKDF2 hash algorithm: {algo}")
        iterations = int(parts[2]) if len(parts) > 2 else DEFAULT_PBKDF2_ITERATIONS
        hexed = _hash_pbkdf2(password, salt, algo, iterations)
        return f"pbkdf2:{algo}:{iterations}${salt}${hexed}"

    if method == "scrypt":
        n, r, p = 2**15, 8, 1
        hexed = _hash_scrypt(password, salt, n, r, p)
        return f"scrypt:{n}:{r}:{p}${salt}${hexed}"

    if method in hashlib.algorithms_guaranteed:
        h = hashlib.new(method)
        h.update((salt + password).encode("utf-8"))
        return f"{method}${salt}${h.hexdigest()}"

    raise ValueError(f"Unsupported hash method: {method}")


def check_password_hash(pwhash: str, password: str) -> bool:
    """校验密码是否与哈希匹配。

    兼容 werkzeug 历史上的四种格式：
        1. ``pbkdf2:<algo>:<iterations>$<salt>$<hexhash>``
        2. ``scrypt:<n>:<r>:<p>$<salt>$<hexhash>``
        3. ``<algo>$<salt>$<hexhash>`` （旧版无参数格式）
        4. ``plain$<password>`` （调试/明文，不建议生产使用但保留兼容）
    """
    if not isinstance(pwhash, str) or not isinstance(password, str):
        return False
    if "$" not in pwhash:
        return False

    method, _, rest = pwhash.partition("$")
    if not rest:
        return False

    if method == "plain":
        if os.environ.get("XCAGI_DEBUG", "1") != "1":
            logger.warning("plain-text password check rejected in non-debug environment")
            return False
        return hmac.compare_digest(rest, password)

    salt, _, stored = rest.partition("$")
    if not stored:
        return False

    try:
        if method.startswith("pbkdf2:"):
            parts = method.split(":")
            algo = parts[1] if len(parts) > 1 else "sha256"
            iterations = int(parts[2]) if len(parts) > 2 else DEFAULT_PBKDF2_ITERATIONS
            candidate = _hash_pbkdf2(password, salt, algo, iterations)
            return hmac.compare_digest(candidate, stored)

        if method.startswith("scrypt:"):
            parts = method.split(":")
            n = int(parts[1])
            r = int(parts[2])
            p = int(parts[3])
            dklen = len(bytes.fromhex(stored))
            candidate = _hash_scrypt(password, salt, n, r, p, dklen=dklen)
            return hmac.compare_digest(candidate, stored)

        if method in hashlib.algorithms_guaranteed:
            h = hashlib.new(method)
            h.update((salt + password).encode("utf-8"))
            return hmac.compare_digest(h.hexdigest(), stored)
    except (ValueError, TypeError):
        return False

    return False


__all__ = [
    "generate_password_hash",
    "check_password_hash",
    "DEFAULT_METHOD",
    "DEFAULT_PBKDF2_ITERATIONS",
]
