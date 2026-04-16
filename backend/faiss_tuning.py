"""
FAISS 索引调优模块
目标：针对不同数据规模选择最优索引参数，平衡检索速度和精度
功能：
    - 自动参数调优
    - 索引类型选择
    - 性能对比测试
    - 精度 - 速度权衡分析
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import time


@dataclass
class IndexConfig:
    """索引配置"""
    index_type: str  # Flat, IVF, HNSW
    nlist: int = 100  # IVF 聚类中心数
    nprobe: int = 10  # IVF 搜索聚类数
    M: int = 32  # HNSW 连接数
    efConstruction: int = 200  # HNSW 构建效率
    efSearch: int = 40  # HNSW 搜索效率


@dataclass
class PerformanceResult:
    """性能测试结果"""
    index_type: str
    build_time_ms: float
    search_time_ms: float
    recall_at_10: float
    memory_usage_mb: float
    index_size_mb: float


class FAISSTuner:
    """FAISS 索引调优器"""
    
    def __init__(self, dimension: int = 512):
        """
        初始化调优器
        Args:
            dimension: 向量维度
        """
        self.dimension = dimension
        self.test_vectors = None
        self.query_vectors = None
        self.ground_truth = None
        
        self.results = []
    
    def prepare_test_data(self, num_vectors: int = 10000, num_queries: int = 100):
        """
        准备测试数据
        Args:
            num_vectors: 向量数量
            num_queries: 查询数量
        """
        try:
            import faiss
        except ImportError:
            raise ImportError("请安装 faiss: pip install faiss-cpu")
        
        # 生成随机向量
        np.random.seed(42)
        self.test_vectors = np.random.rand(num_vectors, self.dimension).astype(np.float32)
        self.query_vectors = np.random.rand(num_queries, self.dimension).astype(np.float32)
        
        # L2 归一化
        faiss.normalize_L2(self.test_vectors)
        faiss.normalize_L2(self.query_vectors)
        
        # 计算真实最近邻（用于评估召回率）
        # 使用精确搜索作为基准
        index_flat = faiss.IndexFlatIP(self.dimension)
        index_flat.add(self.test_vectors)
        
        _, self.ground_truth = index_flat.search(self.query_vectors, k=10)
        
        print(f"测试数据准备完成:")
        print(f"  - 向量数：{num_vectors}")
        print(f"  - 查询数：{num_queries}")
        print(f"  - 维度：{self.dimension}")
    
    def tune_ivf_nlist(self, nlist_candidates: List[int] = None) -> Dict[int, PerformanceResult]:
        """
        调优 IVF 的 nlist 参数
        Args:
            nlist_candidates: 候选 nlist 值列表
        Returns:
            {nlist: 性能结果}
        """
        try:
            import faiss
        except ImportError:
            raise ImportError("请安装 faiss: pip install faiss-cpu")
        
        if nlist_candidates is None:
            # 根据数据量自动选择候选值
            n_vectors = len(self.test_vectors)
            nlist_candidates = [
                int(np.sqrt(n_vectors) * factor) 
                for factor in [0.5, 1.0, 2.0, 4.0]
            ]
            nlist_candidates = [max(10, min(4096, n)) for n in nlist_candidates]
        
        results = {}
        
        for nlist in nlist_candidates:
            print(f"\n测试 IVF nlist={nlist}...")
            
            # 构建索引
            quantizer = faiss.IndexFlatIP(self.dimension)
            index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist, faiss.METRIC_INNER_PRODUCT)
            
            start = time.time()
            index.train(self.test_vectors)
            index.add(self.test_vectors)
            build_time = (time.time() - start) * 1000
            
            # 测试搜索
            nprobe_candidates = [1, 5, 10, 20, 50]
            best_recall = 0
            best_search_time = float('inf')
            best_nprobe = 1
            
            for nprobe in nprobe_candidates:
                index.nprobe = nprobe
                
                start = time.time()
                _, predicted = index.search(self.query_vectors, k=10)
                search_time = (time.time() - start) * 1000
                
                # 计算召回率
                recall = self._compute_recall(predicted, self.ground_truth)
                
                if recall > best_recall or (recall == best_recall and search_time < best_search_time):
                    best_recall = recall
                    best_search_time = search_time
                    best_nprobe = nprobe
            
            # 估算内存使用
            memory_usage = self._estimate_memory_usage(index)
            
            result = PerformanceResult(
                index_type=f"IVF{nlist}_Flat",
                build_time_ms=build_time,
                search_time_ms=best_search_time,
                recall_at_10=best_recall,
                memory_usage_mb=memory_usage,
                index_size_mb=0  # 未计算
            )
            
            results[nlist] = result
            
            print(f"  nprobe={best_nprobe}, 召回率={best_recall:.4f}, "
                  f"搜索时间={best_search_time:.2f}ms, 内存={memory_usage:.2f}MB")
        
        return results
    
    def tune_hnsw_m(self, M_candidates: List[int] = None) -> Dict[int, PerformanceResult]:
        """
        调优 HNSW 的 M 参数
        Args:
            M_candidates: 候选 M 值列表
        Returns:
            {M: 性能结果}
        """
        try:
            import faiss
        except ImportError:
            raise ImportError("请安装 faiss: pip install faiss-cpu")
        
        if M_candidates is None:
            M_candidates = [16, 32, 48, 64]
        
        results = {}
        
        for M in M_candidates:
            print(f"\n测试 HNSW M={M}...")
            
            # 构建索引
            index = faiss.IndexHNSWFlat(self.dimension, M, faiss.METRIC_INNER_PRODUCT)
            index.hnsw.efConstruction = 200
            
            start = time.time()
            index.add(self.test_vectors)
            build_time = (time.time() - start) * 1000
            
            # 测试不同 efSearch 值
            ef_candidates = [20, 40, 80, 160]
            best_recall = 0
            best_search_time = float('inf')
            best_ef = 40
            
            for ef in ef_candidates:
                index.hnsw.efSearch = ef
                
                start = time.time()
                _, predicted = index.search(self.query_vectors, k=10)
                search_time = (time.time() - start) * 1000
                
                recall = self._compute_recall(predicted, self.ground_truth)
                
                if recall > best_recall or (recall == best_recall and search_time < best_search_time):
                    best_recall = recall
                    best_search_time = search_time
                    best_ef = ef
            
            memory_usage = self._estimate_memory_usage(index)
            
            result = PerformanceResult(
                index_type=f"HNSW{M}_Flat",
                build_time_ms=build_time,
                search_time_ms=best_search_time,
                recall_at_10=best_recall,
                memory_usage_mb=memory_usage,
                index_size_mb=0
            )
            
            results[M] = result
            
            print(f"  efSearch={best_ef}, 召回率={best_recall:.4f}, "
                  f"搜索时间={best_search_time:.2f}ms, 内存={memory_usage:.2f}MB")
        
        return results
    
    def compare_all_indexes(self) -> List[PerformanceResult]:
        """
        对比所有索引类型
        Returns:
            性能结果列表
        """
        try:
            import faiss
        except ImportError:
            raise ImportError("请安装 faiss: pip install faiss-cpu")
        
        all_results = []
        
        # 1. Flat 索引（基准）
        print("\n=== Flat 索引（精确搜索）===")
        index_flat = faiss.IndexFlatIP(self.dimension)
        
        start = time.time()
        index_flat.add(self.test_vectors)
        build_time = (time.time() - start) * 1000
        
        start = time.time()
        _, _ = index_flat.search(self.query_vectors, k=10)
        search_time = (time.time() - start) * 1000
        
        memory_usage = self._estimate_memory_usage(index_flat)
        
        flat_result = PerformanceResult(
            index_type="Flat_IP",
            build_time_ms=build_time,
            search_time_ms=search_time,
            recall_at_10=1.0,  # 精确搜索召回率=1
            memory_usage_mb=memory_usage,
            index_size_mb=0
        )
        all_results.append(flat_result)
        
        # 2. 最佳 IVF 索引
        print("\n=== IVF 索引 ===")
        ivf_results = self.tune_ivf_nlist()
        if ivf_results:
            best_ivf = max(ivf_results.values(), key=lambda r: r.recall_at_10 / r.search_time_ms)
            all_results.append(best_ivf)
        
        # 3. 最佳 HNSW 索引
        print("\n=== HNSW 索引 ===")
        hnsw_results = self.tune_hnsw_m()
        if hnsw_results:
            best_hnsw = max(hnsw_results.values(), key=lambda r: r.recall_at_10 / r.search_time_ms)
            all_results.append(best_hnsw)
        
        return all_results
    
    def _compute_recall(self, predicted: np.ndarray, ground_truth: np.ndarray) -> float:
        """计算召回率@10"""
        total_matches = 0
        total_possible = len(ground_truth) * 10
        
        for pred, truth in zip(predicted, ground_truth):
            matches = len(set(pred) & set(truth))
            total_matches += matches
        
        return total_matches / total_possible if total_possible > 0 else 0
    
    def _estimate_memory_usage(self, index) -> float:
        """估算内存使用（MB）"""
        try:
            import faiss
            # 使用 FAISS 的内存估算
            if hasattr(index, 'ntotal'):
                ntotal = index.ntotal
            else:
                ntotal = len(self.test_vectors)
            
            # 粗略估算：每个向量 dimension * 4 bytes (float32)
            base_memory = ntotal * self.dimension * 4 / 1024 / 1024
            
            # 索引结构开销（估算）
            if isinstance(index, faiss.IndexIVFFlat):
                # IVF 额外开销：codebooks + 倒排表
                overhead = base_memory * 0.2
            elif isinstance(index, faiss.IndexHNSWFlat):
                # HNSW 额外开销：图结构
                M = index.hnsw.M
                overhead = base_memory * (M / 8)  # HNSW 内存通常是 Flat 的 M/8 倍
            else:
                overhead = 0
            
            return base_memory + overhead
        except:
            return 0
    
    def print_comparison_table(self, results: List[PerformanceResult]):
        """打印对比表格"""
        print("\n" + "="*100)
        print(f"{'索引类型':<20} {'构建时间 (ms)':<15} {'搜索时间 (ms)':<15} {'召回率@10':<12} {'内存 (MB)':<12}")
        print("="*100)
        
        for result in sorted(results, key=lambda r: r.search_time_ms):
            print(f"{result.index_type:<20} {result.build_time_ms:>12.2f}   "
                  f"{result.search_time_ms:>12.2f}   {result.recall_at_10:>10.4f}   "
                  f"{result.memory_usage_mb:>10.2f}")
        
        print("="*100)
    
    def recommend_index(self, requirements: Dict) -> str:
        """
        根据需求推荐索引
        Args:
            requirements: 需求字典
                - max_search_time_ms: 最大搜索时间
                - min_recall: 最小召回率
                - max_memory_mb: 最大内存
                - data_size: 数据规模
        Returns:
            推荐的索引类型
        """
        results = self.compare_all_indexes()
        
        # 过滤满足要求的索引
        candidates = []
        for result in results:
            if (result.search_time_ms <= requirements.get('max_search_time_ms', float('inf')) and
                result.recall_at_10 >= requirements.get('min_recall', 0) and
                result.memory_usage_mb <= requirements.get('max_memory_mb', float('inf'))):
                candidates.append(result)
        
        if not candidates:
            print("警告：没有满足所有要求的索引，放宽条件...")
            candidates = results
        
        # 选择最快的
        best = min(candidates, key=lambda r: r.search_time_ms)
        
        print(f"\n推荐索引：{best.index_type}")
        print(f"  - 搜索时间：{best.search_time_ms:.2f}ms")
        print(f"  - 召回率：{best.recall_at_10:.4f}")
        print(f"  - 内存使用：{best.memory_usage_mb:.2f}MB")
        
        return best.index_type


def auto_tune_faiss(vectors: np.ndarray, requirements: Optional[Dict] = None) -> Tuple[str, Dict]:
    """
    自动调优 FAISS 索引
    Args:
        vectors: 向量矩阵
        requirements: 性能要求
    Returns:
        (推荐索引类型，配置参数)
    """
    dimension = vectors.shape[1] if len(vectors) > 0 else 512
    
    tuner = FAISSTuner(dimension=dimension)
    tuner.prepare_test_data(num_vectors=min(len(vectors), 10000), num_queries=100)
    
    if requirements is None:
        # 默认要求
        requirements = {
            'max_search_time_ms': 10,
            'min_recall': 0.95,
            'max_memory_mb': 1024
        }
    
    recommended = tuner.recommend_index(requirements)
    
    # 解析推荐结果
    if recommended.startswith('IVF'):
        nlist = int(recommended[3:recommended.find('_')])
        return 'IVF', {'nlist': nlist, 'nprobe': 10}
    elif recommended.startswith('HNSW'):
        M = int(recommended[4:recommended.find('_')])
        return 'HNSW', {'M': M, 'efSearch': 40}
    else:
        return 'Flat', {}


if __name__ == "__main__":
    # 示例：自动调优
    print("FAISS 索引自动调优示例\n")
    
    # 生成测试数据
    np.random.seed(42)
    test_vectors = np.random.rand(5000, 512).astype(np.float32)
    
    # 自动调优
    index_type, config = auto_tune_faiss(test_vectors)
    
    print(f"\n最终推荐：{index_type} 索引")
    print(f"配置参数：{config}")
