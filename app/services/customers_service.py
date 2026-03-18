# -*- coding: utf-8 -*-
"""
客户管理服务
"""
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.customer import Customer

logger = logging.getLogger(__name__)


class CustomerService:
    """客户服务类"""
    
    def get_all_customers(
        self,
        keyword: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        获取所有客户
        
        Args:
            keyword: 搜索关键词
            page: 页码
            per_page: 每页数量
            
        Returns:
            客户列表和总数
        """
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
    
    def create_customer(
        self,
        customer_name: str,
        contact_person: Optional[str] = None,
        contact_phone: Optional[str] = None,
        contact_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建客户"""
        try:
            with get_db() as db:
                customer = Customer(
                    customer_name=customer_name,
                    contact_person=contact_person,
                    contact_phone=contact_phone,
                    contact_address=contact_address
                )
                db.add(customer)
                db.commit()
                db.refresh(customer)
                
                return {
                    "success": True,
                    "message": "客户创建成功",
                    "data": {
                        "id": customer.id,
                        "customer_name": customer.customer_name
                    }
                }
                
        except Exception as e:
            logger.exception(f"创建客户失败：{e}")
            return {
                "success": False,
                "message": f"创建失败：{str(e)}"
            }
    
    def delete_customer(self, customer_id: int) -> Dict[str, Any]:
        """删除客户"""
        try:
            with get_db() as db:
                customer = db.query(Customer).filter(Customer.id == customer_id).first()
                if not customer:
                    return {
                        "success": False,
                        "message": "客户不存在"
                    }
                
                db.delete(customer)
                db.commit()
                
                return {
                    "success": True,
                    "message": "客户删除成功"
                }
                
        except Exception as e:
            logger.exception(f"删除客户失败：{e}")
            return {
                "success": False,
                "message": f"删除失败：{str(e)}"
            }
