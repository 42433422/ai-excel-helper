# 性能基线报告（自动化入口）

本文件由 CI **Performance Smoke**（k6 `scripts/loadtest/smoke.js`）与 [`capacity-planning.md`](capacity-planning.md) 对齐维护。

## 门禁阈值（PR）

| 指标 | 阈值 | 脚本 |
|------|------|------|
| P99 延迟 | < 500 ms | `smoke.js` `http_req_duration` |
| 错误率 | < 1% | `http_req_failed rate<0.01` |

## 运行方式

```bash
# 本地先启动 API（默认 :5000）
python XCAGI/run.py

# 另开终端
k6 run -e BASE_URL=http://127.0.0.1:5000 scripts/loadtest/smoke.js
```

产物：`results.json`（由 `handleSummary` 导出），CI 上传为 artifact。

## 意图准确率基准

见 [`tests/benchmarks/test_intent_accuracy.py`](../../tests/benchmarks/test_intent_accuracy.py) 与 workflow `intent-benchmark.yml`。

- 默认门槛：`INTENT_BENCHMARK_MIN_ACCURACY=0.85`
- 营销「99%+」验证：手动 `workflow_dispatch` 设 `INTENT_BENCHMARK_MIN_ACCURACY=0.99`；未达标须修订 README/对比报告措辞。
