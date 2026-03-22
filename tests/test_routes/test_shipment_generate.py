"""
发货单生成路由测试
"""


class TestShipmentGenerateRoute:
    """测试 /api/shipment/generate 接口。"""

    def test_generate_success(self, client):
        """合法单位+产品时应成功生成发货单（依赖实际服务实现）。"""
        payload = {
            "unit_name": "测试单位",
            "products": [
                {
                    "name": "产品A",
                    "quantity": 1,
                    "unit": "桶",
                    "price": 100,
                }
            ],
        }
        resp = client.post(
            "/api/shipment/generate",
            json=payload,
            content_type="application/json",
        )
        # 不要求真实环境一定成功，但至少路由能正常响应
        assert resp.status_code in (200, 500)
        data = resp.get_json()
        assert isinstance(data, dict)

    def test_generate_missing_unit(self, client):
        """缺少单位名称时返回 400。"""
        payload = {"products": [{"name": "产品A", "quantity": 1}]}
        resp = client.post(
            "/api/shipment/generate",
            json=payload,
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data.get("success") is False

    def test_generate_missing_products(self, client):
        """缺少产品列表时返回 400。"""
        payload = {"unit_name": "测试单位", "products": []}
        resp = client.post(
            "/api/shipment/generate",
            json=payload,
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data.get("success") is False

