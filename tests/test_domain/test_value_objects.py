"""
领域层值对象测试
"""

import pytest
from app.domain.value_objects import (
    Money, Quantity, OrderNumber, ContactInfo, Price, ModelNumber
)


class TestMoney:
    """Money 值对象测试"""

    def test_create_money_with_positive_amount(self):
        money = Money(100.0)
        assert money.amount == 100.0
        assert money.currency == "CNY"

    def test_create_money_with_zero(self):
        money = Money(0)
        assert money.amount == 0

    def test_create_money_with_negative_raises_error(self):
        with pytest.raises(ValueError, match="金额不能为负数"):
            Money(-50.0)

    def test_money_addition(self):
        m1 = Money(100.0)
        m2 = Money(50.0)
        result = m1 + m2
        assert result.amount == 150.0
        assert result.currency == "CNY"

    def test_money_addition_different_currency_raises_error(self):
        m1 = Money(100.0, "CNY")
        m2 = Money(50.0, "USD")
        with pytest.raises(ValueError, match="货币单位不一致"):
            m1 + m2

    def test_money_multiplication(self):
        money = Money(100.0)
        result = money * 2
        assert result.amount == 200.0

    def test_money_to_yuan(self):
        money = Money(100.5)
        assert money.to_yuan() == 100.5

    def test_money_immutability(self):
        m1 = Money(100.0)
        m2 = m1 + Money(50.0)
        assert m1.amount == 100.0
        assert m2.amount == 150.0


class TestQuantity:
    """Quantity 值对象测试"""

    def test_create_quantity(self):
        q = Quantity(tins=5, kg=50.0, spec_per_tin=10.0)
        assert q.tins == 5
        assert q.kg == 50.0
        assert q.spec_per_tin == 10.0

    def test_create_quantity_from_tins_and_spec(self):
        q = Quantity.from_tins_and_spec(tins=3, spec_per_tin=20.0)
        assert q.tins == 3
        assert q.kg == 60.0
        assert q.spec_per_tin == 20.0

    def test_quantity_negative_tins_raises_error(self):
        with pytest.raises(ValueError, match="桶数不能为负数"):
            Quantity(tins=-1, kg=0.0)

    def test_quantity_negative_kg_raises_error(self):
        with pytest.raises(ValueError, match="重量不能为负数"):
            Quantity(tins=0, kg=-10.0)


class TestOrderNumber:
    """OrderNumber 值对象测试"""

    def test_create_order_number(self):
        order_num = OrderNumber(value="ORD20260321001")
        assert order_num.value == "ORD20260321001"

    def test_generate_order_number(self):
        order_num = OrderNumber.generate()
        assert len(order_num.value) == 14
        assert order_num.value.isdigit()

    def test_empty_order_number_raises_error(self):
        with pytest.raises(ValueError, match="订单号不能为空"):
            OrderNumber(value="")

    def test_order_number_str(self):
        order_num = OrderNumber(value="ORD001")
        assert str(order_num) == "ORD001"


class TestContactInfo:
    """ContactInfo 值对象测试"""

    def test_create_contact_info(self):
        contact = ContactInfo(person="张三", phone="13800138000", address="测试地址")
        assert contact.person == "张三"
        assert contact.phone == "13800138000"
        assert contact.address == "测试地址"

    def test_contact_info_empty(self):
        contact = ContactInfo.empty()
        assert contact.person == ""
        assert contact.phone == ""
        assert contact.address is None

    def test_contact_info_immutability(self):
        contact = ContactInfo(person="张三", phone="13800138000")
        with pytest.raises(AttributeError):
            contact.person = "李四"


class TestPrice:
    """Price 值对象测试"""

    def test_create_price(self):
        price = Price(unit_price=100.0)
        assert price.unit_price == 100.0
        assert price.discount_rate == 1.0

    def test_create_price_with_discount(self):
        price = Price(unit_price=100.0, discount_rate=0.8)
        assert price.unit_price == 100.0
        assert price.discount_rate == 0.8

    def test_negative_price_raises_error(self):
        with pytest.raises(ValueError, match="单价不能为负数"):
            Price(unit_price=-10.0)

    def test_invalid_discount_rate_raises_error(self):
        with pytest.raises(ValueError, match="折扣率必须在 0-1 之间"):
            Price(unit_price=100.0, discount_rate=1.5)

    def test_final_price(self):
        price = Price(unit_price=100.0, discount_rate=0.9)
        assert price.final_price() == 90.0

    def test_calculate_amount(self):
        price = Price(unit_price=10.0, discount_rate=1.0)
        quantity = Quantity(tins=5, kg=50.0)
        assert price.calculate_amount(quantity) == 500.0


class TestModelNumber:
    """ModelNumber 值对象测试"""

    def test_create_model_number(self):
        model = ModelNumber(value="9803")
        assert model.value == "9803"

    def test_empty_model_number_raises_error(self):
        with pytest.raises(ValueError, match="型号不能为空"):
            ModelNumber(value="")

    def test_model_number_matches_case_insensitive(self):
        m1 = ModelNumber(value="ABC123")
        m2 = ModelNumber(value="abc123")
        assert m1.matches(m2) is True

    def test_model_number_not_matches(self):
        m1 = ModelNumber(value="ABC123")
        m2 = ModelNumber(value="DEF456")
        assert m1.matches(m2) is False

    def test_model_number_contains(self):
        model = ModelNumber(value="ABC-9803-XYZ")
        assert model.contains("9803") is True
        assert model.contains("abc") is True
        assert model.contains("1234") is False

    def test_model_number_str(self):
        model = ModelNumber(value="9803")
        assert str(model) == "9803"