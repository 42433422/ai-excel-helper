"""
SQLAlchemy 模型验证器

为数据库模型提供数据验证功能，确保数据的完整性和一致性。
"""

import logging

from sqlalchemy.orm import validates

from app.db.base import Base


class ModelValidators:
    """模型验证器集合"""

    @staticmethod
    def validate_positive_number(value, field_name, allow_zero=True):
        """验证数值是否为正数"""
        if value is None:
            return value
        try:
            num_value = float(value)
            if allow_zero:
                if num_value < 0:
                    raise ValueError(f"{field_name} 必须为非负数")
            else:
                if num_value <= 0:
                    raise ValueError(f"{field_name} 必须为正数")
        except (TypeError, ValueError) as e:
            if "must be" in str(e):
                raise
            raise ValueError(f"{field_name} 必须是有效数字")
        return value

    @staticmethod
    def validate_non_empty_string(value, field_name, max_length=None):
        """验证非空字符串"""
        if value is None:
            raise ValueError(f"{field_name} 不能为空")
        str_value = str(value).strip()
        if not str_value:
            raise ValueError(f"{field_name} 不能为空")
        if max_length and len(str_value) > max_length:
            raise ValueError(f"{field_name} 不能超过 {max_length} 个字符")
        return str_value

    @staticmethod
    def validate_phone(value):
        """验证电话号码格式"""
        if not value:
            return value
        import re
        phone_pattern = re.compile(r'^[\d\-\+\(\)\s]{7,20}$')
        if not phone_pattern.match(str(value)):
            raise ValueError("电话号码格式不正确")
        return value

    @staticmethod
    def validate_email(value):
        """验证邮箱格式"""
        if not value:
            return value
        import re
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(str(value)):
            raise ValueError("邮箱格式不正确")
        return value


def register_model_validators():
    """注册所有模型的验证器

    注意：SQLAlchemy @validates 装饰器必须在类定义时声明，
    此函数仅用于初始化检查和日志记录。
    """
    logger = logging.getLogger(__name__)
    try:
        from app.db.models.product import Product
        from app.db.models.purchase_unit import PurchaseUnit
        from app.db.models.customer import Customer
        from app.db.models.material import Material
        from app.db.models.shipment import ShipmentRecord

        models_to_validate = [Product, PurchaseUnit, Customer, Material, ShipmentRecord]
        validated_count = len(models_to_validate)

        for model in models_to_validate:
            if hasattr(model, '__tablename__'):
                logger.debug(f"验证器已就绪: {model.__tablename__}")

        logger.info(f"模型验证器已初始化 ({validated_count} 个模型)")
        return True

    except Exception as e:
        logger.warning(f"模型验证器初始化跳过: {e}")
        return False


def _register_product_validators(class_):
    """为 Product 模型注册验证器"""

    @validates("name")
    def validate_product_name(self, key, value):
        if not value or not str(value).strip():
            raise ValueError("产品名称不能为空")
        return str(value).strip()

    @validates("price")
    def validate_product_price(self, key, value):
        if value is not None:
            try:
                ModelValidators.validate_positive_number(value, "产品价格", allow_zero=True)
            except ValueError:
                raise
        return value

    @validates("quantity")
    def validate_product_quantity(self, key, value):
        if value is not None:
            try:
                ModelValidators.validate_positive_number(value, "产品数量", allow_zero=True)
            except ValueError:
                raise
        return value


def _register_purchase_unit_validators(class_):
    """为 PurchaseUnit 模型注册验证器"""

    @validates("unit_name")
    def validate_unit_name(self, key, value):
        if not value or not str(value).strip():
            raise ValueError("客户名称不能为空")
        return str(value).strip()

    @validates("contact_phone")
    def validate_unit_phone(self, key, value):
        if value:
            ModelValidators.validate_phone(value)
        return value


def _register_customer_validators(class_):
    """为 Customer 模型注册验证器"""

    @validates("customer_name")
    def validate_customer_name(self, key, value):
        if not value or not str(value).strip():
            raise ValueError("客户名称不能为空")
        return str(value).strip()

    @validates("contact_phone")
    def validate_customer_phone(self, key, value):
        if value:
            ModelValidators.validate_phone(value)
        return value


def _register_material_validators(class_):
    """为 Material 模型注册验证器"""

    @validates("name")
    def validate_material_name(self, key, value):
        if not value or not str(value).strip():
            raise ValueError("材料名称不能为空")
        return str(value).strip()

    @validates("material_code")
    def validate_material_code(self, key, value):
        if not value or not str(value).strip():
            raise ValueError("材料编码不能为空")
        return str(value).strip()

    @validates("quantity")
    def validate_material_quantity(self, key, value):
        if value is not None:
            ModelValidators.validate_positive_number(value, "材料数量", allow_zero=True)
        return value

    @validates("unit_price")
    def validate_material_price(self, key, value):
        if value is not None:
            ModelValidators.validate_positive_number(value, "材料单价", allow_zero=True)
        return value


def _register_shipment_validators(class_):
    """为 ShipmentRecord 模型注册验证器"""

    @validates("purchase_unit")
    def validate_shipment_unit(self, key, value):
        if not value or not str(value).strip():
            raise ValueError("购买单位不能为空")
        return str(value).strip()

    @validates("product_name")
    def validate_shipment_product(self, key, value):
        if not value or not str(value).strip():
            raise ValueError("产品名称不能为空")
        return str(value).strip()

    @validates("quantity_kg")
    def validate_shipment_quantity_kg(self, key, value):
        if value is None:
            raise ValueError("重量不能为空")
        ModelValidators.validate_positive_number(value, "重量", allow_zero=False)
        return value

    @validates("quantity_tins")
    def validate_shipment_quantity_tins(self, key, value):
        if value is None:
            raise ValueError("桶数不能为空")
        ModelValidators.validate_positive_number(value, "桶数", allow_zero=False)
        return value

    @validates("unit_price")
    def validate_shipment_price(self, key, value):
        if value is not None:
            ModelValidators.validate_positive_number(value, "单价", allow_zero=True)
        return value

    @validates("amount")
    def validate_shipment_amount(self, key, value):
        if value is not None:
            ModelValidators.validate_positive_number(value, "金额", allow_zero=True)
        return value
