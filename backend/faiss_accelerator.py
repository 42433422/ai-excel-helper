"""
FAISS 向量检索加速模块
目标：实现大规模向量检索加速，支持百万级向量毫秒级检索
功能：
    - FAISS 索引构建
    - 相似度搜索
    - 增量更新
    - 持久化存储
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import pickle
import time


class FAISSAccelerator:
    """FAISS 向量检索加速器"""
    
    def __init__(self, dimension: int = 512, index_type: str = "Flat"):
        """
        初始化 FAISS 加速器
        Args:
            dimension: 向量维度
            index_type: 索引类型
                - "Flat": 精确搜索（适合 < 10 万向量）
                - "IVF": 倒排文件索引（适合 10 万 -100 万向量）
                - "HNSW": 图索引（适合 > 100 万向量）
        """
        self.dimension = dimension
        self.index_type = index_type
        self.index = None
        self.vectors = []
        self.metadata = []
        self.is_trained = False
        
        self._initialize_index()
    
    def _initialize_index(self):
        """初始化 FAISS 索引"""
        try:
            import faiss
            
            if self.index_type == "Flat":
                # 精确搜索索引
                self.index = faiss.IndexFlatIP(self.dimension)  # 内积相似度
            
            elif self.index_type == "IVF":
                # IVF 索引（需要训练）
                nlist = 100  # 聚类中心数
                quantizer = faiss.IndexFlatIP(self.dimension)
                self.index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist, faiss.METRIC_INNER_PRODUCT)
            
            elif self.index_type == "HNSW":
                # HNSW 图索引
                M = 32  # 每个节点的连接数
                self.index = faiss.IndexHNSWFlat(self.dimension, M, faiss.METRIC_INNER_PRODUCT)
            
            else:
                raise ValueError(f"不支持的索引类型：{self.index_type}")
        
        except ImportError:
            raise ImportError("请安装 faiss: pip install faiss-cpu")
    
    def add_vectors(self, vectors: np.ndarray, metadata_list: Optional[List[Dict]] = None):
        """
        添加向量到索引
        Args:
            vectors: 向量矩阵 (n, d)
            metadata_list: 元数据列表
        """
        if len(vectors) == 0:
            return
        
        # 确保向量是 float32 类型
        vectors = np.asarray(vectors, dtype=np.float32)
        
        # L2 归一化（FAISS 内积相似度需要）
        faiss = __import__('faiss')
        faiss.normalize_L2(vectors)
        
        # 添加到索引
        self.index.add(vectors)
        
        # 保存向量和元数据
        self.vectors.append(vectors)
        if metadata_list:
            self.metadata.extend(metadata_list)
    
    def search(self, query_vector: np.ndarray, top_k: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """
        搜索最相似的向量
        Args:
            query_vector: 查询向量 (d,)
            top_k: 返回数量
        Returns:
            (相似向量索引，相似度分数)
        """
        if self.index.ntotal == 0:
            return np.array([], dtype=np.int64), np.array([], dtype=np.float32)
        
        # 确保查询向量形状正确
        query_vector = np.asarray(query_vector, dtype=np.float32).reshape(1, -1)
        
        # L2 归一化
        faiss = __import__('faiss')
        faiss.normalize_L2(query_vector)
        
        # 搜索
        distances, indices = self.index.search(query_vector, k=top_k)
        
        return indices[0], distances[0]
    
    def train(self, training_vectors: np.ndarray):
        """
        训练索引（仅 IVF 索引需要）
        Args:
            training_vectors: 训练向量矩阵 (n, d)
        """
        if self.index_type != "IVF":
            return
        
        if not self.index.is_trained:
            training_vectors = np.asarray(training_vectors, dtype=np.float32)
            self.index.train(training_vectors)
            self.is_trained = True
    
    def save(self, filepath: str):
        """
        保存索引到文件
        Args:
            filepath: 文件路径
        """
        import faiss
        faiss.write_index(self.index, filepath)
        
        # 保存元数据
        metadata_path = filepath + ".meta.pkl"
        with open(metadata_path, 'wb') as f:
            pickle.dump({
                'vectors': self.vectors,
                'metadata': self.metadata,
                'dimension': self.dimension,
                'index_type': self.index_type
            }, f)
    
    def load(self, filepath: str):
        """
        从文件加载索引
        Args:
            filepath: 文件路径
        """
        import faiss
        self.index = faiss.read_index(filepath)
        
        # 加载元数据
        metadata_path = filepath + ".meta.pkl"
        if Path(metadata_path).exists():
            with open(metadata_path, 'rb') as f:
                data = pickle.load(f)
                self.vectors = data['vectors']
                self.metadata = data['metadata']
                self.dimension = data['dimension']
                self.index_type = data['index_type']
    
    def get_stats(self) -> Dict:
        """获取索引统计信息"""
        return {
            'total_vectors': self.index.ntotal,
            'dimension': self.dimension,
            'index_type': self.index_type,
            'is_trained': self.index.is_trained if hasattr(self.index, 'is_trained') else True,
            'memory_usage_mb': self.index.ntotal * self.dimension * 4 / 1024 / 1024  # 估算
        }


class HybridSearchEngine:
    """混合搜索引擎（关键词 + 向量）"""
    
    def __init__(self, faiss_index_type: str = "Flat"):
        """
        初始化混合搜索引擎
        Args:
            faiss_index_type: FAISS 索引类型
        """
        self.faiss_accelerator = None
        self.faiss_index_type = faiss_index_type
        self.documents = []
        self.keyword_index = {}  # 倒排索引
    
    def index_documents(self, documents: List[Dict], vectors: np.ndarray):
        """
        索引文档和向量
        Args:
            documents: 文档列表，每个文档包含 {'text': str, 'metadata': dict}
            vectors: 向量矩阵 (n, d)
        """
        self.documents = documents
        
        # 构建关键词倒排索引
        self._build_keyword_index(documents)
        
        # 初始化 FAISS 加速器
        dimension = vectors.shape[1] if len(vectors) > 0 else 512
        self.faiss_accelerator = FAISSAccelerator(dimension=dimension, index_type=self.faiss_index_type)
        
        # 添加向量到 FAISS
        self.faiss_accelerator.add_vectors(vectors)
    
    def _build_keyword_index(self, documents: List[Dict]):
        """构建关键词倒排索引"""
        self.keyword_index = {}
        
        for idx, doc in enumerate(documents):
            text = doc.get('text', '')
            # 简单分词（实际应该用更好的分词器）
            words = text.lower().split()
            
            for word in words:
                if word not in self.keyword_index:
                    self.keyword_index[word] = []
                self.keyword_index[word].append(idx)
    
    def search(self, query: str, top_k: int = 5, 
               keyword_weight: float = 0.3, 
               semantic_weight: float = 0.7) -> List[Dict]:
        """
        混合搜索
        Args:
            query: 查询文本
            top_k: 返回数量
            keyword_weight: 关键词权重
            semantic_weight: 语义权重
        Returns:
            排序后的文档列表
        """
        # 1. 关键词搜索
        keyword_scores = self._keyword_search(query, top_k * 2)
        
        # 2. 语义搜索（需要外部提供 embedder）
        semantic_scores = self._semantic_search(query, top_k * 2)
        
        # 3. 融合分数
        fused_scores = self._fuse_scores(keyword_scores, semantic_scores, 
                                         keyword_weight, semantic_weight)
        
        # 4. 返回 top_k
        sorted_docs = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for idx, score in sorted_docs[:top_k]:
            result = self.documents[idx].copy()
            result['score'] = float(score)
            results.append(result)
        
        return results
    
    def _keyword_search(self, query: str, top_k: int) -> Dict[int, float]:
        """关键词搜索（BM25 简化版）"""
        scores = {}
        query_words = query.lower().split()
        
        for word in query_words:
            if word in self.keyword_index:
                for doc_idx in self.keyword_index[word]:
                    if doc_idx not in scores:
                        scores[doc_idx] = 0
                    # 简化 BM25：文档频率越高，分数越低
                    scores[doc_idx] += 1.0 / (1 + len(self.keyword_index[word]))
        
        return scores
    
    def _semantic_search(self, query: str, top_k: int) -> Dict[int, float]:
        """语义搜索"""
        if self.faiss_accelerator is None:
            return {}
        
        # 这里需要外部 embedder，简化处理
        # 实际应该调用 embedder.embed_query(query)
        return {}
    
    def _fuse_scores(self, keyword_scores: Dict[int, float], 
                     semantic_scores: Dict[int, float],
                     keyword_weight: float, 
                     semantic_weight: float) -> Dict[int, float]:
        """分数融合"""
        fused = {}
        all_indices = set(keyword_scores.keys()) | set(semantic_scores.keys())
        
        for idx in all_indices:
            kw_score = keyword_scores.get(idx, 0)
            sem_score = semantic_scores.get(idx, 0)
            fused[idx] = kw_score * keyword_weight + sem_score * semantic_weight
        
        return fused


if __name__ == "__main__":
    # 测试 FAISS 加速器
    print("测试 FAISS 加速器...")
    
    # 创建测试向量
    np.random.seed(42)
    test_vectors = np.random.rand(1000, 512).astype(np.float32)
    
    # 初始化加速器
    accelerator = FAISSAccelerator(dimension=512, index_type="Flat")
    
    # 添加向量
    start = time.time()
    accelerator.add_vectors(test_vectors)
    print(f"添加 1000 个向量耗时：{(time.time() - start)*1000:.2f}ms")
    
    # 搜索测试
    query_vector = np.random.rand(512).astype(np.float32)
    start = time.time()
    indices, distances = accelerator.search(query_vector, top_k=5)
    print(f"搜索耗时：{(time.time() - start)*1000:.2f}ms")
    print(f"Top 5 相似度：{distances}")
    
    # 统计信息
    stats = accelerator.get_stats()
    print(f"\n索引统计：{stats}")
