# -*- coding: utf-8 -*-
"""
原材料管理服务
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.material import Material

logger = logging.getLogger(__name__)


class MaterialsService:
    """原材料管理服务类"""
    
    def get_all_materials(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        获取所有原材料
        
        Args:
            search: 搜索关键词
            category: 分类筛选
            page: 页码
            per_page: 每页数量
            
        Returns:
            原材料列表和总数
        """
        try:
            with get_db() as db:
                query = db.query(Material).filter(Material.is_active == 1)
                
                if search:
                    pattern = f"%{search}%"
                    query = query.filter(
                        (Material.name.like(pattern)) |
                        (Material.material_code.like(pattern)) |
                        (Material.supplier.like(pattern))
                    )
                
                if category:
                    query = query.filter(Material.category == category)
                
                total = query.count()
                materials = query.order_by(Material.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
                
                return {
                    "success": True,
                    "data": [
                        self._material_to_dict(m) for m in materials
                    ],
                    "total": total,
                    "page": page,
                    "per_page": per_page
                }
                
        except Exception as e:
            logger.exception(f"获取原材料列表失败：{e}")
            return {
                "success": False,
                "message": f"获取失败：{str(e)}",
                "data": [],
                "total": 0
            }
    
    def get_material_by_id(self, material_id: int) -> Dict[str, Any]:
        """
        根据 ID 获取原材料
        
        Args:
            material_id: 原材料 ID
            
        Returns:
            原材料信息
        """
        try:
            with get_db() as db:
                material = db.query(Material).filter(
                    Material.id == material_id,
                    Material.is_active == 1
                ).first()
                
                if not material:
                    return {
                        "success": False,
                        "message": "原材料不存在"
                    }
                
                return {
                    "success": True,
                    "data": self._material_to_dict(material)
                }
                
        except Exception as e:
            logger.exception(f"获取原材料详情失败：{e}")
            return {
                "success": False,
                "message": f"查询失败：{str(e)}"
            }
    
    def create_material(
        self,
        material_code: str,
        name: str,
        category: Optional[str] = None,
        specification: Optional[str] = None,
        unit: str = "个",
        quantity: float = 0,
        unit_price: float = 0,
        supplier: Optional[str] = None,
        warehouse_location: Optional[str] = None,
        min_stock: float = 0,
        max_stock: float = 0,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建原材料
        
        Args:
            material_code: 原材料编码
            name: 原材料名称
            category: 分类
            specification: 规格型号
            unit: 单位
            quantity: 数量
            unit_price: 单价
            supplier: 供应商
            warehouse_location: 仓库位置
            min_stock: 最低库存
            max_stock: 最高库存
            description: 描述信息
            
        Returns:
            创建结果
        """
        try:
            with get_db() as db:
                existing = db.query(Material).filter(
                    Material.material_code == material_code
                ).first()
                
                if existing:
                    return {
                        "success": False,
                        "message": "原材料编码已存在"
                    }
                
                material = Material(
                    material_code=material_code,
                    name=name,
                    category=category,
                    specification=specification,
                    unit=unit,
                    quantity=quantity,
                    unit_price=unit_price,
                    supplier=supplier,
                    warehouse_location=warehouse_location,
                    min_stock=min_stock,
                    max_stock=max_stock,
                    description=description,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                db.add(material)
                db.commit()
                db.refresh(material)
                
                return {
                    "success": True,
                    "message": "原材料创建成功",
                    "data": self._material_to_dict(material)
                }
                
        except Exception as e:
            logger.exception(f"创建原材料失败：{e}")
            return {
                "success": False,
                "message": f"创建失败：{str(e)}"
            }
    
    def update_material(
        self,
        material_id: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        更新原材料
        
        Args:
            material_id: 原材料 ID
            **kwargs: 要更新的字段
            
        Returns:
            更新结果
        """
        try:
            with get_db() as db:
                material = db.query(Material).filter(
                    Material.id == material_id,
                    Material.is_active == 1
                ).first()
                
                if not material:
                    return {
                        "success": False,
                        "message": "原材料不存在"
                    }
                
                allowed_fields = [
                    'material_code', 'name', 'category', 'specification',
                    'unit', 'quantity', 'unit_price', 'supplier',
                    'warehouse_location', 'min_stock', 'max_stock',
                    'description'
                ]
                
                for field, value in kwargs.items():
                    if field in allowed_fields:
                        setattr(material, field, value)
                
                material.updated_at = datetime.now()
                
                db.commit()
                db.refresh(material)
                
                return {
                    "success": True,
                    "message": "原材料更新成功",
                    "data": self._material_to_dict(material)
                }
                
        except Exception as e:
            logger.exception(f"更新原材料失败：{e}")
            return {
                "success": False,
                "message": f"更新失败：{str(e)}"
            }
    
    def delete_material(self, material_id: int) -> Dict[str, Any]:
        """
        删除原材料（软删除）
        
        Args:
            material_id: 原材料 ID
            
        Returns:
            删除结果
        """
        try:
            with get_db() as db:
                material = db.query(Material).filter(
                    Material.id == material_id,
                    Material.is_active == 1
                ).first()
                
                if not material:
                    return {
                        "success": False,
                        "message": "原材料不存在"
                    }
                
                material.is_active = 0
                material.updated_at = datetime.now()
                db.commit()
                
                return {
                    "success": True,
                    "message": "原材料删除成功"
                }
                
        except Exception as e:
            logger.exception(f"删除原材料失败：{e}")
            return {
                "success": False,
                "message": f"删除失败：{str(e)}"
            }
    
    def batch_delete_materials(self, ids: List[int]) -> Dict[str, Any]:
        """
        批量删除原材料（软删除）
        
        Args:
            ids: 原材料 ID 列表
            
        Returns:
            删除结果
        """
        try:
            with get_db() as db:
                materials = db.query(Material).filter(
                    Material.id.in_(ids),
                    Material.is_active == 1
                ).all()
                
                if not materials:
                    return {
                        "success": False,
                        "message": "未找到要删除的原材料"
                    }
                
                for material in materials:
                    material.is_active = 0
                    material.updated_at = datetime.now()
                
                db.commit()
                
                return {
                    "success": True,
                    "message": f"已删除 {len(materials)} 条记录",
                    "deleted_count": len(materials)
                }
                
        except Exception as e:
            logger.exception(f"批量删除原材料失败：{e}")
            return {
                "success": False,
                "message": f"批量删除失败：{str(e)}"
            }
    
    def get_low_stock_materials(
        self,
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        获取低库存原材料
        
        Args:
            threshold: 库存阈值，如果为 None 则使用 min_stock 判断
            
        Returns:
            低库存原材料列表
        """
        try:
            with get_db() as db:
                query = db.query(Material).filter(
                    Material.is_active == 1
                )
                
                if threshold is not None:
                    query = query.filter(Material.quantity <= threshold)
                else:
                    query = query.filter(Material.quantity <= Material.min_stock)
                
                materials = query.order_by(Material.quantity.asc()).all()
                
                return {
                    "success": True,
                    "data": [
                        self._material_to_dict(m) for m in materials
                    ],
                    "count": len(materials)
                }
                
        except Exception as e:
            logger.exception(f"获取低库存原材料失败：{e}")
            return {
                "success": False,
                "message": f"查询失败：{str(e)}",
                "data": [],
                "count": 0
            }
    
    def _material_to_dict(self, material: Material) -> Dict[str, Any]:
        """将 Material 对象转换为字典"""
        return {
            "id": material.id,
            "material_code": material.material_code,
            "name": material.name,
            "category": material.category,
            "specification": material.specification,
            "unit": material.unit,
            "quantity": material.quantity,
            "unit_price": material.unit_price,
            "supplier": material.supplier,
            "warehouse_location": material.warehouse_location,
            "min_stock": material.min_stock,
            "max_stock": material.max_stock,
            "description": material.description,
            "is_active": material.is_active,
            "created_at": material.created_at.isoformat() if material.created_at else None,
            "updated_at": material.updated_at.isoformat() if material.updated_at else None
        }
