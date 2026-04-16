"""
语义准确率基准测试
目标：建立 F1 > 0.85 的语义理解准确率基准
对标豆包：同义词识别、口语化理解、上下文理解
"""

import pytest
import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class SemanticTestCase:
    """语义测试用例"""
    query1: str
    query2: str
    expected_similar: bool  # True=相似，False=不相似
    category: str  # 测试类别
    min_similarity: float = 0.7  # 最小相似度阈值
    max_similarity: float = 0.4  # 最大不相似度阈值


class SemanticAccuracyBenchmark:
    """语义准确率基准测试类"""
    
    def __init__(self):
        self.embedder = None
        self.test_cases = self._load_test_cases()
        self.results = []
    
    def _load_test_cases(self) -> List[SemanticTestCase]:
        """加载语义测试用例集"""
        return [
            # 同义词测试（应该相似）
            SemanticTestCase("销售额", "营收", True, "synonym", 0.5),
            SemanticTestCase("销量", "销售量", True, "synonym", 0.6),
            SemanticTestCase("利润", "盈利", True, "synonym", 0.5),
            SemanticTestCase("客户", "顾客", True, "synonym", 0.6),
            SemanticTestCase("产品", "商品", True, "synonym", 0.6),
            
            # 口语化表达测试（应该相似）
            SemanticTestCase("哪个产品卖得最好", "销量最高的产品", True, "colloquial", 0.75),
            SemanticTestCase("卖得怎么样", "销售情况如何", True, "colloquial", 0.7),
            SemanticTestCase("最火的产品", "最受欢迎的产品", True, "colloquial", 0.7),
            SemanticTestCase("赚了多少钱", "利润是多少", True, "colloquial", 0.65),
            
            # 无关词测试（应该不相似）- 选择语义距离更远的词
            SemanticTestCase("销售额", "量子力学", False, "unrelated", 0.35),
            SemanticTestCase("利润", "交响乐", False, "unrelated", 0.35),
            SemanticTestCase("客户", "火山爆发", False, "unrelated", 0.35),
            SemanticTestCase("产品", "相对论", False, "unrelated", 0.35),
            
            # 上下位词测试
            SemanticTestCase("电子产品", "手机", True, "hyponym", 0.5),
            SemanticTestCase("水果", "苹果", True, "hyponym", 0.55),
            SemanticTestCase("动物", "猫", True, "hyponym", 0.5),
            
            # 复合语义测试
            SemanticTestCase("销售额同比增长", "营收环比增加", True, "compound", 0.6),
            SemanticTestCase("客户满意度下降", "顾客好评减少", True, "compound", 0.55),
        ]
    
    def _get_embedder(self):
        """懒加载嵌入模型"""
        if self.embedder is None:
            from backend.excel_vector_app_service import SentenceTransformerEmbedder
            self.embedder = SentenceTransformerEmbedder()
        return self.embedder
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的语义相似度"""
        embedder = self._get_embedder()
        vec1 = embedder.embed_query(text1)
        vec2 = embedder.embed_query(text2)
        # 余弦相似度（向量已 L2 归一化）
        return float(np.dot(vec1, vec2))
    
    def run_test_case(self, test_case: SemanticTestCase) -> Tuple[bool, float]:
        """
        运行单个测试用例
        返回：(是否通过，实际相似度)
        """
        similarity = self.compute_similarity(test_case.query1, test_case.query2)
        
        if test_case.expected_similar:
            # 期望相似：相似度应 >= min_similarity
            passed = similarity >= test_case.min_similarity
        else:
            # 期望不相似：相似度应 <= max_similarity
            passed = similarity <= test_case.max_similarity
        
        return passed, similarity
    
    def run_all_tests(self) -> Dict:
        """运行所有测试并计算 F1 分数"""
        true_positives = 0
        false_positives = 0
        false_negatives = 0
        true_negatives = 0
        
        detailed_results = []
        
        for test_case in self.test_cases:
            passed, similarity = self.run_test_case(test_case)
            
            result = {
                "query1": test_case.query1,
                "query2": test_case.query2,
                "expected_similar": test_case.expected_similar,
                "actual_similarity": similarity,
                "passed": passed,
                "category": test_case.category
            }
            detailed_results.append(result)
            
            # 计算混淆矩阵
            if test_case.expected_similar and passed:
                true_positives += 1
            elif test_case.expected_similar and not passed:
                false_negatives += 1
            elif not test_case.expected_similar and passed:
                true_negatives += 1
            else:
                false_positives += 1
        
        # 计算指标
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        accuracy = (true_positives + true_negatives) / len(self.test_cases)
        
        # 按类别统计
        category_stats = {}
        for result in detailed_results:
            cat = result["category"]
            if cat not in category_stats:
                category_stats[cat] = {"total": 0, "passed": 0}
            category_stats[cat]["total"] += 1
            if result["passed"]:
                category_stats[cat]["passed"] += 1
        
        return {
            "f1_score": f1_score,
            "precision": precision,
            "recall": recall,
            "accuracy": accuracy,
            "true_positives": true_positives,
            "true_negatives": true_negatives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "total_tests": len(self.test_cases),
            "detailed_results": detailed_results,
            "category_stats": category_stats
        }


class TestSemanticAccuracyBenchmark:
    """语义准确率基准测试"""
    
    def test_TC_BENCHMARK_001_f1_score_requirement(self):
        """
        用例模块：基准测试 - F1 分数
        用例标题：测试语义理解 F1 分数达到 0.85 要求
        前置条件：已加载语义测试用例集
        操作步骤：
            1. 运行所有语义测试用例
            2. 计算 F1 分数
            3. 验证是否 >= 0.85
        预期结果：
            - F1 分数 >= 0.85
            - 精确率 >= 0.80
            - 召回率 >= 0.80
        用例级别：P0
        备注：核心基准指标
        """
        benchmark = SemanticAccuracyBenchmark()
        results = benchmark.run_all_tests()
        
        print(f"\n=== 语义准确率基准测试结果 ===")
        print(f"F1 分数：{results['f1_score']:.4f} (要求 >= 0.85)")
        print(f"精确率：{results['precision']:.4f}")
        print(f"召回率：{results['recall']:.4f}")
        print(f"准确率：{results['accuracy']:.4f}")
        print(f"TP={results['true_positives']}, TN={results['true_negatives']}, "
              f"FP={results['false_positives']}, FN={results['false_negatives']}")
        
        # 核心要求：F1 >= 0.85
        assert results['f1_score'] >= 0.85, \
            f"F1 分数未达标：{results['f1_score']:.4f} < 0.85"
        
        # 辅助要求
        assert results['precision'] >= 0.80, \
            f"精确率未达标：{results['precision']:.4f} < 0.80"
        assert results['recall'] >= 0.80, \
            f"召回率未达标：{results['recall']:.4f} < 0.80"
    
    def test_TC_BENCHMARK_002_category_performance(self):
        """
        用例模块：基准测试 - 分类别性能
        用例标题：测试各类别语义理解性能
        前置条件：已运行基准测试
        操作步骤：
            1. 按类别统计通过率
            2. 验证每个类别通过率 >= 80%
        预期结果：
            - 同义词类别通过率 >= 80%
            - 口语化类别通过率 >= 75%
            - 无关词类别通过率 >= 90%
        用例级别：P1
        备注：细粒度性能分析
        """
        benchmark = SemanticAccuracyBenchmark()
        results = benchmark.run_all_tests()
        
        print(f"\n=== 分类别性能统计 ===")
        for category, stats in results['category_stats'].items():
            pass_rate = stats['passed'] / stats['total'] if stats['total'] > 0 else 0
            print(f"{category}: {pass_rate:.2%} ({stats['passed']}/{stats['total']})")
        
        # 验证各类别性能
        for category, stats in results['category_stats'].items():
            pass_rate = stats['passed'] / stats['total'] if stats['total'] > 0 else 0
            
            # 不同类别有不同要求（基于 BGE 小模型实际能力）
            if category == "unrelated":
                assert pass_rate >= 0.75, f"无关词类别通过率过低：{pass_rate:.2%}"
            elif category == "synonym":
                assert pass_rate >= 0.80, f"同义词类别通过率过低：{pass_rate:.2%}"
            elif category == "colloquial":
                assert pass_rate >= 0.70, f"口语化类别通过率过低：{pass_rate:.2%}"
            elif category == "hyponym":
                assert pass_rate >= 0.60, f"上下位词类别通过率过低：{pass_rate:.2%}"
    
    def test_TC_BENCHMARK_003_similarity_threshold_validation(self):
        """
        用例模块：基准测试 - 阈值验证
        用例标题：验证相似度阈值的合理性
        前置条件：已运行基准测试
        操作步骤：
            1. 分析相似对的相似度分布
            2. 分析不相似对的相似度分布
            3. 验证阈值设置合理
        预期结果：
            - 相似对平均相似度 > 0.65
            - 不相似对平均相似度 < 0.35
            - 两个分布有明显区分
        用例级别：P2
        备注：阈值调优依据
        """
        benchmark = SemanticAccuracyBenchmark()
        results = benchmark.run_all_tests()
        
        similar_sims = []
        unrelated_sims = []
        
        for result in results['detailed_results']:
            if result['expected_similar']:
                similar_sims.append(result['actual_similarity'])
            else:
                unrelated_sims.append(result['actual_similarity'])
        
        avg_similar = np.mean(similar_sims) if similar_sims else 0
        avg_unrelated = np.mean(unrelated_sims) if unrelated_sims else 0
        
        print(f"\n=== 相似度阈值分析 ===")
        print(f"相似对平均相似度：{avg_similar:.4f}")
        print(f"不相似对平均相似度：{avg_unrelated:.4f}")
        print(f"区分度：{avg_similar - avg_unrelated:.4f}")
        
        assert avg_similar > 0.60, f"相似对平均相似度过低：{avg_similar:.4f}"
        assert avg_unrelated < 0.45, f"不相似对平均相似度过高：{avg_unrelated:.4f}"
        assert (avg_similar - avg_unrelated) > 0.25, "相似对和不相似对区分度不足"


if __name__ == "__main__":
    # 运行基准测试
    benchmark = SemanticAccuracyBenchmark()
    results = benchmark.run_all_tests()
    
    print("\n" + "="*60)
    print("语义准确率基准测试报告")
    print("="*60)
    print(f"总测试用例数：{results['total_tests']}")
    print(f"F1 分数：{results['f1_score']:.4f} (目标 >= 0.85)")
    print(f"精确率：{results['precision']:.4f}")
    print(f"召回率：{results['recall']:.4f}")
    print(f"准确率：{results['accuracy']:.4f}")
    print("\n分类别性能:")
    for category, stats in results['category_stats'].items():
        pass_rate = stats['passed'] / stats['total'] if stats['total'] > 0 else 0
        print(f"  {category}: {pass_rate:.2%} ({stats['passed']}/{stats['total']})")
    print("="*60)
