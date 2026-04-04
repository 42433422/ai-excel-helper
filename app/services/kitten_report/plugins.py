# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import mean
from typing import Any, Dict, List


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _extract_numeric_values(dataset: Dict[str, Any]) -> List[float]:
    preview = dataset.get("preview") or []
    values: List[float] = []
    for row in preview:
        if isinstance(row, list):
            for item in row:
                parsed = _safe_float(item)
                if parsed is not None:
                    values.append(parsed)
        elif isinstance(row, dict):
            for item in row.values():
                parsed = _safe_float(item)
                if parsed is not None:
                    values.append(parsed)
    return values


@dataclass
class PluginResult:
    key: str
    title: str
    level: str
    summary: str
    details: Dict[str, Any]


class AnalysisPlugin:
    key = "plugin"
    title = "基础插件"

    def run(self, payload: Dict[str, Any]) -> PluginResult:
        return PluginResult(
            key=self.key,
            title=self.title,
            level="info",
            summary="无分析结果",
            details={},
        )


class RuleStatsPlugin(AnalysisPlugin):
    key = "rule_stats"
    title = "规则统计分析"

    def run(self, payload: Dict[str, Any]) -> PluginResult:
        dataset = payload.get("dataset") or {}
        messages = payload.get("messages") or []
        rows = int(dataset.get("rows") or 0)
        cols = int(dataset.get("columns") or 0)
        user_count = sum(1 for x in messages if str((x or {}).get("role", "")) == "user")
        ai_count = sum(1 for x in messages if str((x or {}).get("role", "")) == "ai")

        summary = f"数据规模 {rows} 行 / {cols} 列；对话轮次 用户 {user_count} / AI {ai_count}。"
        return PluginResult(
            key=self.key,
            title=self.title,
            level="info",
            summary=summary,
            details={
                "rows": rows,
                "columns": cols,
                "user_messages": user_count,
                "ai_messages": ai_count,
            },
        )


class ForecastHeuristicPlugin(AnalysisPlugin):
    key = "forecast_heuristic"
    title = "预测启发式模型"

    def run(self, payload: Dict[str, Any]) -> PluginResult:
        dataset = payload.get("dataset") or {}
        values = _extract_numeric_values(dataset)
        if not values:
            return PluginResult(
                key=self.key,
                title=self.title,
                level="warn",
                summary="未检测到可用于预测的数值字段，跳过趋势预测。",
                details={"forecast_available": False},
            )

        avg = mean(values)
        forecast = round(avg * 1.05, 4)
        summary = f"基于预览数值均值 {avg:.4f} 做简单外推，下阶段参考值约 {forecast:.4f}。"
        return PluginResult(
            key=self.key,
            title=self.title,
            level="info",
            summary=summary,
            details={
                "forecast_available": True,
                "mean": round(avg, 4),
                "next_period_estimate": forecast,
                "method": "mean*1.05",
            },
        )


class TimeSeriesModelPlugin(AnalysisPlugin):
    key = "timeseries_model"
    title = "时间序列模型插件"

    @staticmethod
    def _build_series(values: List[float]) -> List[Dict[str, Any]]:
        base_date = datetime.now().date() - timedelta(days=max(len(values) - 1, 0))
        points: List[Dict[str, Any]] = []
        for idx, value in enumerate(values):
            points.append({
                "ds": (base_date + timedelta(days=idx)).isoformat(),
                "y": float(value),
            })
        return points

    def _run_prophet(self, values: List[float]) -> Dict[str, Any] | None:
        try:
            import pandas as pd
            from prophet import Prophet
        except Exception:
            return None
        if len(values) < 3:
            return None
        points = self._build_series(values)
        df = pd.DataFrame(points)
        model = Prophet(daily_seasonality=False, weekly_seasonality=False, yearly_seasonality=False)
        model.fit(df)
        future = model.make_future_dataframe(periods=1)
        forecast = model.predict(future)
        yhat = float(forecast["yhat"].iloc[-1])
        return {
            "method": "prophet",
            "forecast": round(yhat, 4),
            "points": len(values),
        }

    def _run_arima(self, values: List[float]) -> Dict[str, Any] | None:
        try:
            import numpy as np
            from statsmodels.tsa.arima.model import ARIMA
        except Exception:
            return None
        if len(values) < 4:
            return None
        arr = np.array(values, dtype=float)
        # 小样本固定阶数，避免自动寻参依赖过重且训练不稳定。
        model = ARIMA(arr, order=(1, 1, 1))
        fitted = model.fit()
        pred = fitted.forecast(steps=1)
        yhat = float(pred[0])
        return {
            "method": "arima(1,1,1)",
            "forecast": round(yhat, 4),
            "points": len(values),
        }

    def run(self, payload: Dict[str, Any]) -> PluginResult:
        dataset = payload.get("dataset") or {}
        values = _extract_numeric_values(dataset)
        if len(values) < 3:
            return PluginResult(
                key=self.key,
                title=self.title,
                level="warn",
                summary="样本点不足（至少3个）或未识别到数值字段，无法运行 Prophet/ARIMA。",
                details={"forecast_available": False, "required_points": 3, "actual_points": len(values)},
            )

        prophet_result = self._run_prophet(values)
        if prophet_result:
            return PluginResult(
                key=self.key,
                title=self.title,
                level="info",
                summary=f"使用 Prophet 完成预测，下阶段参考值约 {prophet_result['forecast']:.4f}。",
                details={**prophet_result, "engine": "prophet"},
            )

        arima_result = self._run_arima(values)
        if arima_result:
            return PluginResult(
                key=self.key,
                title=self.title,
                level="info",
                summary=f"使用 ARIMA 完成预测，下阶段参考值约 {arima_result['forecast']:.4f}。",
                details={**arima_result, "engine": "arima"},
            )

        return PluginResult(
            key=self.key,
            title=self.title,
            level="warn",
            summary="当前环境未安装 Prophet/ARIMA 依赖，已跳过模型预测。",
            details={
                "forecast_available": False,
                "missing": ["prophet or statsmodels"],
                "fallback": "heuristic",
            },
        )


class IndustryStrategyPlugin(AnalysisPlugin):
    key = "industry_strategy"
    title = "行业策略插件"

    _industry_hints = {
        "涂料": "重点关注型号规格与桶数匹配，建议复核单位换算。",
        "油漆": "重点关注颜色/批次字段，建议增加批次追溯。",
        "电商": "建议补充渠道维度，便于 ROI 归因。",
        "零售": "建议按门店与SKU拆分趋势。",
        "餐饮": "建议关注损耗率与补货周期。",
        "物流": "建议关注运输时效与异常签收。",
    }

    def run(self, payload: Dict[str, Any]) -> PluginResult:
        industry = str(payload.get("industry") or "通用").strip()
        hint = "通用策略：建议补充时间字段，支持趋势与预测分析。"
        for key, value in self._industry_hints.items():
            if key in industry:
                hint = value
                break
        return PluginResult(
            key=self.key,
            title=self.title,
            level="info",
            summary=f"当前行业：{industry}。{hint}",
            details={"industry": industry, "hint": hint},
        )
