"""
Print 领域事件定义

包含打印功能的所有领域事件。
"""

from dataclasses import dataclass

from app.neuro_bus.events.base import EventPriority, NeuroEvent


@dataclass
class PrintJobSubmittedEvent(NeuroEvent):
    """打印任务提交事件"""

    event_type: str = "print.job_submitted"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["job_id", "document_id", "printer_id", "copies"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"PrintJobSubmittedEvent 缺少必要字段: {field}")


@dataclass
class PrintJobStartedEvent(NeuroEvent):
    """打印任务开始事件"""

    event_type: str = "print.job_started"
    priority: EventPriority = EventPriority.LOW

    def __post_init__(self):
        super().__post_init__()
        if "job_id" not in self.payload:
            raise ValueError("PrintJobStartedEvent 缺少必要字段: job_id")


@dataclass
class PrintJobCompletedEvent(NeuroEvent):
    """打印任务完成事件"""

    event_type: str = "print.job_completed"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["job_id", "pages_printed", "print_time"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"PrintJobCompletedEvent 缺少必要字段: {field}")


@dataclass
class PrintJobFailedEvent(NeuroEvent):
    """打印任务失败事件"""

    event_type: str = "print.job_failed"
    priority: EventPriority = EventPriority.HIGH

    def __post_init__(self):
        super().__post_init__()
        required = ["job_id", "error_code", "error_message"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"PrintJobFailedEvent 缺少必要字段: {field}")


@dataclass
class PrinterStatusChangedEvent(NeuroEvent):
    """打印机状态变更事件"""

    event_type: str = "print.printer_status_changed"
    priority: EventPriority = EventPriority.HIGH

    def __post_init__(self):
        super().__post_init__()
        required = ["printer_id", "old_status", "new_status"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"PrinterStatusChangedEvent 缺少必要字段: {field}")


@dataclass
class LabelPrintRequestEvent(NeuroEvent):
    """标签打印请求事件"""

    event_type: str = "print.label_requested"
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        super().__post_init__()
        required = ["label_id", "product_id", "quantity", "printer_id"]
        for field in required:
            if field not in self.payload:
                raise ValueError(f"LabelPrintRequestEvent 缺少必要字段: {field}")
