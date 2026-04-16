# 中期优化实施指南

## 📋 概述

本文档提供语义准确率基准、性能基准测试、FAISS 加速、向量索引持久化、Redis 缓存的完整实施指南。

## 1. 语义准确率基准（F1 > 0.85）

### 1.1 目标
- **F1 分数**: ≥ 0.85
- **精确率**: ≥ 0.80
- **召回率**: ≥ 0.80
- **区分度**: 相似对与不相似对平均相似度差异 > 0.25

### 1.2 测试用例集

已创建 [test_semantic_accuracy_benchmark.py](file://e:\FHD\backend\tests\test_semantic_accuracy_benchmark.py)，包含：

- **同义词测试** (5 例): 销售额 - 营收，销量 - 销售量等
- **口语化测试** (4 例): 哪个产品卖得最好 - 销量最高的产品等
- **无关词测试** (4 例): 销售额 - 量子力学等
- **上下位词测试** (3 例): 电子产品 - 手机等
- **复合语义测试** (2 例): 销售额同比增长 - 营收环比增加等

### 1.3 运行测试

```bash
# 运行语义准确率基准测试
python -m pytest backend/tests/test_semantic_accuracy_benchmark.py -v

# 查看 F1 分数详情
python backend/tests/test_semantic_accuracy_benchmark.py
```

### 1.4 优化建议

如果 F1 分数未达标：

1. **调整阈值**: 根据实际模型能力调整 `min_similarity` 和 `max_similarity`
2. **增加训练数据**: 收集领域特定语料进行 fine-tuning
3. **模型升级**: 考虑使用更大的 BGE 模型（bge-large-zh-v1.5）
4. **集成学习**: 多个模型投票提升准确率

## 2. 性能基准测试

### 2.1 目标
- **单次查询延迟**: < 100ms
- **P99 延迟**: < 500ms
- **成功率**: > 99%
- **QPS**: > 50
- **并发支持**: 100+ 并发工

### 2.2 测试内容

已创建 [test_performance_benchmark.py](file://e:\FHD\backend\tests\test_performance_benchmark.py)，包含：

- **单次查询延迟测试**: 10 次查询平均延迟
- **并发负载测试**: 100 并发下的性能
- **延迟分布测试**: P50/P95/P99 延迟分析
- **高压并发测试**: 100 并发工 200 请求压力测试

### 2.3 运行测试

```bash
# 运行性能基准测试
python -m pytest backend/tests/test_performance_benchmark.py -v

# 查看性能报告
python backend/tests/test_performance_benchmark.py
```

### 2.4 性能优化路径

#### 当前状态（基于 BGE + 朴素检索）
- 单次查询：~50-100ms（首次加载模型除外）
- 批量查询：~1-2ms/查询（模型已加载）
- 并发能力：受限于模型加载和 CPU

#### 短期优化（1-2 周）
1. **模型预热**: 启动时加载模型，避免冷启动延迟
2. **批量处理**: 合并多个查询为 batch，提升 GPU 利用率
3. **结果缓存**: 缓存高频查询结果

#### 中期优化（1-2 月）
1. **FAISS 加速**: 引入 FAISS 索引加速检索
2. **向量持久化**: 避免重复构建索引
3. **Redis 缓存**: 热点查询缓存

#### 长期优化（3-6 月）
1. **模型量化**: INT8 量化加速推理
2. **GPU 加速**: 使用 GPU 进行向量计算
3. **分布式检索**: 多节点并行检索

## 3. FAISS 加速检索

### 3.1 目标
- **支持规模**: 百万级向量
- **检索时间**: < 10ms（百万级数据）
- **内存占用**: < 1GB（百万向量）

### 3.2 实现模块

已创建 [faiss_accelerator.py](file://e:\FHD\backend\faiss_accelerator.py)，包含：

- **FAISSAccelerator**: FAISS 索引封装
  - Flat: 精确搜索（< 10 万向量）
  - IVF: 倒排文件索引（10 万 -100 万向量）
  - HNSW: 图索引（> 100 万向量）

- **HybridSearchEngine**: 混合搜索引擎
  - 关键词搜索（倒排索引）
  - 语义搜索（FAISS）
  - 分数融合（可配置权重）

### 3.3 安装 FAISS

```bash
# CPU 版本（推荐开发环境）
pip install faiss-cpu

# GPU 版本（生产环境）
pip install faiss-gpu
```

### 3.4 使用示例

```python
from backend.faiss_accelerator import FAISSAccelerator
import numpy as np

# 创建加速器
accelerator = FAISSAccelerator(dimension=512, index_type="Flat")

# 添加向量
vectors = np.random.rand(10000, 512).astype(np.float32)
accelerator.add_vectors(vectors)

# 搜索
query = np.random.rand(512).astype(np.float32)
indices, distances = accelerator.search(query, top_k=5)

# 保存索引
accelerator.save("index.faiss")

# 加载索引
accelerator2 = FAISSAccelerator(dimension=512, index_type="Flat")
accelerator2.load("index.faiss")
```

### 3.5 索引类型选择

| 数据规模 | 推荐索引 | 检索时间 | 内存占用 | 精度 |
|---------|---------|---------|---------|------|
| < 10 万 | Flat | < 5ms | 中 | 100% |
| 10 万 -100 万 | IVF100 | < 10ms | 低 | 95-98% |
| > 100 万 | HNSW32 | < 5ms | 高 | 98-99% |

## 4. 向量索引持久化

### 4.1 目标
- **保存时间**: < 10 秒（百万向量）
- **加载时间**: < 10 秒
- **增量更新**: 支持不重建全量索引
- **版本管理**: 支持版本回滚

### 4.2 实现模块

已创建 [vector_index_persistence.py](file://e:\FHD\backend\vector_index_persistence.py)，包含：

- **VectorIndexPersistence**: 持久化管理器
  - 索引保存/加载
  - 增量更新
  - 版本管理
  - 备份恢复

- **VectorCache**: 内存缓存（LRU 淘汰）
  - 热点缓存
  - 自动淘汰
  - 统计信息

### 4.3 使用示例

```python
from backend.vector_index_persistence import VectorIndexPersistence
import faiss
import numpy as np

# 创建持久化管理器
persistence = VectorIndexPersistence("/path/to/storage")

# 创建索引
index = faiss.IndexFlatIP(512)
vectors = np.random.rand(1000, 512).astype(np.float32)
faiss.normalize_L2(vectors)
index.add(vectors)

metadata = [{'id': i, 'text': f'doc_{i}'} for i in range(1000)]

# 保存
persistence.save_index(index, vectors, metadata)

# 增量更新
new_vectors = np.random.rand(100, 512).astype(np.float32)
faiss.normalize_L2(new_vectors)
new_metadata = [{'id': i+1000, 'text': f'doc_{i+1000}'} for i in range(100)]

persistence.incremental_update(index, new_vectors, new_metadata)

# 获取版本信息
version = persistence.get_version_info()
print(f"当前版本：{version['version']}, 向量数：{version['vector_count']}")

# 列出备份
backups = persistence.list_backups()
print(f"可用备份：{[b.name for b in backups]}")

# 恢复备份
persistence.restore_from_backup(backups[0])
```

### 4.4 存储结构

```
storage_dir/
├── vector_index.faiss       # FAISS 索引
├── metadata.pkl             # 元数据
├── config.json              # 配置信息
├── version.json             # 版本信息
└── backup_YYYYMMDD_HHMMSS/  # 备份目录
    ├── vector_index.faiss
    ├── metadata.pkl
    ├── config.json
    └── version.json
```

## 5. Redis 缓存热点查询

### 5.1 目标
- **缓存命中率**: > 80%（热点查询）
- **响应时间**: < 5ms（缓存命中）
- **自动过期**: 可配置 TTL
- **热点检测**: 自动识别热点查询

### 5.2 实现模块

已创建 [redis_cache.py](file://e:\FHD\backend\redis_cache.py)，包含：

- **RedisCacheManager**: Redis 缓存管理器
  - 连接管理（支持降级到内存缓存）
  - CRUD 操作
  - 批量操作
  - 统计信息

- **HotQueryDetector**: 热点查询检测器
  - 滑动窗口计数
  - 阈值判断
  - 热点列表

- **VectorCacheManager**: 向量缓存管理器
  - 向量缓存
  - 搜索结果缓存
  - 热点查询自动缓存

### 5.3 安装 Redis

```bash
# Windows (使用 WSL 或 Docker)
docker run -d -p 6379:6379 redis:latest

# Linux
sudo apt-get install redis-server
sudo systemctl start redis

# macOS
brew install redis
brew services start redis
```

### 5.4 使用示例

```python
from backend.redis_cache import VectorCacheManager

# 创建缓存管理器
cache_manager = VectorCacheManager(
    redis_config={
        'host': 'localhost',
        'port': 6379,
        'ttl': 3600  # 1 小时过期
    }
)

# 连接（Redis 不可用时自动降级到内存缓存）
cache_manager.connect()

# 获取或计算（自动缓存热点）
def compute_vector(query):
    # 实际计算逻辑
    return embedder.embed_query(query)

result = cache_manager.get_or_compute("销售额", compute_vector)

# 手动缓存
cache_manager.cache_vector("查询 1", vector)
cache_manager.cache_search_results("查询 2", results)

# 获取缓存
cached_vector = cache_manager.get_cached_vector("查询 1")
cached_results = cache_manager.get_cached_search_results("查询 2")

# 统计信息
stats = cache_manager.get_stats()
print(f"缓存命中率：{stats.get('hit_rate', 0):.2%}")
print(f"热点查询：{stats.get('hot_queries', [])}")
```

### 5.5 缓存策略

#### 缓存键设计
```python
# 查询缓存
key = f"query:{md5(query)}"

# 向量缓存
key = f"vector:{md5(query)}"

# 搜索结果缓存
key = f"search:{md5(query)}"
```

#### TTL 配置建议
| 缓存类型 | 推荐 TTL | 说明 |
|---------|---------|------|
| 查询向量 | 3600s | 向量计算成本高 |
| 搜索结果 | 600s | 数据可能变化 |
| 热点查询 | 7200s | 高频访问延长 |

#### 热点检测配置
```python
# 滑动窗口大小：100 次查询
# 阈值：5 次（窗口内出现 5 次即为热点）
detector = HotQueryDetector(window_size=100, threshold=5)
```

## 6. 测试验证

### 6.1 运行所有中期优化测试

```bash
# 运行中期优化功能测试
python -m pytest backend/tests/test_mid_term_optimization.py -v

# 运行语义准确率基准
python -m pytest backend/tests/test_semantic_accuracy_benchmark.py -v

# 运行性能基准
python -m pytest backend/tests/test_performance_benchmark.py -v
```

### 6.2 测试依赖

```bash
# 安装依赖
pip install faiss-cpu redis pytest numpy

# 可选：GPU 加速
pip install faiss-gpu
```

### 6.3 测试状态

| 测试模块 | 用例数 | 状态 | 依赖 |
|---------|--------|------|------|
| 语义准确率基准 | 3 | ✅ 通过 | BGE 模型 |
| 性能基准 | 4 | ✅ 通过 | - |
| FAISS 加速 | 4 | ⚠️ 需安装 | faiss-cpu |
| 向量持久化 | 2 | ⚠️ 需安装 | faiss-cpu |
| Redis 缓存 | 4 | ✅ 降级通过 | redis（可选） |
| 混合搜索 | 2 | ⚠️ 需安装 | faiss-cpu |

## 7. 实施路线图

### 阶段 1: 基准建立（1-2 周）
- [x] 创建语义准确率基准测试
- [x] 创建性能基准测试
- [ ] 收集真实用户语料（1000+ 条）
- [ ] 建立 F1 > 0.85 基线
- [ ] 建立性能基线（延迟、QPS）

### 阶段 2: FAISS 集成（2-3 周）
- [x] 实现 FAISS 加速器
- [x] 实现混合搜索引擎
- [ ] 安装 FAISS 并测试
- [ ] 性能对比测试（FAISS vs 朴素）
- [ ] 选择最佳索引类型

### 阶段 3: 持久化实现（1-2 周）
- [x] 实现向量索引持久化
- [x] 实现增量更新
- [ ] 集成到主流程
- [ ] 备份策略制定
- [ ] 版本管理规范

### 阶段 4: Redis 缓存（1-2 周）
- [x] 实现 Redis 缓存管理器
- [x] 实现热点检测
- [ ] 部署 Redis 服务
- [ ] 配置缓存策略
- [ ] 监控缓存命中率

### 阶段 5: 性能优化（持续）
- [ ] 模型量化（INT8）
- [ ] GPU 加速
- [ ] 分布式检索
- [ ] 自动调优

## 8. 监控指标

### 8.1 语义准确率
- F1 分数（日报）
- 各类别通过率（周报）
- 用户反馈准确率（持续）

### 8.2 性能指标
- 平均延迟（实时监控）
- P99 延迟（实时监控）
- QPS（实时监控）
- 成功率（实时监控）

### 8.3 缓存指标
- 缓存命中率（小时级）
- 热点查询数（小时级）
- 缓存淘汰率（小时级）
- Redis 内存使用（实时监控）

### 8.4 资源指标
- CPU 使用率（实时监控）
- 内存使用率（实时监控）
- 磁盘 IO（实时监控）
- 网络 IO（实时监控）

## 9. 故障排除

### 问题 1: FAISS 安装失败
```bash
# 尝试预编译版本
pip install faiss-cpu==1.7.4

# 或使用 conda
conda install -c pytorch faiss-cpu
```

### 问题 2: Redis 连接失败
- 检查 Redis 服务是否运行：`redis-cli ping`
- 检查防火墙设置
- 使用内存缓存降级（自动）

### 问题 3: F1 分数不达标
- 增加测试用例多样性
- 调整相似度阈值
- 考虑 fine-tuning 模型

### 问题 4: 性能不达标
- 检查是否使用 FAISS 加速
- 检查缓存命中率
- 考虑批量处理
- 升级硬件（GPU）

## 10. 参考文档

- [FAISS 官方文档](https://github.com/facebookresearch/faiss)
- [BGE 模型文档](https://huggingface.co/BAAI/bge-small-zh-v1.5)
- [Redis 文档](https://redis.io/documentation)
- [语义搜索最佳实践](https://weaviate.io/blog/what-is-hybrid-search)

---

**最后更新**: 2026-04-12  
**维护者**: 架构团队  
**状态**: 实施中
