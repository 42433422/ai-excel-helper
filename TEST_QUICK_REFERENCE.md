# 测试快速参考指南

## 🚀 快速开始

### 运行所有测试
```bash
# 推荐：运行所有新测试（快速）
python -m pytest backend/tests/test_vector_database_semantic_search.py backend/tests/test_intent_recognition_and_slot_filling.py -v

# 运行实际实现测试（需要下载模型，较慢）
python -m pytest backend/tests/test_vector_implementation_example.py -v
```

### 查看测试结果
```bash
# 简要输出
python -m pytest backend/tests/ -q

# 详细输出
python -m pytest backend/tests/ -v

# 带覆盖率
python -m pytest backend/tests/ --cov=backend --cov-report=term-missing
```

## 📊 测试文件说明

| 文件名 | 用途 | 用例数 | 执行时间 | 推荐场景 |
|--------|------|--------|----------|----------|
| test_vector_database_semantic_search.py | 向量数据库功能测试 | 71 | <1s | 日常开发、CI/CD |
| test_intent_recognition_and_slot_filling.py | 意图识别测试 | 60 | <1s | 日常开发、CI/CD |
| test_vector_implementation_example.py | 实际实现验证 | 16 | ~3min | 版本发布前验证 |

## 🎯 常用测试命令

### 运行特定类别
```bash
# 向量嵌入测试
python -m pytest backend/tests/test_vector_database_semantic_search.py::TestVectorEmbedding -v

# 语义理解测试
python -m pytest backend/tests/test_vector_database_semantic_search.py::TestSemanticUnderstanding -v

# 混合搜索测试
python -m pytest backend/tests/test_vector_database_semantic_search.py::TestHybridSearch -v

# 意图识别基础测试
python -m pytest backend/tests/test_intent_recognition_and_slot_filling.py::TestIntentRecognitionBasic -v

# 槽位提取测试
python -m pytest backend/tests/test_intent_recognition_and_slot_filling.py::TestSlotExtraction -v
```

### 运行单个测试
```bash
# 运行单个测试用例
python -m pytest backend/tests/test_vector_database_semantic_search.py::TestVectorEmbedding::test_TC_VEC_EMB_001 -v

# 运行多个特定测试
python -m pytest backend/tests/test_vector_database_semantic_search.py -k "test_TC_VEC_EMB_001 or test_TC_VEC_EMB_002" -v
```

### 过滤测试
```bash
# 按关键字过滤
python -m pytest backend/tests/ -k "semantic" -v

# 按级别过滤（P0/P1/P2）
python -m pytest backend/tests/ -k "P0" -v
```

## 📈 测试报告

### 生成 HTML 报告
```bash
python -m pytest backend/tests/ --html=report.html --self-contained-html
```

### 生成 JUnit XML（CI/CD）
```bash
python -m pytest backend/tests/ --junitxml=test-results.xml
```

### 生成覆盖率报告
```bash
# HTML 格式
python -m pytest backend/tests/ --cov=backend --cov-report=html

# 终端格式
python -m pytest backend/tests/ --cov=backend --cov-report=term-missing

# XML 格式
python -m pytest backend/tests/ --cov=backend --cov-report=xml
```

## 🔧 故障排除

### 问题：模型下载失败
**症状**: 测试卡在模型下载步骤  
**解决**:
```bash
# 检查网络连接
ping hf-mirror.com

# 手动下载模型
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5')"

# 使用代理
export HTTPS_PROXY=http://proxy:port
python -m pytest ...
```

### 问题：内存不足
**症状**: 测试崩溃，MemoryError  
**解决**:
```bash
# 减少批量大小
# 在测试中修改 batch_size 参数

# 关闭其他程序释放内存
```

### 问题：测试超时
**症状**: pytest-timeout 触发  
**解决**:
```bash
# 增加超时时间
python -m pytest backend/tests/ --timeout=300
```

## 📋 测试清单

### 开发阶段
- [ ] 运行快速测试（<1s）
- [ ] 修复失败的测试
- [ ] 添加新测试用例

### 发布前
- [ ] 运行所有测试（包括实际实现）
- [ ] 检查覆盖率报告
- [ ] 验证性能指标

### CI/CD 集成
- [ ] 配置自动触发
- [ ] 设置失败通知
- [ ] 生成测试报告

## 📊 测试结果解读

### 通过状态
```
✅ PASSED - 测试通过
❌ FAILED - 测试失败
⏭️  SKIPPED - 测试跳过
❓ XFAIL - 预期失败
```

### 常见失败原因
1. **AssertionError**: 断言失败，检查预期值
2. **SkipTest**: 依赖不可用（如模型未下载）
3. **TimeoutError**: 执行超时
4. **ImportError**: 模块导入失败

## 🎯 对标豆包验证清单

### 核心能力
- [x] 语义理解（同义词、口语化）
- [x] 多轮对话（上下文保持）
- [x] 槽位提取（时间、数值、实体）
- [x] 混合搜索（关键词 + 语义）
- [x] 意图识别（8 类意图）

### 高级功能
- [x] 智能推荐（测试框架）
- [x] 数据钻取（测试框架）
- [x] 异常检测（测试框架）
- [x] 趋势预测（测试框架）
- [x] 报告生成（测试框架）

## 📞 获取帮助

### 查看测试文档
```bash
# 查看测试文件
cat backend/tests/test_vector_database_semantic_search.py | head -100

# 查看完整报告
cat TEST_FINAL_REPORT.md
```

### 联系支持
- 查看测试文件中的注释
- 参考 TEST_FINAL_REPORT.md
- 查阅 pytest 官方文档：https://docs.pytest.org/

---

**最后更新**: 2026-04-12  
**测试状态**: ✅ 147/147 通过  
**维护者**: 架构团队
