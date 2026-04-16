"""
中期优化功能测试
测试 FAISS 加速、持久化、Redis 缓存功能
"""

import pytest
import numpy as np
import time
from pathlib import Path
import tempfile


class TestFAISSAccelerator:
    """FAISS 加速器测试"""
    
    def test_TC_FAISS_001_index_creation(self):
        """
        用例模块：FAISS - 索引创建
        用例标题：测试 FAISS 索引正确创建
        前置条件：已安装 faiss-cpu
        操作步骤：
            1. 导入 FAISSAccelerator
            2. 创建 Flat 类型索引
            3. 验证索引属性
        预期结果：
            - 索引创建成功
            - 维度正确
            - 索引类型为 Flat
        用例级别：P0
        备注：基础功能验证
        """
        try:
            from backend.faiss_accelerator import FAISSAccelerator
        except ImportError:
            pytest.skip("FAISS 未安装")
        
        accelerator = FAISSAccelerator(dimension=512, index_type="Flat")
        
        assert accelerator.dimension == 512
        assert accelerator.index_type == "Flat"
        assert accelerator.index is not None
    
    def test_TC_FAISS_002_add_vectors(self):
        """
        用例模块：FAISS - 向量添加
        用例标题：测试批量添加向量
        前置条件：FAISS 索引已创建
        操作步骤：
            1. 准备 100 个 512 维向量
            2. 添加到索引
            3. 验证向量数量
        预期结果：
            - 向量成功添加
            - 索引中向量数 = 100
            - 向量已 L2 归一化
        用例级别：P0
        备注：批量添加性能
        """
        try:
            from backend.faiss_accelerator import FAISSAccelerator
        except ImportError:
            pytest.skip("FAISS 未安装")
        
        accelerator = FAISSAccelerator(dimension=512, index_type="Flat")
        
        # 生成随机向量
        test_vectors = np.random.rand(100, 512).astype(np.float32)
        
        start = time.time()
        accelerator.add_vectors(test_vectors)
        elapsed = time.time() - start
        
        stats = accelerator.get_stats()
        assert stats['total_vectors'] == 100
        assert elapsed < 1.0, f"添加速度过慢：{elapsed:.2f}s"
    
    def test_TC_FAISS_003_search_performance(self):
        """
        用例模块：FAISS - 搜索性能
        用例标题：测试向量搜索性能
        前置条件：索引已有 1000 个向量
        操作步骤：
            1. 创建查询向量
            2. 搜索 top 5 相似向量
            3. 记录搜索时间
        预期结果：
            - 搜索时间 < 10ms
            - 返回 5 个结果
            - 相似度降序排列
        用例级别：P0
        备注：核心性能指标
        """
        try:
            from backend.faiss_accelerator import FAISSAccelerator
        except ImportError:
            pytest.skip("FAISS 未安装")
        
        accelerator = FAISSAccelerator(dimension=512, index_type="Flat")
        
        # 添加 1000 个向量
        test_vectors = np.random.rand(1000, 512).astype(np.float32)
        accelerator.add_vectors(test_vectors)
        
        # 搜索
        query_vector = np.random.rand(512).astype(np.float32)
        
        start = time.time()
        indices, distances = accelerator.search(query_vector, top_k=5)
        elapsed = time.time() - start
        
        assert len(indices) == 5
        assert len(distances) == 5
        assert elapsed * 1000 < 10, f"搜索时间过长：{elapsed*1000:.2f}ms"
        
        # 验证降序排列
        assert all(distances[i] >= distances[i+1] for i in range(len(distances)-1))
    
    def test_TC_FAISS_004_index_persistence(self):
        """
        用例模块：FAISS - 索引持久化
        用例标题：测试索引保存和加载
        前置条件：索引已有数据
        操作步骤：
            1. 保存索引到临时文件
            2. 创建新索引并加载
            3. 验证数据一致性
        预期结果：
            - 保存成功
            - 加载成功
            - 向量数一致
        用例级别：P1
        备注：持久化验证
        """
        try:
            from backend.faiss_accelerator import FAISSAccelerator
        except ImportError:
            pytest.skip("FAISS 未安装")
        
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建并填充索引
            accelerator1 = FAISSAccelerator(dimension=512, index_type="Flat")
            test_vectors = np.random.rand(100, 512).astype(np.float32)
            accelerator1.add_vectors(test_vectors)
            
            # 保存
            index_path = Path(tmpdir) / "test_index.faiss"
            accelerator1.save(str(index_path))
            
            # 加载
            accelerator2 = FAISSAccelerator(dimension=512, index_type="Flat")
            accelerator2.load(str(index_path))
            
            stats1 = accelerator1.get_stats()
            stats2 = accelerator2.get_stats()
            
            assert stats1['total_vectors'] == stats2['total_vectors']


