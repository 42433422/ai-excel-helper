"""Minimal workflow sandbox validation for CI / slim MODstore_server checkout."""

from __future__ import annotations

from typing import Any, List, Optional

from sqlalchemy.orm import Session


def validate_workflow_sandbox_ready(
    db: Session,
    *,
    workflow_id: int,
    user_id: Optional[int] = None,
) -> List[str]:
    del db, workflow_id, user_id
    return []
