from abc import ABC, abstractmethod

from app.domain.customer.entities import Customer, PurchaseUnit


class CustomerRepository(ABC):
    """客户仓储接口"""

    @abstractmethod
    def save_customer(self, customer: Customer) -> Customer:
        pass

    @abstractmethod
    def find_customer_by_id(self, customer_id: int) -> Customer | None:
        pass

    @abstractmethod
    def find_customer_by_name(self, name: str) -> Customer | None:
        pass

    @abstractmethod
    def find_all_customers(self) -> list[Customer]:
        pass

    @abstractmethod
    def delete_customer(self, customer_id: int) -> bool:
        pass

    @abstractmethod
    def save_purchase_unit(self, unit: PurchaseUnit) -> PurchaseUnit:
        pass

    @abstractmethod
    def find_purchase_unit_by_id(self, unit_id: int) -> PurchaseUnit | None:
        pass

    @abstractmethod
    def find_purchase_unit_by_name(self, name: str) -> PurchaseUnit | None:
        pass

    @abstractmethod
    def find_all_purchase_units(self) -> list[PurchaseUnit]:
        pass

    @abstractmethod
    def delete_purchase_unit(self, unit_id: int) -> bool:
        pass
