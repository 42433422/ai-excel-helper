"""
中期优化功能测试
测试 FAISS 调优、Redis 缓存优化、持久化集成
"""

import pytest
import numpy as np
import time
from pathlib import Path
import tempfile


class TestFAISSTuning:
    """FAISS 索引调优测试"""
    
    def test_TC_FAISS_TUNE_001_index_config_creation(self):
        """
        用例模块：FAISS 调优 - 索引配置
        用例标题：测试索引配置正确创建
        前置条件：无
        操作步骤：
            1. 导入 IndexConfig
            2. 创建 Flat 索引配置
            3. 创建 IVF 索引配置
            4. 创建 HNSW 索引配置
        预期结果：
            - 配置创建成功
            - 默认参数正确
        用例级别：P0
        备注：配置验证
        """
        try:
            from backend.faiss_tuning import IndexConfig
        except ImportError:
            pytest.skip("FAISS 调优模块未安装")
        
        # Flat 配置
        flat_config = IndexConfig(index_type="Flat")
        assert flat_config.index_type == "Flat"
        
        # IVF 配置
        ivf_config = IndexConfig(index_type="IVF", nlist=100, nprobe=10)
        assert ivf_config.nlist == 100
        assert ivf_config.nprobe == 10
        
        # HNSW 配置
        hnsw_config = IndexConfig(index_type="HNSW", M=32, efConstruction=200)
        assert hnsw_config.M == 32
        assert hnsw_config.efConstruction == 200
    
    def test_TC_FAISS_TUNE_002_tuner_initialization(self):
        """
        用例模块：FAISS 调优 - 调优器初始化
        用例标题：测试 FAISSTuner 正确初始化
        前置条件：无
        操作步骤：
            1. 创建 FAISSTuner 实例
            2. 验证维度设置
        预期结果：
            - 调优器创建成功
            - 维度正确
        用例级别：P0
        备注：初始化验证
        """
        try:
            from backend.faiss_tuning import FAISSTuner
        except ImportError:
            pytest.skip("FAISS 调优模块未安装")
        
        tuner = FAISSTuner(dimension=512)
        assert tuner.dimension == 512
    
    def test_TC_FAISS_TUNE_003_test_data_preparation(self):
        """
        用例模块：FAISS 调优 - 测试数据准备
        用例标题：测试测试数据正确生成
        前置条件：FAISSTuner 已创建
        操作步骤：
            1. 准备测试向量
            2. 准备查询向量
            3. 计算真实最近邻
        预期结果：
            - 向量维度正确
            - 向量已归一化
            - 真实最近邻计算成功
        用例级别：P1
        备注：数据准备
        """
        try:
            from backend.faiss_tuning import FAISSTuner
        except ImportError:
            pytest.skip("FAISS 调优模块未安装")
        
        tuner = FAISSTuner(dimension=512)
        
        try:
            tuner.prepare_test_data(num_vectors=100, num_queries=10)
            
            assert tuner.test_vectors.shape == (100, 512)
            assert tuner.query_vectors.shape == (10, 512)
            assert tuner.ground_truth is not None
        except ImportError as e:
            pytest.skip(str(e))
    
    def test_TC_FAISS_TUNE_004_recall_computation(self):
        """
        用例模块：FAISS 调优 - 召回率计算
        用例标题：测试召回率正确计算
        前置条件：已准备测试数据
        操作步骤：
            1. 创建预测结果
            2. 创建真实标签
            3. 计算召回率
        预期结果：
            - 召回率在 0-1 之间
            - 完全匹配时召回率=1
        用例级别：P1
        备注：召回率验证
        """
        try:
            from backend.faiss_tuning import FAISSTuner
        except ImportError:
            pytest.skip("FAISS 调优模块未安装")
        
        tuner = FAISSTuner(dimension=512)
        
        # 完全匹配（使用更大的样本以符合@10 的计算）
        predicted = np.array([[i for i in range(10)] for _ in range(5)])
        ground_truth = np.array([[i for i in range(10)] for _ in range(5)])
        
        recall = tuner._compute_recall(predicted, ground_truth)
        assert 0 <= recall <= 1
        assert recall == 1.0
        
        # 部分匹配
        predicted_partial = np.array([[0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                                     [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]])
        ground_truth_partial = np.array([[0, 1, 2, 3, 4, 5, 6, 7, 8, 100],
                                        [10, 11, 12, 13, 14, 15, 16, 17, 18, 200]])
        
        recall_partial = tuner._compute_recall(predicted_partial, ground_truth_partial)
        assert 0 <= recall_partial <= 1
        assert 0.8 <= recall_partial <= 1.0  # 应该有 90% 的召回率


class TestRedisCacheOptimization:
    """Redis 缓存优化测试"""
    
    def test_TC_REDIS_OPT_001_adaptive_ttl_computation(self):
        """
        用例模块：Redis 优化 - 自适应 TTL
        用例标题：测试 TTL 根据频率自适应调整
        前置条件：AdaptiveTTLManager 已创建
        操作步骤：
            1. 创建 TTL 管理器
            2. 多次查询相同 key
            3. 验证 TTL 增加
        预期结果：
            - 频繁查询 TTL 更长
            - TTL 不超过最大值
        用例级别：P0
        备注：自适应 TTL
        """
        from backend.redis_cache_optimization import AdaptiveTTLManager
        
        manager = AdaptiveTTLManager(base_ttl=3600, max_ttl=7200)
        
        # 第一次查询
        ttl1 = manager.compute_ttl("test_query")
        assert ttl1 == 3600
        
        # 短时间内再次查询
        ttl2 = manager.compute_ttl("test_query")
        assert ttl2 >= ttl1
        assert ttl2 <= 7200
    
    def test_TC_REDIS_OPT_002_lfu_cache_operations(self):
        """
        用例模块：Redis 优化 - LFU 缓存
        用例标题：测试 LFU 缓存正确操作
        前置条件：LFUCache 已创建
        操作步骤：
            1. 设置缓存
            2. 获取缓存
            3. 验证淘汰策略
        预期结果：
            - 缓存命中
            - 最少使用被淘汰
        用例级别：P0
        备注：LFU 缓存
        """
        from backend.redis_cache_optimization import LFUCache
        
        cache = LFUCache(max_size=3)
        
        # 设置缓存
        cache.set("key1", "value1", ttl=3600)
        cache.set("key2", "value2", ttl=3600)
        cache.set("key3", "value3", ttl=3600)
        
        # 访问 key1 多次
        cache.get("key1")
        cache.get("key1")
        
        # 添加新 key，应该淘汰 key2 或 key3（最少使用）
        cache.set("key4", "value4", ttl=3600)
        
        # key1 应该还在
        assert cache.get("key1") == "value1"
    
    def test_TC_REDIS_OPT_003_tiered_cache_hierarchy(self):
        """
        用例模块：Redis 优化 - 分层缓存
        用例标题：测试分层缓存层级结构
        前置条件：TieredCacheManager 已创建
        操作步骤：
            1. 设置缓存
            2. 从不同层级获取
            3. 验证缓存提升
        预期结果：
            - L1 优先
            - L2 提升到 L1
            - 统计正确
        用例级别：P1
        备注：分层缓存
        """
        from backend.redis_cache_optimization import TieredCacheManager
        
        manager = TieredCacheManager(l1_size=2, l2_size=10)
        
        # 设置缓存
        manager.set("key1", "value1")
        
        # 第一次获取（L1 miss, L2 miss）
        value = manager.get("key1")
        assert value == "value1"
        
        # 第二次获取（应该 L1 hit）
        value = manager.get("key1")
        assert value == "value1"
        
        # 检查统计
        stats = manager.get_stats()
        assert stats['l1_hit_rate'] > 0
    
    def test_TC_REDIS_OPT_004_smart_cache_pattern_analysis(self):
        """
        用例模块：Redis 优化 - 智能缓存模式分析
        用例标题：测试查询模式自动识别
        前置条件：SmartCacheManager 已创建
        操作步骤：
            1. 创建智能缓存
            2. 分析不同查询模式
            3. 验证模式识别
        预期结果：
            - 正确识别销售指标模式
            - 正确识别地理模式
            - 正确识别时间模式
        用例级别：P1
        备注：模式分析
        """
        from backend.redis_cache_optimization import SmartCacheManager
        
        cache = SmartCacheManager()
        
        # 测试销售指标模式
        pattern = cache.analyze_query_pattern("销售额是多少")
        assert pattern == 'sales_metric'
        
        # 测试地理模式
        pattern = cache.analyze_query_pattern("北京地区销售")
        assert pattern == 'geographic'
        
        # 测试时间模式
        pattern = cache.analyze_query_pattern("上个月的数据")
        assert pattern == 'temporal'


class TestPersistenceIntegration:
    """持久化集成测试"""
    
    def test_TC_PERSIST_INT_001_service_creation(self):
        """
        用例模块：持久化集成 - 服务创建
        用例标题：测试 PersistedExcelVectorService 正确创建
        前置条件：无
        操作步骤：
            1. 创建持久化服务
            2. 验证持久化目录
        预期结果：
            - 服务创建成功
            - 持久化目录存在
        用例级别：P0
        备注：服务创建
        """
        try:
            from backend.persistence_integration import create_persisted_service
        except ImportError:
            pytest.skip("持久化集成模块未安装")
        
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            service = create_persisted_service(workspace_root=tmpdir)
            
            assert service.persist_dir.exists()
            assert service.index_file.parent == service.persist_dir
    
    def test_TC_PERSIST_INT_002_version_management(self):
        """
        用例模块：持久化集成 - 版本管理
        用例标题：测试版本信息正确管理
        前置条件：持久化服务已创建
        操作步骤：
            1. 获取版本信息
            2. 验证版本结构
        预期结果：
            - 版本信息包含必要字段
            - 初始版本为 0
        用例级别：P0
        备注：版本管理
        """
        try:
            from backend.persistence_integration import create_persisted_service
        except ImportError:
            pytest.skip("持久化集成模块未安装")
        
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            service = create_persisted_service(workspace_root=tmpdir)
            
            version_info = service.get_version_info()
            
            # 初始状态
            assert version_info == {} or version_info.get('version') == 0
    
    def test_TC_PERSIST_INT_003_index_stats(self):
        """
        用例模块：持久化集成 - 索引统计
        用例标题：测试索引统计信息正确
        前置条件：持久化服务已创建
        操作步骤：
            1. 获取索引统计
            2. 验证统计字段
        预期结果：
            - 包含 chunk_count
            - 包含 version
            - 包含 persist_dir
        用例级别：P1
        备注：索引统计
        """
        try:
            from backend.persistence_integration import create_persisted_service
        except ImportError:
            pytest.skip("持久化集成模块未安装")
        
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            service = create_persisted_service(workspace_root=tmpdir)
            
            stats = service.get_index_stats()
            
            assert 'chunk_count' in stats
            assert 'version' in stats
            assert 'persist_dir' in stats
    
    def test_TC_PERSIST_INT_004_cache_stats(self):
        """
        用例模块：持久化集成 - 缓存统计
        用例标题：测试缓存统计信息正确
        前置条件：缓存持久化服务已创建
        操作步骤：
            1. 获取缓存统计
            2. 验证统计字段
        预期结果：
            - 包含 cache_size
            - 包含 hit_rate
            - 包含 hits/misses
        用例级别：P1
        备注：缓存统计
        """
        try:
            from backend.persistence_integration import create_persisted_service
        except ImportError:
            pytest.skip("持久化集成模块未安装")
        
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            service = create_persisted_service(
                workspace_root=tmpdir,
                use_cache=True
            )
            
            cache_stats = service.get_cache_stats()
            
            assert 'cache_size' in cache_stats
            assert 'hit_rate' in cache_stats
            assert 'hits' in cache_stats
            assert 'misses' in cache_stats


class TestIntegrationWorkflow:
    """集成工作流测试"""
    
    def test_TC_WORKFLOW_001_full_optimization_pipeline(self):
        """
        用例模块：集成工作流 - 完整优化流程
        用例标题：测试从 FAISS 调优到缓存的完整流程
        前置条件：所有优化模块可用
        操作步骤：
            1. 创建 FAISS 调优器
            2. 准备测试数据
            3. 创建智能缓存
            4. 创建持久化服务
            5. 验证集成
        预期结果：
            - 所有模块正常工作
            - 集成无冲突
        用例级别：P2
        备注：端到端测试
        """
        # 1. FAISS 调优
        try:
            from backend.faiss_tuning import FAISSTuner
            tuner = FAISSTuner(dimension=512)
            tuner.prepare_test_data(num_vectors=50, num_queries=5)
        except ImportError:
            pytest.skip("FAISS 调优模块未安装")
        
        # 2. 智能缓存
        from backend.redis_cache_optimization import SmartCacheManager
        cache = SmartCacheManager()
        
        # 3. 持久化服务
        try:
            from backend.persistence_integration import create_persisted_service
            import tempfile
            
            with tempfile.TemporaryDirectory() as tmpdir:
                service = create_persisted_service(workspace_root=tmpdir)
                
                # 验证所有组件
                assert tuner.test_vectors is not None
                assert cache.query_patterns is not None
                assert service.persist_dir.exists()
        except ImportError:
            pytest.skip("持久化集成模块未安装")
    
    def test_TC_WORKFLOW_002_performance_optimization(self):
        """
        用例模块：集成工作流 - 性能优化
        用例标题：测试性能优化效果
        前置条件：优化模块可用
        操作步骤：
            1. 测试无缓存性能
            2. 测试有缓存性能
            3. 对比性能提升
        预期结果：
            - 缓存提升性能
            - 命中率逐步提高
        用例级别：P2
        备注：性能对比
        """
        from backend.redis_cache_optimization import SmartCacheManager
        
        cache = SmartCacheManager()
        
        # 模拟计算函数
        def mock_compute(query):
            time.sleep(0.01)  # 10ms 延迟
            return {'result': query}
        
        # 第一次查询（未缓存）
        start = time.time()
        cache.get_or_compute("test", mock_compute)
        time1 = time.time() - start
        
        # 第二次查询（缓存命中）
        start = time.time()
        cache.get_or_compute("test", mock_compute)
        time2 = time.time() - start
        
        # 缓存命中应该更快
        assert time2 < time1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
