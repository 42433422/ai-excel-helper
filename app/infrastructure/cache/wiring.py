from app.domain.ports.cache_port import set_intent_cache
from app.infrastructure.cache import get_intent_cache


def wire_cache_port() -> None:
    set_intent_cache(get_intent_cache())
