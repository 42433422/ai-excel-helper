"""移动端推送：FCM + 极光 JPush（可选，无密钥时静默跳过）。"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


def _jpush_enabled() -> bool:
    return bool(
        (os.environ.get("JPUSH_APP_KEY") or "").strip()
        and (os.environ.get("JPUSH_MASTER_SECRET") or "").strip()
    )


def _fcm_enabled() -> bool:
    return bool(
        os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
        or os.environ.get("FIREBASE_SERVICE_ACCOUNT")
    )


def send_jpush(
    registration_ids: List[str],
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
) -> bool:
    if not registration_ids or not _jpush_enabled():
        return False
    app_key = os.environ["JPUSH_APP_KEY"].strip()
    master_secret = os.environ["JPUSH_MASTER_SECRET"].strip()
    payload = {
        "platform": "android",
        "audience": {"registration_id": registration_ids},
        "notification": {
            "android": {
                "alert": body,
                "title": title,
                "extras": data or {},
            }
        },
        "message": {
            "msg_content": body,
            "title": title,
            "extras": data or {},
        },
    }
    try:
        r = httpx.post(
            "https://api.jpush.cn/v3/push",
            auth=(app_key, master_secret),
            json=payload,
            timeout=15.0,
        )
        if r.status_code >= 400:
            logger.warning("jpush failed: %s %s", r.status_code, r.text[:500])
            return False
        return True
    except Exception as exc:
        logger.warning("jpush error: %s", exc)
        return False


def send_fcm(
    tokens: List[str],
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
) -> bool:
    if not tokens or not _fcm_enabled():
        return False
    try:
        import google.oauth2.service_account
        from google.auth.transport.requests import Request
    except ImportError:
        logger.warning("google-auth not installed; skip FCM")
        return False

    cred_path = (
        os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
        or os.environ.get("FIREBASE_SERVICE_ACCOUNT")
        or ""
    ).strip()
    if not cred_path or not os.path.isfile(cred_path):
        logger.warning("FIREBASE_SERVICE_ACCOUNT_JSON not a file: %s", cred_path)
        return False

    try:
        creds = google.oauth2.service_account.Credentials.from_service_account_file(
            cred_path,
            scopes=["https://www.googleapis.com/auth/firebase.messaging"],
        )
        creds.refresh(Request())
        access_token = creds.token
        project_id = json.load(open(cred_path, encoding="utf-8")).get("project_id")
        if not project_id:
            return False
        url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
        ok_any = False
        str_data = {k: str(v) for k, v in (data or {}).items()}
        for token in tokens[:500]:
            msg = {
                "message": {
                    "token": token,
                    "notification": {"title": title, "body": body},
                    "data": str_data,
                }
            }
            r = httpx.post(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                json=msg,
                timeout=15.0,
            )
            if r.status_code < 400:
                ok_any = True
            else:
                logger.warning("fcm token fail: %s", r.text[:300])
        return ok_any
    except Exception as exc:
        logger.warning("fcm error: %s", exc)
        return False


def send_to_user_devices(
    devices: List[Dict[str, Any]],
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, bool]:
    """devices: rows with push_provider, push_token (or legacy fcm_token)."""
    fcm_tokens: List[str] = []
    jpush_ids: List[str] = []
    for d in devices:
        provider = (d.get("push_provider") or "fcm").strip().lower()
        tok = (d.get("push_token") or d.get("fcm_token") or "").strip()
        if not tok:
            continue
        if provider == "jpush":
            jpush_ids.append(tok)
        else:
            fcm_tokens.append(tok)
    return {
        "fcm": send_fcm(fcm_tokens, title, body, data),
        "jpush": send_jpush(jpush_ids, title, body, data),
    }


def notify_user(
    user_id: int, title: str, body: str, data: Optional[Dict[str, Any]] = None
) -> Dict[str, bool]:
    from app.db.models.mobile_device import MobileDeviceToken
    from app.db.session import get_db

    with get_db() as db:
        rows = db.query(MobileDeviceToken).filter(MobileDeviceToken.user_id == user_id).all()
        devices = [
            {
                "push_provider": getattr(r, "push_provider", None) or "fcm",
                "push_token": getattr(r, "push_token", None) or r.fcm_token,
                "fcm_token": r.fcm_token,
            }
            for r in rows
        ]
    return send_to_user_devices(devices, title, body, data)
