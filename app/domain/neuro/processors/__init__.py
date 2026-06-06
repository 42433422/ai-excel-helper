"""神经处理器"""

from app.domain.neuro.processors.conscious import ConsciousProcessor
from app.domain.neuro.processors.coordinator import ProcessorCoordinator, ProcessorType
from app.domain.neuro.processors.subconscious import SubconsciousProcessor

__all__ = [
    "SubconsciousProcessor",
    "ConsciousProcessor",
    "ProcessorCoordinator",
    "ProcessorType",
]
