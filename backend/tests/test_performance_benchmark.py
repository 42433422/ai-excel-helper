"""
性能基准测试
目标：建立向量检索性能基准，验证响应时间、并发能力
对标豆包：响应时间 < 500ms，支持 100+ 并发
"""

import pytest
import time
import numpy as np
from typing import List, Dict
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed


@dataclass
class PerformanceMetrics:
    """性能指标"""
    avg_latency_ms: float  # 平均延迟
    p50_latency_ms: float  # P50 延迟
    p95_latency_ms: float  # P95 延迟
    p99_latency_ms: float  # P99 延迟
    max_latency_ms: float  # 最大延迟
    min_latency_ms: float  # 最小延迟
    qps: float  # 每秒查询数
    success_rate: float  # 成功率
    total_requests: int  # 总请求数
    failed_requests: int  # 失败请求数


class PerformanceBenchmark:
    """性能基准测试类"""
    
    def __init__(self, excel_workspace=None):
        self.excel_workspace = excel_workspace
        self.service = None
        self.test_queries = [
            "销售额",
            "销量最高的产品",
            "北京地区销售数据",
            "上个月营收情况",
            "产品对比分析",
        ]
    
    def _get_service(self):
        """懒加载向量检索服务"""
        if self.service is None:
            from backend.excel_vector_app_service import ExcelVectorAppService
            
            if self.excel_workspace:
                self.service = ExcelVectorAppService(workspace_root=str(self.excel_workspace))
                try:
                    self.service.index_excel("sample.xlsx")
                except:
                    pass
            else:
                # 创建最小化服务用于测试
                import tempfile
                self.service = ExcelVectorAppService(workspace_root=tempfile.gettempdir())
        
        return self.service
    
    def single_query_latency(self, query: str) -> float:
        """单次查询延迟（毫秒）"""
        service = self._get_service()
        
        start = time.perf_counter()
        try:
            results = service.search(query, top_k=5)
            latency_ms = (time.perf_counter() - start) * 1000
            return latency_ms
        except Exception as e:
            return -1  # 失败标记
    
    def run_load_test(self, num_requests: int = 100, num_workers: int = 10) -> PerformanceMetrics:
        """
        运行负载测试
        Args:
            num_requests: 总请求数
            num_workers: 并发工人数
        """
        latencies = []
        failed = 0
        
        def worker(query_idx: int):
            query = self.test_queries[query_idx % len(self.test_queries)]
            latency = self.single_query_latency(query)
            return latency
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker, i) for i in range(num_requests)]
            
            for future in as_completed(futures):
                try:
                    latency = future.result()
                    if latency > 0:
                        latencies.append(latency)
                    else:
                        failed += 1
                except:
                    failed += 1
        
        if not latencies:
            return PerformanceMetrics(
                avg_latency_ms=0, p50_latency_ms=0, p95_latency_ms=0,
                p99_latency_ms=0, max_latency_ms=0, min_latency_ms=0,
                qps=0, success_rate=0, total_requests=num_requests,
                failed_requests=failed
            )
        
        latencies.sort()
        total_time = sum(latencies) / 1000  # 转换为秒
        
        return PerformanceMetrics(
            avg_latency_ms=np.mean(latencies),
            p50_latency_ms=latencies[int(len(latencies) * 0.50)],
            p95_latency_ms=latencies[int(len(latencies) * 0.95)],
            p99_latency_ms=latencies[int(len(latencies) * 0.99)],
            max_latency_ms=max(latencies),
            min_latency_ms=min(latencies),
            qps=num_requests / total_time if total_time > 0 else 0,
            success_rate=(num_requests - failed) / num_requests,
            total_requests=num_requests,
            failed_requests=failed
        )
    
    def run_scale_test(self) -> Dict[int, PerformanceMetrics]:
        """
        运行规模测试（不同数据量下的性能）
        Returns:
            {数据量：性能指标}
        """
        results = {}
        
        # 这里简化处理，实际应该测试不同规模的索引
        for scale in [100, 1000, 10000]:
            metrics = self.run_load_test(num_requests=50, num_workers=5)
            results[scale] = metrics
        
        return results


