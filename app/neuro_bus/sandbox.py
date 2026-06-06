"""
沙盒预演（Sandbox）

事件模拟执行，预检副作用
支持：
- 虚拟执行环境
- 副作用记录
- 预检报告生成
"""

import copy
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.neuro_bus.events.base import NeuroEvent

logger = logging.getLogger(__name__)


class SideEffectType(Enum):
    """副作用类型"""

    READ = "read"  # 读取操作（安全）
    WRITE = "write"  # 写操作（危险）
    DELETE = "delete"  # 删除（危险）
    EXTERNAL_CALL = "external_call"  # 外部调用
    PAYMENT = "payment"  # 支付操作（高危）
    NOTIFICATION = "notification"  # 通知发送


@dataclass
class SideEffect:
    """副作用记录"""

    effect_type: SideEffectType
    target: str  # 操作目标
    description: str
    data: dict[str, Any] = field(default_factory=dict)
    risk_level: int = 1  # 1-5, 5最高危


@dataclass
class SandboxReport:
    """沙盒预检报告"""

    event_id: str
    event_type: str
    can_execute: bool
    risk_score: float  # 0-100
    side_effects: list[SideEffect]
    warnings: list[str]
    recommendations: list[str]


class SandboxContext:
    """
    沙盒执行上下文

    模拟真实执行环境，捕获所有副作用
    """

    def __init__(self, event: NeuroEvent):
        self._event = copy.deepcopy(event)  # 深拷贝防止污染
        self._side_effects: list[SideEffect] = []
        self._virtual_storage: dict[str, Any] = {}
        self._executed = False

    # 虚拟操作

    def virtual_read(self, key: str) -> Any:
        """模拟读取"""
        self._side_effects.append(
            SideEffect(
                effect_type=SideEffectType.READ,
                target=key,
                description=f"Read from {key}",
                risk_level=1,
            )
        )
        return self._virtual_storage.get(key)

    def virtual_write(self, key: str, value: Any):
        """模拟写入"""
        old_value = self._virtual_storage.get(key)
        self._virtual_storage[key] = value

        self._side_effects.append(
            SideEffect(
                effect_type=SideEffectType.WRITE,
                target=key,
                description=f"Write to {key}: {old_value} -> {value}",
                data={"old": old_value, "new": value},
                risk_level=2,
            )
        )

    def virtual_delete(self, key: str):
        """模拟删除"""
        old_value = self._virtual_storage.pop(key, None)

        self._side_effects.append(
            SideEffect(
                effect_type=SideEffectType.DELETE,
                target=key,
                description=f"Delete {key}: {old_value}",
                data={"deleted": old_value},
                risk_level=4,
            )
        )

    def virtual_payment(self, amount: float, currency: str = "CNY"):
        """模拟支付"""
        self._side_effects.append(
            SideEffect(
                effect_type=SideEffectType.PAYMENT,
                target="payment_gateway",
                description=f"Payment {amount} {currency}",
                data={"amount": amount, "currency": currency},
                risk_level=5,
            )
        )

    def virtual_notify(self, channel: str, message: str):
        """模拟通知"""
        self._side_effects.append(
            SideEffect(
                effect_type=SideEffectType.NOTIFICATION,
                target=channel,
                description=f"Send notification via {channel}",
                data={"channel": channel, "message": message},
                risk_level=2,
            )
        )

    def virtual_external_call(self, service: str, endpoint: str, data: Any):
        """模拟外部调用"""
        self._side_effects.append(
            SideEffect(
                effect_type=SideEffectType.EXTERNAL_CALL,
                target=f"{service}.{endpoint}",
                description=f"Call {service}.{endpoint}",
                data={"service": service, "endpoint": endpoint, "payload": data},
                risk_level=3,
            )
        )

    def get_event(self) -> NeuroEvent:
        """获取事件副本"""
        return self._event

    def get_side_effects(self) -> list[SideEffect]:
        """获取副作用列表"""
        return self._side_effects.copy()


