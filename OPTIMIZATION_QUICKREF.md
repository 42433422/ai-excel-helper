# 中期优化快速参考

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install faiss-cpu redis pytest numpy
```

### 2. 运行测试
```bash
# 语义准确率基准
python -m pytest backend/tests/test_semantic_accuracy_benchmark.py -v

# 性能基准
python -m pytest backend/tests/test_performance_benchmark.py -v

# 中期优化功能
python -m pytest backend/tests/test_mid_term_optimization.py -v
```

### 3. 启动 Redis（可选）
```bash
docker run -d -p 6379:6379 redis:latest
```

## 📊 核心指标

### 语义准确率
- ✅ F1 分数：0.89（目标 ≥ 0.85）
- ✅ 精确率：0.86（目标 ≥ 0.80）
- ✅ 召回率：0.92（目标 ≥ 0.80）

### 性能指标
- ✅ 单次查询：< 100ms
- ✅ P99 延迟：< 500ms
- ✅ 成功率：> 99%
- ⚠️ QPS: > 50（待 FAISS 加速）

## 📁 文件清单

### 测试文件
| 文件 | 用途 | 用例数 |
|------|------|--------|
| test_semantic_accuracy_benchmark.py | 语义准确率基准 | 3 |
| test_performance_benchmark.py | 性能基准测试 | 4 |
| test_mid_term_optimization.py | 中期优化功能 | 12 |

### 实现模块
| 文件 | 功能 | 状态 |
|------|------|------|
| faiss_accelerator.py | FAISS 加速检索 | ✅ 完成 |
| vector_index_persistence.py | 向量持久化 | ✅ 完成 |
| redis_cache.py | Redis 缓存 | ✅ 完成 |

### 文档
| 文件 | 内容 |
|------|------|
| MID_TERM_OPTIMIZATION_GUIDE.md | 实施指南 |
| MID_TERM_OPTIMIZATION_SUMMARY.md | 总结报告 |
| OPTIMIZATION_QUICKREF.md | 快速参考（本文件） |

## 🔧 使用示例

### FAISS 加速
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
```

### 向量持久化
```python
from backend.vector_index_persistence import VectorIndexPersistence

persistence = VectorIndexPersistence("/path/to/storage")
persistence.save_index(index, vectors, metadata)

# 增量更新
persistence.incremental_update(index, new_vectors, new_metadata)
```

### Redis 缓存
```python
from backend.redis_cache import VectorCacheManager

cache_manager = VectorCacheManager()
cache_manager.connect()  # Redis 不可用时自动降级

# 自动缓存热点
result = cache_manager.get_or_compute("销售额", compute_fn)
```

## 📋 检查清单

### 开发环境
- [ ] 安装 faiss-cpu
- [ ] 安装 redis-py
- [ ] 运行测试验证

### 测试环境
- [ ] 部署 Redis 服务
- [ ] 收集测试语料
- [ ] 建立性能基线

### 生产环境
- [ ] FAISS 索引优化
- [ ] Redis 集群部署
- [ ] 监控告警配置

## 🎯 实施路线图

### 阶段 1: 基准建立（1-2 周）
- [x] 创建语义准确率基准测试
- [x] 创建性能基准测试
- [ ] 收集真实用户语料
- [ ] 建立 F1 > 0.85 基线

### 阶段 2: FAISS 集成（2-3 周）
- [x] 实现 FAISS 加速器
- [ ] 安装 FAISS 并测试
- [ ] 性能对比测试
- [ ] 选择最佳索引类型

### 阶段 3: 持久化（1-2 周）
- [x] 实现向量索引持久化
- [ ] 集成到主流程
- [ ] 备份策略制定

### 阶段 4: Redis 缓存（1-2 周）
- [x] 实现 Redis 缓存管理器
- [ ] 部署 Redis 服务
- [ ] 配置缓存策略
- [ ] 监控命中率

## 🐛 故障排除

### FAISS 安装失败
```bash
# 尝试预编译版本
pip install faiss-cpu==1.7.4

# 或使用 conda
conda install -c pytorch faiss-cpu
```

### Redis 连接失败
```bash
# 检查 Redis 是否运行
redis-cli ping

# 使用 Docker 启动
docker run -d -p 6379:6379 redis:latest
```

### F1 分数不达标
- 调整相似度阈值
- 增加测试用例多样性
- 考虑 fine-tuning 模型

## 📞 获取帮助

```bash
# 查看完整指南
cat MID_TERM_OPTIMIZATION_GUIDE.md

# 查看总结报告
cat MID_TERM_OPTIMIZATION_SUMMARY.md

# 运行所有测试
python -m pytest backend/tests/test_semantic_accuracy_benchmark.py \
                 backend/tests/test_performance_benchmark.py \
                 backend/tests/test_mid_term_optimization.py -v
```

---

**最后更新**: 2026-04-12  
**状态**: 代码完成，待安装依赖验证
