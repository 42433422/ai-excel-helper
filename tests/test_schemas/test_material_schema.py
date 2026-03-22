# -*- coding: utf-8 -*-
"""
Material Schema 测试

测试 MaterialCreate、MaterialUpdate 等 Pydantic 模型的验证逻辑。
"""

import pytest
from pydantic import ValidationError
from app.schemas.material_schema import (
    MaterialCreate,
    MaterialUpdate,
    MaterialResponse,
)


class TestMaterialCreate:
    """MaterialCreate 模型测试"""

    def test_valid_material(self):
        """测试有效数据"""
        material = MaterialCreate(
            name="测试原材料",
            material_code="M-001",
            quantity=100,
            unit_price=50.0,
            unit="kg"
        )
        assert material.name == "测试原材料"
        assert material.material_code == "M-001"
        assert material.quantity == 100
        assert material.unit_price == 50.0

    def test_name_empty_string_rejected(self):
        """测试空字符串名称被拒绝"""
        with pytest.raises(ValidationError) as exc_info:
            MaterialCreate(name="   ")
        errors = exc_info.value.errors()
        assert any("不能为空" in str(e.get("msg", "")) for e in errors)

    def test_name_whitespace_trimmed(self):
        """测试名称前后空格被去除"""
        material = MaterialCreate(name="  测试名称  ")
        assert material.name == "测试名称"

    def test_material_code_valid_format(self):
        """测试有效的编码格式"""
        material = MaterialCreate(
            name="测试",
            material_code="M-001-ABC"
        )
        assert material.material_code == "M-001-ABC"

    def test_material_code_invalid_characters_rejected(self):
        """测试无效编码字符被拒绝"""
        with pytest.raises(ValidationError) as exc_info:
            MaterialCreate(name="测试", material_code="M@001!")
        errors = exc_info.value.errors()
        assert any("只能包含" in str(e.get("msg", "")) for e in errors)

    def test_material_code_with_underscore_valid(self):
        """测试带下划线的编码"""
        material = MaterialCreate(name="测试", material_code="M_001_ABC")
        assert material.material_code == "M_001_ABC"

    def test_negative_quantity_rejected(self):
        """测试负数数量被拒绝"""
        with pytest.raises(ValidationError):
            MaterialCreate(name="测试", quantity=-10)

    def test_negative_unit_price_rejected(self):
        """测试负数单价被拒绝"""
        with pytest.raises(ValidationError):
            MaterialCreate(name="测试", unit_price=-5.0)

    def test_zero_quantity_allowed(self):
        """测试零数量是允许的"""
        material = MaterialCreate(name="测试", quantity=0)
        assert material.quantity == 0

    def test_default_values(self):
        """测试默认值"""
        material = MaterialCreate(name="测试")
        assert material.unit == "个"
        assert material.quantity == 0
        assert material.unit_price == 0
        assert material.min_stock == 0
        assert material.max_stock == 0

    def test_optional_fields_can_be_none(self):
        """测试可选字段可以为 None"""
        material = MaterialCreate(
            name="测试",
            category=None,
            specification=None,
            supplier=None
        )
        assert material.category is None
        assert material.specification is None

    def test_name_too_long_rejected(self):
        """测试超长名称被拒绝"""
        with pytest.raises(ValidationError):
            MaterialCreate(name="x" * 201)


class TestMaterialUpdate:
    """MaterialUpdate 模型测试"""

    def test_partial_update(self):
        """测试部分更新"""
        update = MaterialUpdate(name="新名称")
        assert update.name == "新名称"
        assert update.quantity is None

    def test_all_fields_optional(self):
        """测试所有字段都是可选的"""
        update = MaterialUpdate()
        assert update.name is None
        assert update.quantity is None

    def test_update_with_empty_name_rejected(self):
        """测试更新时空名称被拒绝"""
        with pytest.raises(ValidationError):
            MaterialUpdate(name="")


class TestMaterialResponse:
    """MaterialResponse 模型测试"""

    def test_response_model_config(self):
        """测试响应模型配置"""
        assert MaterialResponse.model_config.get("from_attributes") == True