class TestPerformanceBenchmark:
    """性能基准测试"""
    
    def test_TC_PERF_001_single_query_latency(self):
        """
        用例模块：性能测试 - 单次查询延迟
        用例标题：测试单次查询的响应时间
        前置条件：向量检索服务已初始化
        操作步骤：
            1. 执行查询"销售额"
            2. 记录响应时间
            3. 重复 10 次取平均
        预期结果：
            - 平均延迟 < 100ms
            - 最大延迟 < 500ms
        用例级别：P0
        备注：基础性能指标
        """
        benchmark = PerformanceBenchmark()
        
        latencies = []
        for _ in range(10):
            latency = benchmark.single_query_latency("销售额")
            if latency > 0:
                latencies.append(latency)
        
        assert len(latencies) > 0, "所有查询都失败"
        
        avg_latency = np.mean(latencies)
        max_latency = max(latencies)
        
        print(f"\n=== 单次查询延迟测试 ===")
        print(f"平均延迟：{avg_latency:.2f}ms (要求 < 100ms)")
        print(f"最大延迟：{max_latency:.2f}ms (要求 < 500ms)")
        
        assert avg_latency < 100, f"平均延迟超标：{avg_latency:.2f}ms > 100ms"
        assert max_latency < 500, f"最大延迟超标：{max_latency:.2f}ms > 500ms"
    
    def test_TC_PERF_002_concurrent_load(self):
        """
        用例模块：性能测试 - 并发负载
        用例标题：测试 100 并发下的性能表现
        前置条件：向量检索服务已初始化
        操作步骤：
            1. 启动 100 个并发请求
            2. 记录各项性能指标
            3. 验证 P99 延迟和成功率
        预期结果：
            - P99 延迟 < 500ms
            - 成功率 > 99%
            - QPS > 50
        用例级别：P0
        备注：核心并发指标
        """
        benchmark = PerformanceBenchmark()
        metrics = benchmark.run_load_test(num_requests=100, num_workers=10)
        
        print(f"\n=== 并发负载测试结果 ===")
        print(f"总请求数：{metrics.total_requests}")
        print(f"失败请求数：{metrics.failed_requests}")
        print(f"成功率：{metrics.success_rate:.2%} (要求 > 99%)")
        print(f"平均延迟：{metrics.avg_latency_ms:.2f}ms")
        print(f"P50 延迟：{metrics.p50_latency_ms:.2f}ms")
        print(f"P95 延迟：{metrics.p95_latency_ms:.2f}ms")
        print(f"P99 延迟：{metrics.p99_latency_ms:.2f}ms (要求 < 500ms)")
        print(f"QPS: {metrics.qps:.2f} (要求 > 50)")
        
        assert metrics.success_rate > 0.99, f"成功率过低：{metrics.success_rate:.2%}"
        assert metrics.p99_latency_ms < 500, f"P99 延迟超标：{metrics.p99_latency_ms:.2f}ms"
        assert metrics.qps > 50, f"QPS 过低：{metrics.qps:.2f}"
    
    def test_TC_PERF_003_latency_distribution(self):
        """
        用例模块：性能测试 - 延迟分布
        用例标题：测试延迟分布的合理性
        前置条件：已运行负载测试
        操作步骤：
            1. 分析延迟分布
            2. 验证 P99/P50 比率
            3. 验证延迟稳定性
        预期结果：
            - P99/P50 比率 < 5（分布不过于分散）
            - 最大/最小比率 < 20
        用例级别：P1
        备注：延迟稳定性
        """
        benchmark = PerformanceBenchmark()
        metrics = benchmark.run_load_test(num_requests=50, num_workers=5)
        
        p99_p50_ratio = metrics.p99_latency_ms / metrics.p50_latency_ms if metrics.p50_latency_ms > 0 else float('inf')
        max_min_ratio = metrics.max_latency_ms / metrics.min_latency_ms if metrics.min_latency_ms > 0 else float('inf')
        
        print(f"\n=== 延迟分布分析 ===")
        print(f"P99/P50 比率：{p99_p50_ratio:.2f} (要求 < 5)")
        print(f"最大/最小比率：{max_min_ratio:.2f} (要求 < 20)")
        
        assert p99_p50_ratio < 5, f"延迟分布过于分散：P99/P50={p99_p50_ratio:.2f}"
        assert max_min_ratio < 20, f"延迟波动过大：Max/Min={max_min_ratio:.2f}"
    
    def test_TC_PERF_004_high_concurrency_stress(self):
        """
        用例模块：性能测试 - 高压并发
        用例标题：测试 100 并发压力下的稳定性
        前置条件：向量检索服务已初始化
        操作步骤：
            1. 启动 100 个并发工
            2. 发送 200 个请求
            3. 检查系统稳定性
        预期结果：
            - 无崩溃
            - 成功率 > 95%
            - P99 延迟 < 1000ms
        用例级别：P1
        备注：压力测试
        """
        benchmark = PerformanceBenchmark()
        metrics = benchmark.run_load_test(num_requests=200, num_workers=100)
        
        print(f"\n=== 高压并发测试结果 ===")
        print(f"并发工人数：100")
        print(f"总请求数：200")
        print(f"成功率：{metrics.success_rate:.2%} (要求 > 95%)")
        print(f"P99 延迟：{metrics.p99_latency_ms:.2f}ms (要求 < 1000ms)")
        
        assert metrics.success_rate > 0.95, f"高压下成功率过低：{metrics.success_rate:.2%}"
        assert metrics.p99_latency_ms < 1000, f"高压下 P99 延迟超标：{metrics.p99_latency_ms:.2f}ms"


if __name__ == "__main__":
    print("="*60)
    print("性能基准测试报告")
    print("="*60)
    
    benchmark = PerformanceBenchmark()
    
    # 单次查询测试
    print("\n【单次查询延迟测试】")
    latencies = []
    for _ in range(10):
        latency = benchmark.single_query_latency("销售额")
        if latency > 0:
            latencies.append(latency)
    
    if latencies:
        print(f"平均延迟：{np.mean(latencies):.2f}ms")
        print(f"最大延迟：{max(latencies):.2f}ms")
    
    # 并发负载测试
    print("\n【并发负载测试】")
    metrics = benchmark.run_load_test(num_requests=100, num_workers=10)
    print(f"成功率：{metrics.success_rate:.2%}")
    print(f"P99 延迟：{metrics.p99_latency_ms:.2f}ms")
    print(f"QPS: {metrics.qps:.2f}")
    
    print("\n" + "="*60)