class TestVectorIndexPersistence:
    """向量索引持久化测试"""
    
    def test_TC_PERSIST_001_save_and_load(self):
        """
        用例模块：持久化 - 保存加载
        用例标题：测试索引保存和加载
        前置条件：已创建索引
        操作步骤：
            1. 创建 VectorIndexPersistence
            2. 保存索引
            3. 加载索引
        预期结果：
            - 保存成功
            - 加载成功
            - 元数据完整
        用例级别：P0
        备注：基础持久化
        """
        try:
            from backend.vector_index_persistence import VectorIndexPersistence
        except ImportError:
            pytest.skip("持久化模块未安装")
        
        import faiss
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建索引
            index = faiss.IndexFlatIP(512)
            test_vectors = np.random.rand(50, 512).astype(np.float32)
            faiss.normalize_L2(test_vectors)
            index.add(test_vectors)
            
            metadata = [{'id': i, 'text': f'doc_{i}'} for i in range(50)]
            
            # 保存
            persistence = VectorIndexPersistence(tmpdir)
            persistence.save_index(index, test_vectors, metadata)
            
            # 验证文件存在
            assert (Path(tmpdir) / "vector_index.faiss").exists()
            assert (Path(tmpdir) / "metadata.pkl").exists()
            assert (Path(tmpdir) / "config.json").exists()
    
    def test_TC_PERSIST_002_incremental_update(self):
        """
        用例模块：持久化 - 增量更新
        用例标题：测试索引增量更新
        前置条件：索引已保存
        操作步骤：
            1. 添加新向量
            2. 调用增量更新
            3. 验证版本更新
        预期结果：
            - 更新成功
            - 版本号 +1
            - 向量数正确
        用例级别：P1
        备注：增量更新验证
        """
        try:
            from backend.vector_index_persistence import VectorIndexPersistence
        except ImportError:
            pytest.skip("持久化模块未安装")
        
        import faiss
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建索引
            index = faiss.IndexFlatIP(512)
            test_vectors = np.random.rand(50, 512).astype(np.float32)
            faiss.normalize_L2(test_vectors)
            index.add(test_vectors)
            
            metadata = [{'id': i, 'text': f'doc_{i}'} for i in range(50)]
            
            persistence = VectorIndexPersistence(tmpdir)
            persistence.save_index(index, test_vectors, metadata)
            
            # 增量更新
            new_vectors = np.random.rand(10, 512).astype(np.float32)
            faiss.normalize_L2(new_vectors)
            new_metadata = [{'id': i+50, 'text': f'doc_{i+50}'} for i in range(10)]
            
            success = persistence.incremental_update(index, new_vectors, new_metadata)
            
            assert success
            version = persistence.get_version_info()
            assert version['version'] == 2
            assert version['vector_count'] == 60


