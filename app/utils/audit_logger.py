import json
import logging
from datetime import datetime, timezone

_audit_logger = logging.getLogger("audit")
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(message)s"))
_audit_logger.addHandler(_handler)
_audit_logger.setLevel(logging.INFO)


def audit_log(event_type: str, user_id, ip_address, details, success: bool = True):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "user_id": user_id,
        "ip_address": ip_address,
        "details": details,
        "success": success,
    }
    _audit_logger.info(json.dumps(entry, ensure_ascii=False, default=str))