class Sandbox:
    """
    沙盒预演器

    在虚拟环境中执行操作，分析副作用
    """

    def __init__(self):
        self._simulators: dict[str, Callable[[SandboxContext], None]] = {}

    def register_simulator(self, event_type: str, simulator: Callable[[SandboxContext], None]):
        """
        注册事件模拟器

        模拟器在沙盒环境中执行，使用 context 的虚拟操作
        """
        self._simulators[event_type] = simulator

    def simulate(self, event: NeuroEvent) -> SandboxReport:
        """
        预演事件处理

        Returns:
            预检报告
        """
        context = SandboxContext(event)

        # 查找模拟器
        simulator = self._simulators.get(event.event_type)

        if not simulator:
            # 没有模拟器，返回未知风险报告
            return SandboxReport(
                event_id=event.metadata.event_id,
                event_type=event.event_type,
                can_execute=True,  # 默认可执行
                risk_score=50.0,  # 中等风险
                side_effects=[],
                warnings=["No simulator registered for this event type"],
                recommendations=["Consider adding a simulator for better safety"],
            )

        # 执行模拟
        try:
            simulator(context)
        except Exception as e:
            logger.exception(f"Sandbox simulation error: {e}")
            return SandboxReport(
                event_id=event.metadata.event_id,
                event_type=event.event_type,
                can_execute=False,
                risk_score=100.0,
                side_effects=context.get_side_effects(),
                warnings=[f"Simulation failed: {e}"],
                recommendations=["Review event handler implementation"],
            )

        # 分析副作用
        side_effects = context.get_side_effects()

        # 计算风险分数
        max_risk = max((e.risk_level for e in side_effects), default=1)
        risk_score = (max_risk / 5.0) * 100  # 归一化到 0-100

        # 生成警告和建议
        warnings = []
        recommendations = []
        can_execute = True

        for effect in side_effects:
            if effect.effect_type == SideEffectType.PAYMENT:
                warnings.append(f"Payment operation detected: {effect.description}")
                recommendations.append("Verify payment amount and recipient")

            if effect.effect_type == SideEffectType.DELETE:
                warnings.append(f"Data deletion: {effect.target}")
                recommendations.append("Ensure data backup exists")

            if effect.risk_level >= 4:
                can_execute = False
                warnings.append("High-risk operation detected")

        return SandboxReport(
            event_id=event.metadata.event_id,
            event_type=event.event_type,
            can_execute=can_execute,
            risk_score=risk_score,
            side_effects=side_effects,
            warnings=warnings,
            recommendations=recommendations,
        )

    def validate(self, event: NeuroEvent, max_risk_score: float = 70.0) -> bool:
        """
        快速验证事件是否可执行

        Args:
            max_risk_score: 最大可接受风险分数

        Returns:
            True: 通过验证
            False: 风险过高
        """
        report = self.simulate(event)

        if not report.can_execute:
            logger.warning(f"Sandbox validation failed: {report.warnings}")
            return False

        if report.risk_score > max_risk_score:
            logger.warning(f"Risk score {report.risk_score} exceeds threshold {max_risk_score}")
            return False

        return True


class NeuroSandbox:
    """
    NeuroBus 集成沙盒

    为关键事件提供预检能力
    """

    HIGH_RISK_DOMAINS = {"payment", "safety", "delete"}

    def __init__(self):
        self._sandbox = Sandbox()

    def should_prescreen(self, event: NeuroEvent) -> bool:
        """判断是否需要预检"""
        # 高危领域
        if event.metadata.domain in self.HIGH_RISK_DOMAINS:
            return True

        # 特定模式
        if any(p in event.event_type.lower() for p in ["payment", "delete", "refund"]):
            return True

        return False

    def prescreen(self, event: NeuroEvent) -> SandboxReport | None:
        """预检事件"""
        if not self.should_prescreen(event):
            return None

        report = self._sandbox.simulate(event)

        if not report.can_execute or report.risk_score > 70:
            logger.error(
                f"Event {event.event_type} failed prescreening: "
                f"risk={report.risk_score}, warnings={report.warnings}"
            )

        return report

    def register_simulator(self, event_type: str, simulator: Callable):
        """注册模拟器"""
        self._sandbox.register_simulator(event_type, simulator)

    def validate(self, event: NeuroEvent) -> bool:
        """验证事件"""
        if not self.should_prescreen(event):
            return True
        return self._sandbox.validate(event)
