"""
OCR 领域事件定义

包含 OCR 识别流程中的所有领域事件。
"""

from dataclasses import dataclass

from app.neuro_bus.events.base import EventPriority, NeuroEvent


@dataclass
class OCRTaskSubmittedEvent(NeuroEvent):
    """OCR 任务提交事件"""

    event_type: str = "ocr.task_submitted"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["task_id", "image_url", "ocr_type"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"OCRTaskSubmittedEvent 缺少必要字段: {field}")


@dataclass
class OCRTaskStartedEvent(NeuroEvent):
    """OCR 任务开始处理事件"""

    event_type: str = "ocr.task_started"
    priority: EventPriority = EventPriority.LOW

    def __post_init__(self):
        super().__post_init__()
        if "task_id" not in self.payload:
            raise ValueError("OCRTaskStartedEvent 缺少必要字段: task_id")


@dataclass
class OCRTaskCompletedEvent(NeuroEvent):
    """OCR 任务完成事件"""

    event_type: str = "ocr.task_completed"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["task_id", "result", "confidence"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"OCRTaskCompletedEvent 缺少必要字段: {field}")


@dataclass
class OCRTaskFailedEvent(NeuroEvent):
    """OCR 任务失败事件"""

    event_type: str = "ocr.task_failed"
    priority: EventPriority = EventPriority.HIGH

    def __post_init__(self):
        super().__post_init__()
        required = ["task_id", "error_code", "error_message"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"OCRTaskFailedEvent 缺少必要字段: {field}")


@dataclass
class OCRResultValidatedEvent(NeuroEvent):
    """OCR 结果人工验证事件"""

    event_type: str = "ocr.result_validated"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["task_id", "validated_by", "is_correct", "corrections"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"OCRResultValidatedEvent 缺少必要字段: {field}")


@dataclass
class OCRBatchProcessingCompletedEvent(NeuroEvent):
    """OCR 批量处理完成事件"""

    event_type: str = "ocr.batch_completed"
    priority: EventPriority = EventPriority.LOW

    def __post_init__(self):
        super().__post_init__()
        required = ["batch_id", "total_count", "success_count", "failed_count"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"OCRBatchProcessingCompletedEvent 缺少必要字段: {field}")