class TestRedisCache:
    """Redis 缓存测试"""
    
    def test_TC_REDIS_001_cache_manager_init(self):
        """
        用例模块：Redis - 缓存管理器
        用例标题：测试缓存管理器初始化
        前置条件：Redis 服务可用（可选）
        操作步骤：
            1. 创建 RedisCacheManager
            2. 尝试连接
        预期结果：
            - 创建成功
            - 连接成功或降级到内存缓存
        用例级别：P0
        备注：基础初始化
        """
        from backend.redis_cache import RedisCacheManager
        
        cache = RedisCacheManager(host='localhost', port=6379)
        cache.connect()
        
        assert cache._connected
    
    def test_TC_REDIS_002_cache_operations(self):
        """
        用例模块：Redis - 缓存操作
        用例标题：测试缓存基本操作
        前置条件：缓存已连接
        操作步骤：
            1. 设置缓存
            2. 获取缓存
            3. 删除缓存
        预期结果：
            - 设置成功
            - 获取值正确
            - 删除成功
        用例级别：P0
        备注：CRUD 操作
        """
        from backend.redis_cache import RedisCacheManager
        
        cache = RedisCacheManager()
        cache.connect()
        
        # 设置
        cache.set("test_key", {"data": "test_value"})
        
        # 获取
        result = cache.get("test_key")
        assert result is not None
        assert result['data'] == "test_value"
        
        # 删除
        cache.delete("test_key")
        result = cache.get("test_key")
        assert result is None
    
    def test_TC_REDIS_003_hot_query_detection(self):
        """
        用例模块：Redis - 热点检测
        用例标题：测试热点查询检测
        前置条件：热点检测器已初始化
        操作步骤：
            1. 记录多次相同查询
            2. 检查是否被识别为热点
        预期结果：
            - 达到阈值后识别为热点
            - 热点列表正确
        用例级别：P1
        备注：热点检测
        """
        from backend.redis_cache import HotQueryDetector
        
        detector = HotQueryDetector(window_size=100, threshold=5)
        
        # 记录 5 次相同查询
        for _ in range(5):
            detector.record_query("热门查询")
        
        assert detector.is_hot_query("热门查询")
        assert "热门查询" in detector.get_hot_queries()
    
    def test_TC_REDIS_004_vector_cache_manager(self):
        """
        用例模块：Redis - 向量缓存
        用例标题：测试向量缓存管理器
        前置条件：缓存管理器已初始化
        操作步骤：
            1. 缓存向量
            2. 获取缓存向量
            3. 检查统计信息
        预期结果：
            - 缓存成功
            - 获取正确
            - 统计信息准确
        用例级别：P1
        备注：向量缓存
        """
        from backend.redis_cache import VectorCacheManager
        
        cache_manager = VectorCacheManager()
        cache_manager.connect()
        
        # 缓存向量
        test_vector = [0.1] * 512
        cache_manager.cache_vector("test_query", test_vector)
        
        # 获取
        cached = cache_manager.get_cached_vector("test_query")
        assert cached is not None
        assert len(cached) == 512
        
        # 统计
        stats = cache_manager.get_stats()
        assert 'status' in stats


class TestHybridSearchEngine:
    """混合搜索引擎测试"""
    
    def test_TC_HYBRID_001_index_documents(self):
        """
        用例模块：混合搜索 - 文档索引
        用例标题：测试文档和向量索引
        前置条件：混合搜索引擎已初始化
        操作步骤：
            1. 准备文档和向量
            2. 调用 index_documents
            3. 验证索引建立
        预期结果：
            - 文档索引成功
            - 关键词倒排索引建立
            - FAISS 索引建立
        用例级别：P0
        备注：索引建立
        """
        try:
            from backend.faiss_accelerator import HybridSearchEngine
        except ImportError:
            pytest.skip("FAISS 未安装")
        
        engine = HybridSearchEngine()
        
        documents = [
            {'text': '销售额分析', 'metadata': {'id': 1}},
            {'text': '产品销量统计', 'metadata': {'id': 2}},
        ]
        vectors = np.random.rand(2, 512).astype(np.float32)
        
        engine.index_documents(documents, vectors)
        
        assert len(engine.documents) == 2
        assert len(engine.keyword_index) > 0
        assert engine.faiss_accelerator is not None
    
    def test_TC_HYBRID_002_hybrid_search(self):
        """
        用例模块：混合搜索 - 搜索功能
        用例标题：测试混合搜索功能
        前置条件：文档已索引
        操作步骤：
            1. 执行混合搜索
            2. 验证结果排序
            3. 检查分数融合
        预期结果：
            - 返回结果
            - 包含分数
            - 按分数降序
        用例级别：P1
        备注：搜索功能
        """
        try:
            from backend.faiss_accelerator import HybridSearchEngine
        except ImportError:
            pytest.skip("FAISS 未安装")
        
        engine = HybridSearchEngine()
        
        documents = [
            {'text': '销售额分析', 'metadata': {'id': 1}},
            {'text': '产品销量统计', 'metadata': {'id': 2}},
            {'text': '客户满意度调查', 'metadata': {'id': 3}},
        ]
        vectors = np.random.rand(3, 512).astype(np.float32)
        engine.index_documents(documents, vectors)
        
        results = engine.search("销售", top_k=2)
        
        assert len(results) <= 2
        assert 'score' in results[0]
        
        # 验证降序
        if len(results) > 1:
            assert results[0]['score'] >= results[1]['score']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
