"""在 Service / Mixin 上复用的 NeuroBus 领域事件发布逻辑。"""

from __future__ import annotations

import logging
from typing import Any

from app.neuro_bus.bus import get_neuro_bus
from app.neuro_bus.events.base import EventPriority, NeuroEvent

logger = logging.getLogger(__name__)


class NeuroEventPublisherMixin:
    """为服务类提供统一的 ``_publish_event``，避免各处复制粘贴。"""

    def _publish_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        priority: EventPriority | None = None,
    ) -> str:
        if priority is None:
            priority = EventPriority.NORMAL
        try:
            bus = get_neuro_bus()
            event = NeuroEvent(
                event_type=event_type,
                payload=payload,
                source=self.__class__.__name__,
                priority=priority,
            )
            bus.publish(event)
            return event.metadata.event_id
        except Exception as e:
            logger.warning("发布事件失败 %s: %s", event_type, e)
            return ""
