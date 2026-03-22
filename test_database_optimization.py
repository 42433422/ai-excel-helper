"""
数据库优化验证测试脚本

测试内容：
1. 外键约束验证
2. 级联删除测试
3. 索引存在性验证
4. Alembic 迁移测试
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.db.base import Base
from app.db.init_db import get_db_path
from app.db.models.user import User, Session as UserSession
from app.db.models.ai import (
    AIToolCategory, AITool, AIConversation, AIConversationSession
)
from app.db.models.wechat import (
    WechatContact, WechatTask, WechatContactContext
)
from app.db.models.shipment import ShipmentRecord
from app.db.models.purchase_unit import PurchaseUnit


def get_test_engine():
    """创建测试数据库引擎"""
    db_path = get_db_path("products.db")
    return create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
        echo=False,
    )


def test_foreign_keys_exist():
    """测试外键约束是否存在"""
    print("\n=== 测试外键约束 ===")
    
    engine = get_test_engine()
    conn = engine.connect()
    
    # 定义预期的外键关系 (表名，父表名，子表字段)
    expected_foreign_keys = [
        ('sessions', 'users', 'user_id'),
        ('ai_conversation_sessions', 'users', 'user_id'),
        ('ai_conversations', 'ai_conversation_sessions', 'session_id'),
        ('ai_tools', 'ai_tool_categories', 'category_id'),
        ('wechat_tasks', 'wechat_contacts', 'contact_id'),
        ('wechat_contact_context', 'wechat_contacts', 'contact_id'),
        ('shipment_records', 'purchase_units', 'unit_id')
    ]
    
    all_passed = True
    
    for table, parent_table, column in expected_foreign_keys:
        try:
            result = conn.execute(text(f"PRAGMA foreign_key_list({table})"))
            fks = result.fetchall()
            
            # 检查是否存在指向父表的外键
            fk_exists = any(fk[2] == parent_table and fk[3] == column for fk in fks)
            
            if fk_exists:
                print(f"✓ {table}.{column} -> {parent_table}.id - 存在")
            else:
                print(f"✗ {table}.{column} -> {parent_table}.id - 不存在")
                all_passed = False
        except Exception as e:
            print(f"✗ 检查表 {table} 失败：{e}")
            all_passed = False
    
    conn.close()
    
    if all_passed:
        print("\n✓ 所有外键约束都已创建")
    else:
        print("\n✗ 部分外键约束缺失")
    
    return all_passed


def test_indexes_exist():
    """测试索引是否存在"""
    print("\n=== 测试索引 ===")
    
    engine = get_test_engine()
    conn = engine.connect()
    
    expected_indexes = [
        'idx_shipment_records_status_date',
        'idx_ai_conversations_session_date',
        'idx_products_category_active',
        'idx_wechat_tasks_status_updated',
        'idx_sessions_expires'
    ]
    
    all_passed = True
    
    for index_name in expected_indexes:
        try:
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='index' AND name=:index_name"
            ), {"index_name": index_name})
            
            if result.fetchone():
                print(f"✓ {index_name} - 存在")
            else:
                print(f"✗ {index_name} - 不存在")
                all_passed = False
        except Exception as e:
            print(f"✗ 检查索引 {index_name} 失败：{e}")
            all_passed = False
    
    conn.close()
    
    if all_passed:
        print("\n✓ 所有索引都已创建")
    else:
        print("\n✗ 部分索引缺失")
    
    return all_passed


def test_cascade_delete():
    """测试级联删除功能"""
    print("\n=== 测试级联删除 ===")
    
    from datetime import datetime, timedelta
    
    engine = get_test_engine()
    
    try:
        with Session(engine) as session:
            # 创建测试用户
            test_user = User(username="test_cascade_user", password="hashed_password")
            session.add(test_user)
            session.commit()
            
            # 创建测试会话
            test_session = UserSession(
                session_id="test_cascade_session",
                user_id=test_user.id,
                expires_at=datetime.now() + timedelta(days=365)
            )
            session.add(test_session)
            session.commit()
            
            # 删除用户
            session.delete(test_user)
            session.commit()
            
            # 验证会话是否被级联删除
            remaining_session = session.query(UserSession).filter_by(
                session_id="test_cascade_session"
            ).first()
            
            if remaining_session is None:
                print("✓ 级联删除测试通过 - 会话已被级联删除")
                return True
            else:
                print("✗ 级联删除测试失败 - 会话未被删除")
                return False
                
    except Exception as e:
        print(f"✗ 级联删除测试异常：{e}")
        return False
    finally:
        # 清理测试数据
        with Session(engine) as session:
            session.query(UserSession).filter_by(session_id="test_cascade_session").delete()
            session.query(User).filter_by(username="test_cascade_user").delete()
            session.commit()


def test_alembic_migration():
    """测试 Alembic 迁移状态"""
    print("\n=== 测试 Alembic 迁移状态 ===")
    
    try:
        from alembic.config import Config
        from alembic.command import current, upgrade, downgrade
        from io import StringIO
        
        alembic_cfg = Config('alembic.ini')
        
        # 检查当前版本
        print("当前 Alembic 版本:")
        output = StringIO()
        current(alembic_cfg)
        
        print("\n✓ Alembic 配置正确")
        return True
        
    except Exception as e:
        print(f"✗ Alembic 测试失败：{e}")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("数据库优化验证测试")
    print("=" * 60)
    
    results = {
        '外键约束': test_foreign_keys_exist(),
        '索引': test_indexes_exist(),
        '级联删除': test_cascade_delete(),
        'Alembic 迁移': test_alembic_migration()
    }
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ 所有测试通过！数据库优化成功！")
    else:
        print("✗ 部分测试失败，请检查迁移脚本")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
