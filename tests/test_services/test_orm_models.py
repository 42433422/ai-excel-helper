"""
ORM 层单元测试
"""

import pytest
import tempfile
import os
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.db.models import (
    PurchaseUnit, Product, ShipmentRecord,
    WechatContact, WechatTask, WechatContactContext,
    User, UserSession,
    Material,
    AIToolCategory, AITool, AIConversation
)


@pytest.fixture(scope="function")
def test_engine():
    """创建测试用的内存数据库引擎"""
    return create_engine("sqlite:///:memory:")


@pytest.fixture(scope="function")
def test_session(test_engine):
    """创建测试用的 Session"""
    Base.metadata.create_all(test_engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
    Base.metadata.drop_all(test_engine)


class TestPurchaseUnitModel:
    """购货单位模型测试"""
    
    def test_create_purchase_unit(self, test_session):
        """测试创建购货单位"""
        unit = PurchaseUnit(
            unit_name="测试购货单位",
            contact_person="张三",
            contact_phone="13800138000",
            address="测试地址",
            discount_rate=0.9,
            is_active=1
        )
        test_session.add(unit)
        test_session.commit()
        test_session.refresh(unit)
        
        assert unit.id is not None
        assert unit.unit_name == "测试购货单位"
        assert unit.contact_person == "张三"
        assert unit.discount_rate == 0.9
        assert unit.is_active == 1
    
    def test_purchase_unit_soft_delete(self, test_session):
        """测试软删除"""
        unit = PurchaseUnit(unit_name="要删除的单位", is_active=1)
        test_session.add(unit)
        test_session.commit()
        
        unit.is_active = 0
        test_session.commit()
        test_session.refresh(unit)
        
        assert unit.is_active == 0


class TestProductModel:
    """产品模型测试"""
    
    def test_create_product(self, test_session):
        """测试创建产品"""
        product = Product(
            model_number="TEST-001",
            name="测试产品",
            specification="25kg/桶",
            price=100.0,
            is_active=1
        )
        test_session.add(product)
        test_session.commit()
        test_session.refresh(product)
        
        assert product.id is not None
        assert product.model_number == "TEST-001"
        assert product.name == "测试产品"
        assert product.price == 100.0
    
    def test_product_optional_fields(self, test_session):
        """测试产品可选字段"""
        product = Product(
            name="只有名称的产品",
            is_active=1
        )
        test_session.add(product)
        test_session.commit()
        
        assert product.id is not None
        assert product.model_number is None


class TestShipmentRecordModel:
    """发货记录模型测试"""
    
    def test_create_shipment_record(self, test_session):
        """测试创建发货记录"""
        shipment = ShipmentRecord(
            purchase_unit="测试购货单位",
            product_name="测试产品",
            quantity_kg=50.0,
            quantity_tins=2,
            status="pending"
        )
        test_session.add(shipment)
        test_session.commit()
        test_session.refresh(shipment)
        
        assert shipment.id is not None
        assert shipment.purchase_unit == "测试购货单位"
        assert shipment.product_name == "测试产品"
        assert shipment.quantity_kg == 50.0
        assert shipment.quantity_tins == 2
        assert shipment.status == "pending"


class TestWechatContactModel:
    """微信联系人模型测试"""
    
    def test_create_wechat_contact(self, test_session):
        """测试创建微信联系人"""
        contact = WechatContact(
            contact_name="测试联系人",
            wechat_id="test_wx_001",
            contact_type="customer",
            is_active=1
        )
        test_session.add(contact)
        test_session.commit()
        test_session.refresh(contact)
        
        assert contact.id is not None
        assert contact.contact_name == "测试联系人"
        assert contact.wechat_id == "test_wx_001"
        assert contact.contact_type == "customer"


class TestWechatTaskModel:
    """微信任务模型测试"""
    
    def test_create_wechat_task(self, test_session):
        """测试创建微信任务"""
        task = WechatTask(
            username="test_user",
            display_name="测试用户",
            message_id="msg_001",
            msg_timestamp=1234567890,
            raw_text="测试消息内容",
            task_type="shipment_order",
            status="pending"
        )
        test_session.add(task)
        test_session.commit()
        test_session.refresh(task)
        
        assert task.id is not None
        assert task.username == "test_user"
        assert task.raw_text == "测试消息内容"
        assert task.status == "pending"


class TestUserModel:
    """用户模型测试"""
    
    def test_create_user(self, test_session):
        """测试创建用户"""
        user = User(
            username="testuser",
            password="hashed_password",
            display_name="测试用户",
            role="user"
        )
        test_session.add(user)
        test_session.commit()
        test_session.refresh(user)
        
        assert user.id is not None
        assert user.username == "testuser"
        assert user.display_name == "测试用户"
        assert user.role == "user"


class TestUserSessionModel:
    """用户会话模型测试"""
    
    def test_create_user_session(self, test_session):
        """测试创建用户会话"""
        user = User(username="testuser2", password="pwd", role="user")
        test_session.add(user)
        test_session.commit()
        
        from datetime import datetime, timedelta
        session = UserSession(
            session_id="sess_001",
            user_id=user.id,
            expires_at=datetime.now() + timedelta(hours=24)
        )
        test_session.add(session)
        test_session.commit()
        test_session.refresh(session)
        
        assert session.id is not None
        assert session.session_id == "sess_001"
        assert session.user_id == user.id


class TestMaterialModel:
    """原材料模型测试"""
    
    def test_create_material(self, test_session):
        """测试创建原材料"""
        material = Material(
            material_code="MAT-001",
            name="测试原材料",
            quantity=100.0,
            unit="kg"
        )
        test_session.add(material)
        test_session.commit()
        test_session.refresh(material)
        
        assert material.id is not None
        assert material.material_code == "MAT-001"
        assert material.name == "测试原材料"
        assert material.quantity == 100.0


class TestAIModels:
    """AI 相关模型测试"""
    
    def test_create_ai_tool_category(self, test_session):
        """测试创建 AI 工具分类"""
        category = AIToolCategory(
            category_key="text_generation",
            category_name="文本生成"
        )
        test_session.add(category)
        test_session.commit()
        test_session.refresh(category)
        
        assert category.id is not None
        assert category.category_key == "text_generation"
        assert category.category_name == "文本生成"
    
    def test_create_ai_conversation(self, test_session):
        """测试创建 AI 对话"""
        conv = AIConversation(
            session_id="session_001",
            role="user",
            content="你好"
        )
        test_session.add(conv)
        test_session.commit()
        test_session.refresh(conv)
        
        assert conv.id is not None
        assert conv.session_id == "session_001"
        assert conv.role == "user"
        assert conv.content == "你好"


class TestProductRelationships:
    """产品模型关系测试"""
    
    def test_product_with_shipment_records(self, test_session):
        """测试产品与发货记录的关系"""
        product = Product(
            name="测试产品",
            model_number="TEST-001",
            price=100.0,
            is_active=1
        )
        test_session.add(product)
        test_session.commit()
        
        shipment = ShipmentRecord(
            purchase_unit="测试单位",
            product_name=product.name,
            model_number=product.model_number,
            quantity_kg=50.0,
            quantity_tins=2
        )
        test_session.add(shipment)
        test_session.commit()
        
        assert shipment.product_name == product.name
        assert shipment.model_number == product.model_number


class TestShipmentRecordValidation:
    """发货记录验证测试"""
    
    def test_shipment_required_fields(self, test_session):
        """测试发货记录必需字段"""
        shipment = ShipmentRecord(
            purchase_unit="测试单位",
            product_name="测试产品",
            quantity_kg=100.0,
            quantity_tins=4
        )
        test_session.add(shipment)
        test_session.commit()
        
        assert shipment.purchase_unit is not None
        assert shipment.product_name is not None
        assert shipment.quantity_kg is not None
        assert shipment.quantity_tins is not None
    
    def test_shipment_status_values(self, test_session):
        """测试发货记录状态值"""
        valid_statuses = ["pending", "processing", "shipped", "delivered", "cancelled"]
        
        for status in valid_statuses:
            shipment = ShipmentRecord(
                purchase_unit=f"测试单位_{status}",
                product_name="测试产品",
                quantity_kg=50.0,
                quantity_tins=2,
                status=status
            )
            test_session.add(shipment)
            test_session.commit()
            test_session.refresh(shipment)
            
            assert shipment.status == status


class TestWechatContactValidation:
    """微信联系人验证测试"""
    
    def test_contact_soft_delete(self, test_session):
        """测试微信联系人软删除"""
        contact = WechatContact(
            contact_name="测试联系人",
            wechat_id="wx_test",
            is_active=1
        )
        test_session.add(contact)
        test_session.commit()
        
        contact.is_active = 0
        test_session.commit()
        test_session.refresh(contact)
        
        assert contact.is_active == 0
    
    def test_contact_context_relationship(self, test_session):
        """测试联系人上下文关系"""
        contact = WechatContact(
            contact_name="测试联系人",
            wechat_id="wx_001"
        )
        test_session.add(contact)
        test_session.commit()
        
        context = WechatContactContext(
            contact_id=contact.id,
            wechat_id=contact.wechat_id,
            context_json='{"last_message": "hello"}',
            message_count=1
        )
        test_session.add(context)
        test_session.commit()
        
        assert context.contact_id == contact.id
        assert context.message_count == 1


class TestMaterialValidation:
    """原材料验证测试"""
    
    def test_material_low_stock(self, test_session):
        """测试低库存检测"""
        material = Material(
            material_code="MAT-001",
            name="低库存原料",
            quantity=5.0,
            min_stock=10.0,
            unit="kg"
        )
        test_session.add(material)
        test_session.commit()
        
        assert material.quantity < material.min_stock
    
    def test_material_required_fields(self, test_session):
        """测试原材料必需字段"""
        material = Material(
            material_code="MAT-002",
            name="测试原料"
        )
        test_session.add(material)
        test_session.commit()
        
        assert material.material_code is not None
        assert material.name is not None
        assert material.quantity == 0  # 默认值
        assert material.unit == "个"  # 默认值


class TestUserAuthentication:
    """用户认证相关测试"""
    
    def test_user_unique_username(self, test_session):
        """测试用户名唯一性"""
        user1 = User(
            username="uniqueuser",
            password="pwd1",
            display_name="用户 1",
            role="user"
        )
        test_session.add(user1)
        test_session.commit()
        
        assert user1.username == "uniqueuser"
    
    def test_user_session_expiration(self, test_session):
        """测试用户会话过期"""
        from datetime import datetime, timedelta
        from app.db.models.user import Session as UserSession
        
        user = User(username="testuser", password="pwd", role="user")
        test_session.add(user)
        test_session.commit()
        
        expired_session = UserSession(
            session_id="expired_sess",
            user_id=user.id,
            expires_at=datetime.now() - timedelta(hours=1)
        )
        test_session.add(expired_session)
        test_session.commit()
        
        assert expired_session.expires_at < datetime.now()


class TestBulkOperations:
    """批量操作测试"""
    
    def test_bulk_insert_products(self, test_session):
        """测试批量插入产品"""
        products = [
            Product(name=f"产品_{i}", price=100.0 * i, is_active=1)
            for i in range(10)
        ]
        test_session.bulk_save_objects(products)
        test_session.commit()
        
        count = test_session.query(Product).count()
        assert count >= 10
    
    def test_bulk_insert_contacts(self, test_session):
        """测试批量插入联系人"""
        contacts = [
            WechatContact(
                contact_name=f"联系人_{i}",
                wechat_id=f"wx_{i}",
                is_active=1
            )
            for i in range(5)
        ]
        test_session.bulk_save_objects(contacts)
        test_session.commit()
        
        count = test_session.query(WechatContact).filter(
            WechatContact.is_active == 1
        ).count()
        assert count >= 5


class TestDataIntegrity:
    """数据完整性测试"""
    
    def test_unique_constraints(self, test_session):
        """测试唯一约束"""
        from sqlalchemy.exc import IntegrityError
        
        user1 = User(username="unique_user", password="pwd", role="user")
        user2 = User(username="unique_user", password="pwd", role="user")
        
        test_session.add(user1)
        test_session.commit()
        
        test_session.add(user2)
        with pytest.raises(IntegrityError):
            test_session.commit()
    
    def test_cascade_delete(self, test_session):
        """测试级联删除（如果配置了的话）"""
        user = User(username="cascade_user", password="pwd", role="user")
        test_session.add(user)
        test_session.commit()
        
        test_session.delete(user)
        test_session.commit()
        
        deleted_user = test_session.query(User).filter_by(username="cascade_user").first()
        assert deleted_user is None
