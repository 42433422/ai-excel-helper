"""XCMAX 同步应用层门面。"""

from __future__ import annotations

from typing import Any


def push_outbox(*, remote_host: str, remote_port: int) -> Any:
    from app.services.xcmax_sync_service import push_outbox as _push

    return _push(remote_host=remote_host, remote_port=remote_port)


def apply_inbox(limit: int = 200, **kwargs: Any) -> Any:
    from app.services.xcmax_sync_service import apply_inbox as _apply

    return _apply(limit=limit, **kwargs)


def pull_from_remote(*, remote_host: str, remote_port: int, **kwargs: Any) -> Any:
    from app.services.xcmax_sync_service import pull_from_remote as _pull

    return _pull(remote_host=remote_host, remote_port=remote_port, **kwargs)


def entity_appliers():
    from app.services.xcmax_sync_service import _ENTITY_APPLIERS

    return _ENTITY_APPLIERS
