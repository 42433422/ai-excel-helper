# -*- coding: utf-8 -*-
"""
数据分析服务
为 AI生态提供文件解析、统计分析和图表数据生成服务
"""
import os
import uuid
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from app.utils.path_utils import get_upload_dir


class DataAnalysisService:
    """数据分析核心服务"""

    def analyze_file(self, file_path: str, query: str = "") -> Dict[str, Any]:
        """分析上传的文件并根据查询生成结果"""
        try:
            df = self._load_file(file_path)
            if df is None or df.empty:
                return {"success": False, "message": "无法读取文件或文件为空"}

            result = {
                "success": True,
                "file_info": {
                    "rows": len(df),
                    "columns": list(df.columns),
                    "shape": df.shape,
                },
                "statistics": self._generate_statistics(df),
                "chart_data": self._generate_chart_data(df, query),
                "insights": self._generate_insights(df, query),
                "download_url": f"/api/ai/analyze/export/{uuid.uuid4().hex[:12]}"
            }
            return result
        except Exception as e:
            return {"success": False, "message": f"分析失败: {str(e)}"}

    def _load_file(self, file_path: str) -> Optional[pd.DataFrame]:
        """加载不同格式的文件"""
        path = Path(file_path)
        suffix = path.suffix.lower()

        try:
            if suffix in ['.xlsx', '.xls']:
                return pd.read_excel(file_path)
            elif suffix == '.csv':
                return pd.read_csv(file_path)
            elif suffix == '.json':
                return pd.read_json(file_path)
            elif suffix == '.txt':
                # 尝试作为CSV读取
                return pd.read_csv(file_path, sep='\t')
            else:
                return None
        except Exception:
            return None

    def _generate_statistics(self, df: pd.DataFrame) -> Dict:
        """生成基础统计信息"""
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        stats = {}

        for col in numeric_cols[:5]:  # 限制数量
            stats[col] = {
                "mean": float(df[col].mean()) if not df[col].empty else 0,
                "sum": float(df[col].sum()) if not df[col].empty else 0,
                "min": float(df[col].min()) if not df[col].empty else 0,
                "max": float(df[col].max()) if not df[col].empty else 0,
            }

        return stats

    def _generate_chart_data(self, df: pd.DataFrame, query: str) -> Dict:
        """生成适合 Chart.js 的图表数据"""
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        if not numeric_cols:
            return {"type": "bar", "labels": [], "datasets": []}

        # 简单趋势图
        if len(numeric_cols) > 0:
            col = numeric_cols[0]
            labels = list(range(1, min(11, len(df) + 1)))
            values = df[col].head(10).tolist()

            return {
                "type": "line",
                "labels": labels,
                "datasets": [{
                    "label": col,
                    "data": values,
                    "borderColor": "#3b82f6",
                    "backgroundColor": "rgba(59, 130, 246, 0.1)",
                    "tension": 0.4
                }]
            }
        
        return {"type": "bar", "labels": [], "datasets": []}

    def _generate_insights(self, df: pd.DataFrame, query: str) -> List[str]:
        """生成分析洞察"""
        insights = ["数据已成功加载", f"共 {len(df)} 条记录"]
        
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if numeric_cols:
            col = numeric_cols[0]
            insights.append(f"{col} 平均值: {df[col].mean():.2f}")
        
        if "销量" in str(query) or "销售" in str(query):
            insights.append("检测到销量相关分析需求")
        if "ROI" in str(query) or "渠道" in str(query):
            insights.append("检测到ROI/渠道分析需求")
            
        return insights

    def export_to_excel(self, data: Dict, output_path: str) -> bool:
        """导出分析结果为Excel"""
        try:
            # 这里简化实现，实际可根据data生成详细报告
            df = pd.DataFrame({"分析结果": ["导出成功"]})
            df.to_excel(output_path, index=False)
            return True
        except Exception:
            return False


def get_data_analysis_service():
    """获取服务实例"""
    return DataAnalysisService()
