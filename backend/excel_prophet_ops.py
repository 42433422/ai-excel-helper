"""
Prophet: 时间序列趋势预测与基于残差的异常点检测。
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd


def _prepare_prophet_frame(df: pd.DataFrame, date_col: str, y_col: str) -> pd.DataFrame:
    if date_col not in df.columns or y_col not in df.columns:
        raise KeyError(f"missing column: date={date_col!r} value={y_col!r}")
    out = df[[date_col, y_col]].copy()
    out = out.rename(columns={date_col: "ds", y_col: "y"})
    out["ds"] = pd.to_datetime(out["ds"], errors="coerce")
    out["y"] = pd.to_numeric(out["y"], errors="coerce")
    out = out.dropna(subset=["ds", "y"])
    if len(out) < 2:
        raise ValueError("need at least 2 valid (ds, y) rows after cleaning")
    return out


def run_prophet_forecast(
    df: pd.DataFrame,
    date_col: str,
    y_col: str,
    periods: int,
    freq: str | None = None,
) -> dict[str, Any]:
    try:
        from prophet import Prophet
    except ImportError as e:
        return {"error": "prophet_not_installed", "hint": "pip install prophet", "message": str(e)}

    if periods < 1 or periods > 366 * 5:
        return {"error": "invalid_periods", "hint": "use 1..1825"}

    dfp = _prepare_prophet_frame(df, date_col, y_col)
    m = Prophet(daily_seasonality=True, weekly_seasonality=True, yearly_seasonality=True)
    m.fit(dfp)
    kwargs: dict[str, Any] = {"periods": periods}
    if freq:
        kwargs["freq"] = freq
    future = m.make_future_dataframe(**kwargs)
    fc = m.predict(future)
    tail = fc.tail(periods)[["ds", "yhat", "yhat_lower", "yhat_upper"]]
    fitted = fc.merge(dfp, on="ds", how="inner")
    fitted = fitted[["ds", "y", "yhat", "yhat_lower", "yhat_upper"]].tail(min(30, len(fitted)))
    return {
        "action": "forecast",
        "history_points": len(dfp),
        "forecast_periods": periods,
        "future_forecast": json_records(tail),
        "recent_fitted_sample": json_records(fitted),
    }


def run_prophet_anomalies(
    df: pd.DataFrame,
    date_col: str,
    y_col: str,
    sigma: float = 3.0,
    max_anomaly_rows: int = 200,
) -> dict[str, Any]:
    try:
        from prophet import Prophet
    except ImportError as e:
        return {"error": "prophet_not_installed", "hint": "pip install prophet", "message": str(e)}

    if sigma <= 0:
        return {"error": "invalid_sigma"}

    dfp = _prepare_prophet_frame(df, date_col, y_col)
    m = Prophet(daily_seasonality=True, weekly_seasonality=True, yearly_seasonality=True)
    m.fit(dfp)
    fc = m.predict(dfp[["ds"]])
    merged = dfp.merge(fc[["ds", "yhat", "yhat_lower", "yhat_upper"]], on="ds")
    merged["residual"] = (merged["y"] - merged["yhat"]).abs()
    mu = float(merged["residual"].mean())
    std = float(merged["residual"].std()) or 1e-9
    thr = mu + sigma * std
    merged["threshold"] = thr
    merged["is_anomaly"] = merged["residual"] > thr
    anomalies = merged[merged["is_anomaly"]].sort_values("residual", ascending=False)
    total = int(anomalies.shape[0])
    anomalies = anomalies.head(max_anomaly_rows)
    return {
        "action": "anomalies",
        "history_points": len(dfp),
        "residual_mean": mu,
        "residual_std": std,
        "threshold": thr,
        "anomaly_count": total,
        "truncated": total > max_anomaly_rows,
        "anomalies": json_records(
            anomalies.rename(columns={"ds": date_col, "y": y_col})
        ),
    }


def json_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    j = df.replace({np.nan: None}).copy()
    for c in j.select_dtypes(include=["datetime64", "datetimetz"]).columns:
        j[c] = j[c].astype(str)
    return json.loads(j.to_json(orient="records", date_format="iso"))
