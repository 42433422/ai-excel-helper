"""
产品库服务模块

提供产品 CRUD 等业务逻辑。
"""

from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.db.models import Product

logger = logging.getLogger(__name__)


class ProductsService:
    """产品库服务类"""
    
    def __init__(self):
        """初始化产品库服务"""
        pass
    
    def _product_to_dict(self, product: Product) -> Dict[str, Any]:
        """将 Product 模型转换为字典，保持向后兼容性"""
        result = {}
        for column in inspect(Product).columns:
            value = getattr(product, column.name)
            result[column.name] = value
        
        # 字段映射，保持向后兼容
        if "name" in result:
            result["product_name"] = result["name"]
        
        return result
    
    def get_products(
        self,
        unit_name: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        获取产品列表
        
        Args:
            unit_name: 单位名称（可选）
            keyword: 搜索关键词（可选）
            page: 页码（默认 1）
            per_page: 每页数量（默认 20）
            
        Returns:
            结果字典：
                - success: 是否成功
                - data: 产品列表
                - total: 总数
                - page: 当前页
                - per_page: 每页数量
        """
        try:
            logger.info(f"查询产品列表：unit_name={unit_name}, keyword={keyword}")
            
            with get_db() as db:
                # 检查 products 表是否存在
                inspector = inspect(db.bind)
                if "products" not in inspector.get_table_names():
                    return {
                        "success": True,
                        "data": [],
                        "total": 0,
                        "page": page,
                        "per_page": per_page
                    }
                
                # 构建查询
                query = db.query(Product)
                
                # 根据单位名称过滤
                if unit_name:
                    query = query.filter(Product.unit == unit_name)
                
                if keyword:
                    query = query.filter(
                        (Product.name.like(f"%{keyword}%")) | 
                        (Product.description.like(f"%{keyword}%"))
                    )
                
                # 查询总数
                total = query.count()
                
                # 查询当前页数据
                offset = (page - 1) * per_page
                products = query.order_by(
                    Product.id.desc()
                ).limit(per_page).offset(offset).all()
                
                # 转换为字典列表
                rows = [self._product_to_dict(product) for product in products]
            
            return {
                "success": True,
                "data": rows,
                "total": int(total),
                "page": page,
                "per_page": per_page
            }
            
        except Exception as e:
            logger.exception(f"查询产品列表失败：{e}")
            return {
                "success": False,
                "message": f"查询失败：{str(e)}",
                "data": [],
                "total": 0,
                "page": page,
                "per_page": per_page
            }
    
    def get_product(self, product_id: int) -> Dict[str, Any]:
        """
        获取单个产品
        
        Args:
            product_id: 产品 ID
            
        Returns:
            结果字典
        """
        try:
            with get_db() as db:
                product = db.query(Product).filter(Product.id == product_id).first()
                
                if product:
                    return {
                        "success": True,
                        "data": self._product_to_dict(product)
                    }
                else:
                    return {
                        "success": False,
                        "message": "产品不存在",
                        "data": None
                    }
            
        except Exception as e:
            logger.exception(f"获取产品失败：{e}")
            return {
                "success": False,
                "message": f"查询失败：{str(e)}",
                "data": None
            }
    
    def create_product(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建产品
        
        Args:
            data: 产品数据，包含：
                - unit_name: 单位名称
                - product_name: 产品名称
                - price: 价格
                - description: 描述（可选）
                
        Returns:
            结果字典
        """
        try:
            product_name = data.get("product_name") or data.get("name")
            price = data.get("price", 0.0)
            description = data.get("description", "")
            
            if not product_name:
                return {
                    "success": False,
                    "message": "产品名称不能为空"
                }
            
            with get_db() as db:
                product = Product(
                    name=product_name,
                    price=price,
                    description=description,
                    model_number=data.get("model_number"),
                    specification=data.get("specification"),
                    quantity=data.get("quantity"),
                    category=data.get("category"),
                    brand=data.get("brand"),
                    unit=data.get("unit", "个"),
                    is_active=data.get("is_active", 1),
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                db.add(product)
                db.commit()
                db.refresh(product)
                product_id = product.id
            
            return {
                "success": True,
                "message": "产品创建成功",
                "product_id": product_id
            }
            
        except Exception as e:
            logger.exception(f"创建产品失败：{e}")
            return {
                "success": False,
                "message": f"创建失败：{str(e)}"
            }
    
    def update_product(self, product_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新产品
        
        Args:
            product_id: 产品 ID
            data: 产品数据
            
        Returns:
            结果字典
        """
        try:
            with get_db() as db:
                product = db.query(Product).filter(Product.id == product_id).first()
                
                if not product:
                    return {
                        "success": False,
                        "message": "产品不存在"
                    }
                
                # 更新字段
                has_update = False
                if "product_name" in data or "name" in data:
                    product.name = data.get("product_name") or data.get("name")
                    has_update = True
                if "price" in data:
                    product.price = data["price"]
                    has_update = True
                if "description" in data:
                    product.description = data["description"]
                    has_update = True
                if "model_number" in data:
                    product.model_number = data["model_number"]
                    has_update = True
                if "specification" in data:
                    product.specification = data["specification"]
                    has_update = True
                if "quantity" in data:
                    product.quantity = data["quantity"]
                    has_update = True
                if "category" in data:
                    product.category = data["category"]
                    has_update = True
                if "brand" in data:
                    product.brand = data["brand"]
                    has_update = True
                if "unit" in data:
                    product.unit = data["unit"]
                    has_update = True
                if "is_active" in data:
                    product.is_active = data["is_active"]
                    has_update = True
                
                if not has_update:
                    return {
                        "success": False,
                        "message": "没有要更新的字段"
                    }
                
                product.updated_at = datetime.now()
                db.commit()
            
            return {
                "success": True,
                "message": "产品更新成功"
            }
            
        except Exception as e:
            logger.exception(f"更新产品失败：{e}")
            return {
                "success": False,
                "message": f"更新失败：{str(e)}"
            }
    
    def delete_product(self, product_id: int) -> Dict[str, Any]:
        """
        删除产品
        
        Args:
            product_id: 产品 ID
            
        Returns:
            结果字典
        """
        try:
            with get_db() as db:
                product = db.query(Product).filter(Product.id == product_id).first()
                
                if not product:
                    return {
                        "success": False,
                        "message": "产品不存在"
                    }
                
                db.delete(product)
                db.commit()
            
            return {
                "success": True,
                "message": "产品删除成功"
            }
            
        except Exception as e:
            logger.exception(f"删除产品失败：{e}")
            return {
                "success": False,
                "message": f"删除失败：{str(e)}"
            }
    
    def batch_add_products(self, products_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量添加产品
        
        Args:
            products_data: 产品数据列表，每个产品包含：
                - unit_name: 单位名称
                - product_name: 产品名称
                - price: 价格
                - description: 描述（可选）
                - 其他可选字段
                
        Returns:
            结果字典
        """
        try:
            if not products_data:
                return {
                    "success": False,
                    "message": "产品列表不能为空"
                }
            
            success_count = 0
            failed_products = []
            product_ids = []
            
            with get_db() as db:
                for index, data in enumerate(products_data):
                    try:
                        product_name = data.get("product_name") or data.get("name")
                        price = data.get("price", 0.0)
                        description = data.get("description", "")
                        
                        if not product_name:
                            failed_products.append({
                                "index": index,
                                "reason": "产品名称不能为空"
                            })
                            continue
                        
                        product = Product(
                            name=product_name,
                            price=price,
                            description=description,
                            model_number=data.get("model_number"),
                            specification=data.get("specification"),
                            quantity=data.get("quantity"),
                            category=data.get("category"),
                            brand=data.get("brand"),
                            unit=data.get("unit", "个"),
                            is_active=data.get("is_active", 1),
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        
                        db.add(product)
                        db.flush()
                        product_ids.append(product.id)
                        success_count += 1
                        
                    except Exception as e:
                        logger.error(f"添加第 {index + 1} 个产品失败：{e}")
                        failed_products.append({
                            "index": index,
                            "reason": str(e)
                        })
                
                db.commit()
            
            result = {
                "success": True,
                "message": f"成功添加 {success_count} 个产品",
                "success_count": success_count,
                "failed_count": len(failed_products),
                "product_ids": product_ids
            }
            
            if failed_products:
                result["failed_products"] = failed_products
            
            return result
            
        except Exception as e:
            logger.exception(f"批量添加产品失败：{e}")
            return {
                "success": False,
                "message": f"批量添加失败：{str(e)}"
            }
    
    def batch_delete_products(self, product_ids: List[int]) -> Dict[str, Any]:
        """
        批量删除产品
        
        Args:
            product_ids: 产品 ID 列表
            
        Returns:
            结果字典
        """
        try:
            if not product_ids:
                return {
                    "success": False,
                    "message": "产品 ID 列表不能为空"
                }
            
            with get_db() as db:
                # 查询要删除的产品
                products = db.query(Product).filter(Product.id.in_(product_ids)).all()
                
                if not products:
                    return {
                        "success": False,
                        "message": "未找到要删除的产品"
                    }
                
                # 删除产品
                for product in products:
                    db.delete(product)
                
                db.commit()
                
                return {
                    "success": True,
                    "message": f"成功删除 {len(products)} 个产品",
                    "deleted_count": len(products)
                }
            
        except Exception as e:
            logger.exception(f"批量删除产品失败：{e}")
            return {
                "success": False,
                "message": f"批量删除失败：{str(e)}"
            }
    
    def _product_exists(self, product_id: int) -> bool:
        """检查产品是否存在"""
        try:
            with get_db() as db:
                product = db.query(Product).filter(Product.id == product_id).first()
                return product is not None
            
        except Exception as e:
            logger.error(f"检查产品存在失败：{e}")
            return False
    
    def get_product_names(self, keyword: Optional[str] = None) -> Dict[str, Any]:
        """
        获取产品名称列表
        
        Args:
            keyword: 搜索关键词（可选）
            
        Returns:
            结果字典：
                - success: 是否成功
                - data: 产品名称列表
                - count: 数量
        """
        try:
            with get_db() as db:
                inspector = inspect(db.bind)
                if "products" not in inspector.get_table_names():
                    return {
                        "success": True,
                        "data": [],
                        "count": 0
                    }
                
                query = db.query(Product.name)
                
                if keyword:
                    query = query.filter(Product.name.like(f"%{keyword}%"))
                
                query = query.distinct()
                names = [row[0] for row in query.all() if row[0]]
                
                return {
                    "success": True,
                    "data": names,
                    "count": len(names)
                }
            
        except Exception as e:
            logger.exception(f"获取产品名称列表失败：{e}")
            return {
                "success": False,
                "message": f"查询失败：{str(e)}",
                "data": [],
                "count": 0
            }
    
    def export_to_excel(self, unit_name: Optional[str] = None, keyword: Optional[str] = None) -> Dict[str, Any]:
        """
        导出产品到 Excel 文件
        
        Args:
            unit_name: 单位名称（可选）
            keyword: 搜索关键词（可选）
            
        Returns:
            结果字典：
                - success: 是否成功
                - file_path: 文件路径
                - filename: 文件名
        """
        try:
            import os
            from datetime import datetime
            from openpyxl import Workbook
            
            logger.info(f"导出产品：unit_name={unit_name}, keyword={keyword}")
            
            with get_db() as db:
                inspector = inspect(db.bind)
                if "products" not in inspector.get_table_names():
                    return {
                        "success": False,
                        "message": "产品表不存在",
                        "file_path": None,
                        "filename": None
                    }
                
                query = db.query(Product)
                
                if unit_name:
                    query = query.filter(Product.unit == unit_name)
                
                if keyword:
                    query = query.filter(
                        (Product.name.like(f"%{keyword}%")) | 
                        (Product.description.like(f"%{keyword}%"))
                    )
                
                products = query.order_by(Product.id.desc()).all()
                
                wb = Workbook()
                ws = wb.active
                ws.title = "产品列表"
                
                headers = ["ID", "产品编码", "产品名称", "规格型号", "价格", "数量", "单位", "类别", "品牌", "描述", "状态", "创建时间", "更新时间"]
                ws.append(headers)
                
                for product in products:
                    ws.append([
                        product.id,
                        product.model_number or "",
                        product.name or "",
                        product.specification or "",
                        product.price or 0.0,
                        product.quantity or 0,
                        product.unit or "个",
                        product.category or "",
                        product.brand or "",
                        product.description or "",
                        "启用" if product.is_active else "停用",
                        product.created_at.strftime("%Y-%m-%d %H:%M:%S") if product.created_at else "",
                        product.updated_at.strftime("%Y-%m-%d %H:%M:%S") if product.updated_at else ""
                    ])
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"products_{timestamp}.xlsx"
                
                from app.utils.path_utils import get_data_dir
                export_dir = os.path.join(get_data_dir(), "exports")
                os.makedirs(export_dir, exist_ok=True)
                file_path = os.path.join(export_dir, filename)
                
                wb.save(file_path)
                
                logger.info(f"产品导出完成：{file_path}, 共 {len(products)} 条记录")
                
                return {
                    "success": True,
                    "file_path": str(file_path),
                    "filename": filename,
                    "count": len(products)
                }
            
        except Exception as e:
            logger.exception(f"导出产品失败：{e}")
            return {
                "success": False,
                "message": f"导出失败：{str(e)}",
                "file_path": None,
                "filename": None
            }
