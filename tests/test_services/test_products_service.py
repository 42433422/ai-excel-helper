"""产品库服务单元测试（基于 ProductRepository 端口，非遗留 get_db）。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.products_service import ProductsService


@pytest.fixture
def mock_repo():
    return MagicMock()


@pytest.fixture
def service(mock_repo):
    svc = ProductsService(repository=mock_repo)
    svc._cache = None
    svc._monitor = None
    return svc


class TestGetProducts:
    def test_get_products_tuple_result(self, service, mock_repo):
        row = MagicMock()
        row.to_dict.return_value = {"id": 1, "name": "A"}
        mock_repo.find_all.return_value = ([row], 1)

        result = service.get_products(page=1, per_page=20)

        assert result["success"] is True
        assert result["total"] == 1
        assert result["data"] == [{"id": 1, "name": "A"}]
        mock_repo.find_all.assert_called_once()

    def test_get_products_dict_result(self, service, mock_repo):
        mock_repo.find_all.return_value = {"data": [{"id": 2}], "total": 1}

        result = service.get_products(keyword="x")

        assert result["success"] is True
        assert result["total"] == 1

    def test_get_products_no_repository(self, mock_repo):
        svc = ProductsService(repository=mock_repo)
        svc._repository = None
        result = svc.get_products()
        assert result["success"] is False


class TestGetProduct:
    def test_get_product_found(self, service, mock_repo):
        mock_repo.find_by_id.return_value = {"id": 3, "name": "B"}

        result = service.get_product(3)

        assert result["success"] is True
        assert result["data"]["id"] == 3

    def test_get_product_missing(self, service, mock_repo):
        mock_repo.find_by_id.return_value = None

        result = service.get_product(99)

        assert result["success"] is False
        assert "不存在" in result["message"]


class TestMutations:
    def test_update_product_delegates(self, service, mock_repo):
        mock_repo.update.return_value = {"success": True, "data": {"id": 1}}

        result = service.update_product(1, {"price": 10})

        assert result["success"] is True
        mock_repo.update.assert_called_once_with(1, {"price": 10})

    def test_delete_product_success(self, service, mock_repo):
        mock_repo.delete.return_value = True

        result = service.delete_product(1)

        assert result["success"] is True
        assert "删除成功" in result["message"]

    def test_delete_product_failure(self, service, mock_repo):
        mock_repo.delete.return_value = False

        result = service.delete_product(1)

        assert result["success"] is False

    def test_product_exists(self, service, mock_repo):
        mock_repo.exists.return_value = True
        assert service._product_exists(1) is True
        mock_repo.exists.assert_called_once_with(1)


class TestNormalizeFindAll:
    def test_normalize_list_fallback(self, service):
        products, total = service._normalize_find_all_result([{"id": 1}, {"id": 2}])
        assert len(products) == 2
        assert total == 2

    def test_normalize_empty(self, service):
        products, total = service._normalize_find_all_result(None)
        assert products == []
        assert total == 0
