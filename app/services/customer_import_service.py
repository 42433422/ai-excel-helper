# -*- coding: utf-8 -*-
"""
客户导入导出服务
"""
import logging
from typing import Dict, Any, Optional
from app.db.session import get_db
from app.db.models.customer import Customer
from sqlalchemy import func

logger = logging.getLogger(__name__)


class CustomerImportService:
    """客户导入导出服务类"""
    
    def import_from_excel(self, file) -> Dict[str, Any]:
        """从 Excel 导入客户"""
        try:
            # TODO: 实现 Excel 导入逻辑
            return {
                "success": True,
                "message": "导入功能待实现",
                "updated": 0,
                "inserted": 0,
                "skipped": 0
            }
        except Exception as e:
            logger.exception(f"导入失败：{e}")
            raise
    
    def export_to_excel(self, keyword: Optional[str] = None) -> Dict[str, Any]:
        """导出客户到 Excel"""
        try:
            # TODO: 实现 Excel 导出逻辑
            return {
                "success": True,
                "message": "导出功能待实现",
                "file_path": None,
                "filename": "客户导出.xlsx"
            }
        except Exception as e:
            logger.exception(f"导出失败：{e}")
            raise
    
    def get_all(
        self,
        keyword: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """获取所有客户"""
        try:
            with get_db() as db:
                query = db.query(Customer)
                
                if keyword:
                    pattern = f"%{keyword}%"
                    query = query.filter(Customer.customer_name.like(pattern))
                
                total = query.count()
                customers = query.order_by(Customer.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
                
                return {
                    "success": True,
                    "data": [
                        {
                            "id": c.id,
                            "customer_name": c.customer_name,
                            "contact_person": c.contact_person,
                            "contact_phone": c.contact_phone,
                            "contact_address": c.contact_address,
                            "created_at": c.created_at.isoformat() if c.created_at else None,
                            "updated_at": c.updated_at.isoformat() if c.updated_at else None
                        }
                        for c in customers
                    ],
                    "total": total,
                    "page": page,
                    "per_page": per_page
                }
                
        except Exception as e:
            logger.exception(f"获取客户列表失败：{e}")
            return {
                "success": False,
                "message": f"获取失败：{str(e)}",
                "data": [],
                "total": 0
            }
    
    def get_by_id(self, customer_id: int) -> Dict[str, Any]:
        """根据 ID 获取单个客户"""
        try:
            with get_db() as db:
                customer = db.query(Customer).filter(Customer.id == customer_id).first()
                
                if not customer:
                    return {
                        "success": False,
                        "message": "客户不存在",
                        "data": None
                    }
                
                return {
                    "success": True,
                    "data": {
                        "id": customer.id,
                        "customer_name": customer.customer_name,
                        "contact_person": customer.contact_person,
                        "contact_phone": customer.contact_phone,
                        "contact_address": customer.contact_address,
                        "created_at": customer.created_at.isoformat() if customer.created_at else None,
                        "updated_at": customer.updated_at.isoformat() if customer.updated_at else None
                    }
                }
                
        except Exception as e:
            logger.exception(f"获取客户失败：{e}")
            return {
                "success": False,
                "message": f"获取失败：{str(e)}",
                "data": None
            }
    
    def create(self, customer_data: dict) -> Dict[str, Any]:
        """创建单个客户"""
        try:
            with get_db() as db:
                # 检查客户名称是否已存在
                existing = db.query(Customer).filter(
                    Customer.customer_name == customer_data.get("customer_name")
                ).first()
                
                if existing:
                    return {
                        "success": False,
                        "message": "客户名称已存在",
                        "data": None
                    }
                
                # 创建新客户
                customer = Customer(
                    customer_name=customer_data.get("customer_name"),
                    contact_person=customer_data.get("contact_person"),
                    contact_phone=customer_data.get("contact_phone"),
                    contact_address=customer_data.get("contact_address")
                )
                
                db.add(customer)
                db.commit()
                db.refresh(customer)
                
                return {
                    "success": True,
                    "message": "客户创建成功",
                    "data": {
                        "id": customer.id,
                        "customer_name": customer.customer_name,
                        "contact_person": customer.contact_person,
                        "contact_phone": customer.contact_phone,
                        "contact_address": customer.contact_address,
                        "created_at": customer.created_at.isoformat() if customer.created_at else None,
                        "updated_at": customer.updated_at.isoformat() if customer.updated_at else None
                    }
                }
                
        except Exception as e:
            logger.exception(f"创建客户失败：{e}")
            db.rollback()
            return {
                "success": False,
                "message": f"创建失败：{str(e)}",
                "data": None
            }
    
    def update(self, customer_id: int, customer_data: dict) -> Dict[str, Any]:
        """更新单个客户"""
        try:
            with get_db() as db:
                customer = db.query(Customer).filter(Customer.id == customer_id).first()
                
                if not customer:
                    return {
                        "success": False,
                        "message": "客户不存在",
                        "data": None
                    }
                
                # 检查客户名称是否与其他客户重复
                if "customer_name" in customer_data:
                    existing = db.query(Customer).filter(
                        Customer.customer_name == customer_data.get("customer_name"),
                        Customer.id != customer_id
                    ).first()
                    
                    if existing:
                        return {
                            "success": False,
                            "message": "客户名称已存在",
                            "data": None
                        }
                
                # 更新字段
                if "customer_name" in customer_data:
                    customer.customer_name = customer_data["customer_name"]
                if "contact_person" in customer_data:
                    customer.contact_person = customer_data["contact_person"]
                if "contact_phone" in customer_data:
                    customer.contact_phone = customer_data["contact_phone"]
                if "contact_address" in customer_data:
                    customer.contact_address = customer_data["contact_address"]
                
                db.commit()
                db.refresh(customer)
                
                return {
                    "success": True,
                    "message": "客户更新成功",
                    "data": {
                        "id": customer.id,
                        "customer_name": customer.customer_name,
                        "contact_person": customer.contact_person,
                        "contact_phone": customer.contact_phone,
                        "contact_address": customer.contact_address,
                        "created_at": customer.created_at.isoformat() if customer.created_at else None,
                        "updated_at": customer.updated_at.isoformat() if customer.updated_at else None
                    }
                }
                
        except Exception as e:
            logger.exception(f"更新客户失败：{e}")
            db.rollback()
            return {
                "success": False,
                "message": f"更新失败：{str(e)}",
                "data": None
            }
    
    def delete(self, customer_id: int) -> Dict[str, Any]:
        """删除单个客户"""
        try:
            with get_db() as db:
                customer = db.query(Customer).filter(Customer.id == customer_id).first()
                
                if not customer:
                    return {
                        "success": False,
                        "message": "客户不存在",
                        "deleted_count": 0
                    }
                
                db.delete(customer)
                db.commit()
                
                return {
                    "success": True,
                    "message": "客户删除成功",
                    "deleted_count": 1
                }
                
        except Exception as e:
            logger.exception(f"删除客户失败：{e}")
            db.rollback()
            return {
                "success": False,
                "message": f"删除失败：{str(e)}",
                "deleted_count": 0
            }
    
    def batch_delete(self, ids: list) -> Dict[str, Any]:
        """批量删除客户"""
        try:
            with get_db() as db:
                # 查询要删除的客户
                customers = db.query(Customer).filter(Customer.id.in_(ids)).all()
                
                if not customers:
                    return {
                        "success": False,
                        "message": "未找到要删除的客户",
                        "deleted_count": 0
                    }
                
                # 删除客户
                for customer in customers:
                    db.delete(customer)
                
                db.commit()
                
                return {
                    "success": True,
                    "message": f"成功删除 {len(customers)} 条记录",
                    "deleted_count": len(customers)
                }
                
        except Exception as e:
            logger.exception(f"批量删除失败：{e}")
            db.rollback()
            return {
                "success": False,
                "message": f"删除失败：{str(e)}",
                "deleted_count": 0
            }
