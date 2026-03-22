"""
AI 产品解析路由测试
"""

from unittest.mock import patch


class TestAIParseSingle:
    """单条解析接口测试"""

    def test_parse_single_success_in_order(self, client):
        """顺序正常的语句应解析成功"""
        text = "9803 PE白底漆 20KG/桶 50桶"
        resp = client.post(
            "/api/ai/parse-single",
            json={"text": text, "use_ai": False, "fallback_to_rule": True},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("success") is True
        assert data.get("unit") == "桶"
        assert data.get("quantity") == 50
        assert data.get("specification")

    def test_parse_single_success_permuted(self, client):
        """同语义乱序输入也应解析成功"""
        text = "50桶 20KG/桶 9803 PE白底漆"
        resp = client.post(
            "/api/ai/parse-single",
            json={"text": text, "use_ai": False, "fallback_to_rule": True},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("success") is True
        assert data.get("unit") == "桶"
        assert data.get("quantity") == 50
        assert data.get("specification")

    def test_parse_single_missing_specification(self, client):
        """缺少规格时应失败并返回 missing_fields"""
        text = "七彩乐园 9803 3桶"
        resp = client.post(
            "/api/ai/parse-single",
            json={"text": text, "use_ai": False, "fallback_to_rule": True},
            content_type="application/json",
        )
        assert resp.status_code == 422
        data = resp.get_json()
        assert data.get("success") is False
        missing = data.get("missing_fields", [])
        assert "specification" in missing
        assert data.get("invalid_reason")

    def test_parse_single_empty_text(self, client):
        """空文本应返回 400"""
        resp = client.post(
            "/api/ai/parse-single",
            json={"text": "   "},
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data.get("success") is False
        assert data.get("invalid_reason") == "输入为空，无法解析"


class TestAIParseBatch:
    """批量解析接口测试"""

    def test_parse_products_success(self, client):
        """批量解析返回 items 列表"""
        texts = [
            "9803 PE白底漆 20KG/桶 50桶",
            "50桶 20KG/桶 9803 PE白底漆",
        ]
        resp = client.post(
            "/api/ai/parse-products",
            json={"texts": texts, "use_ai": False, "fallback_to_rule": True},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("success") is True
        items = data.get("items", [])
        assert len(items) == 2
        assert all("unit" in item for item in items)

    def test_parse_products_invalid_payload(self, client):
        """texts 为空或类型错误时返回 400"""
        resp = client.post(
            "/api/ai/parse-products",
            json={"texts": []},
            content_type="application/json",
        )
        assert resp.status_code == 400

        resp2 = client.post(
            "/api/ai/parse-products",
            json={"texts": "not a list"},
            content_type="application/json",
        )
        assert resp2.status_code == 400

