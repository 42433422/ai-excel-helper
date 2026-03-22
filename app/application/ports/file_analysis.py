from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class FileAnalysisPort(ABC):
    """文件分析端口"""

    @abstractmethod
    def analyze_file(
        self,
        upload_file,
        purpose: str = "general"
    ) -> Dict[str, Any]:
        raise NotImplementedError
