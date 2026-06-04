"""Facade shim for the Rasa NLU service.

This module re-exports the implementation from
`app.ai_engines.rasa.nlu_service` and acts as a thin compatibility facade
for call sites under `app.services.*`.

Do not add new logic here; update the authoritative implementation in
`app.ai_engines.rasa.nlu_service`.
"""

from __future__ import annotations

from app.ai_engines.rasa.nlu_service import RasaNLUService, get_rasa_nlu_service

__all__ = ["RasaNLUService", "get_rasa_nlu_service"]

# Re-apply instrumentation wrapper for services layer (keeps existing telemetry)
from app.neuro_bus.neuro_service_instrumentation import instrument_service_layer_class

instrument_service_layer_class(RasaNLUService, "app.services.rasa_nlu_service")
