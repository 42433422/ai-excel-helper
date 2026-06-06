from abc import ABC, abstractmethod

from app.domain.product.entities import Product


class ProductRepository(ABC):
    """产品仓储接口"""

    @abstractmethod
    def save(self, product: Product) -> Product:
        pass

    @abstractmethod
    def find_by_id(self, product_id: int) -> Product | None:
        pass

    @abstractmethod
    def find_all(self, page: int = 1, per_page: int = 20) -> list[Product]:
        pass

    @abstractmethod
    def find_all_dict(self, page: int = 1, per_page: int = 20, **kwargs) -> tuple:
        pass

    @abstractmethod
    def find_by_model_number(self, model_number: str) -> Product | None:
        pass

    @abstractmethod
    def find_by_name(self, name: str) -> list[Product]:
        pass

    @abstractmethod
    def delete(self, product_id: int) -> bool:
        pass

    @abstractmethod
    def count(self) -> int:
        pass
