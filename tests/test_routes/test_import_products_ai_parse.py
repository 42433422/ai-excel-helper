"""
产品导入接口 + AI 产品解析集成测试
"""

from unittest.mock import patch, MagicMock


class TestImportProductsWithAIParse:
    """测试 /api/excel/data/import/products 与 AIProductParser 集成。"""

    @patch("app.routes.excel_extract._get_ai_product_parser")
    @patch("app.bootstrap.get_product_import_service")
    @patch("app.bootstrap.get_extract_log_service")
    def test_import_products_with_ai_parse(
        self,
        mock_log_service,
        mock_import_service,
        mock_get_parser,
        client,
    ):
        """启用 use_ai_parse 时，应使用 AIProductParser 标准化字段后再导入。"""
        # 日志服务 mock
        log_instance = MagicMock()
        log_instance.create_log.return_value = 1
        mock_log_service.return_value = log_instance

        # 导入服务 mock
        import_instance = MagicMock()
        import_instance.import_data.return_value = {
            "imported": 1,
            "skipped": 0,
            "failed": 0,
            "details": {"skipped_items": [], "failed_items": []},
        }
        mock_import_service.return_value = import_instance

        # AI 解析器 mock
        parser_instance = MagicMock()
        parser_instance.parse_single.return_value = {
            "success": True,
            "product_code": "9803",
            "product_name": "PE白底漆",
            "specification": "20KG/桶",
            "quantity": 50,
            "unit": "桶",
        }
        mock_get_parser.return_value = parser_instance

        payload = {
            "data": [
                {
                    "原始文本": "9803 PE白底漆 20KG/桶 50桶",
                }
            ],
            "options": {
                "use_ai_parse": True,
                "ai_source_field": "原始文本",
                "skip_duplicates": False,
                "validate_before_import": True,
                "clean_data": True,
            },
            "file_name": "products.xlsx",
        }

        resp = client.post(
            "/api/excel/data/import/products",
            json=payload,
            content_type="application/json",
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("success") is True

        # 确认 AI 解析被调用
        parser_instance.parse_single.assert_called_once()

        # 确认导入服务收到的是经过标准化的字段
        args, kwargs = import_instance.import_data.call_args
        rows = kwargs.get("data") or args[0]
        assert rows[0].get("product_code") == "9803"
        assert rows[0].get("product_name") == "PE白底漆"
        assert rows[0].get("specification") == "20KG/桶"

