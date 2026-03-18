"""
发货单服务模块

提供发货单生成、查询、下载等业务逻辑。
"""

import os
import sys
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.db.models import PurchaseUnit, ShipmentRecord

logger = logging.getLogger(__name__)


class ShipmentService:
    """发货单服务类"""
    
    def __init__(self):
        """初始化发货单服务"""
        self.db_path = self._get_db_path()
        self.template_dir = self._get_template_dir()
        self.output_dir = self._get_output_dir()
    
    def _get_db_path(self) -> str:
        """获取数据库路径"""
        # 使用 XCAGI/db.py 中的函数
        from db import get_db_path
        return get_db_path()
    
    def _get_template_dir(self) -> str:
        """获取模板目录"""
        # 使用配置或路径工具函数
        from app.config import Config
        from app.utils.path_utils import get_base_dir
        return os.path.join(get_base_dir(), 'AI 助手', 'uploads')
    
    def _get_output_dir(self) -> str:
        """获取输出目录"""
        # 使用配置或路径工具函数
        from app.utils.path_utils import get_app_data_dir
        return os.path.join(get_app_data_dir(), 'shipment_outputs')
    
    def _load_products_from_db(self, unit_name: str = None) -> List[Dict[str, Any]]:
        """从数据库加载产品（优先从客户专属数据库加载）"""
        products = []
        
        # 1. 先尝试从客户专属数据库加载
        if unit_name:
            unit_db_path = self._get_unit_db_path(unit_name)
            if unit_db_path and os.path.exists(unit_db_path):
                try:
                    conn = sqlite3.connect(unit_db_path)
                    cursor = conn.cursor()
                    cursor.execute('SELECT id, model_number, name, price, specification, brand, unit FROM products')
                    rows = cursor.fetchall()
                    conn.close()
                    
                    if rows:
                        for r in rows:
                            products.append({
                                'id': r[0],
                                'model_number': r[1] or '',
                                'name': r[2] or '',
                                'price': float(r[3]) if r[3] else 0.0,
                                'specification': r[4] or '',
                                'brand': r[5] or '',
                                'unit': r[6] or '',
                            })
                        logger.info(f"从客户数据库加载产品: {unit_name}, 数量: {len(products)}")
                        return products
                except Exception as e:
                    logger.warning(f"从客户数据库加载产品失败: {e}")
        
        # 2. 回退到主 products.db
        try:
            from app.db.session import get_db
            from app.db.models import Product
            
            with get_db() as db:
                db_products = db.query(Product).all()
                for p in db_products:
                    products.append({
                        'id': p.id,
                        'name': p.name or '',
                        'model_number': p.model_number or '',
                        'price': float(p.price) if p.price else 0.0,
                        'specification': p.specification or '',
                        'brand': p.brand or '',
                        'unit': p.unit or '',
                    })
                logger.info(f"从主数据库加载产品: {len(products)} 个")
        except Exception as e:
            logger.warning(f"加载产品失败: {e}")
        
        return products
    
    def _get_unit_db_path(self, unit_name: str) -> str:
        """获取客户专属数据库路径"""
        try:
            # AI助手的 unit_databases 目录
            ai_helper_base = r"E:\FHD\AI助手"
            unit_db_dir = os.path.join(ai_helper_base, "unit_databases")
            db_path = os.path.join(unit_db_dir, f"{unit_name}.db")
            if os.path.exists(db_path):
                logger.info(f"找到客户数据库: {db_path}")
                return db_path
        except Exception as e:
            logger.warning(f"查找客户数据库失败: {e}")
        return None
    
    def _match_product(self, name: str, model_number: str, db_products: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """从数据库产品列表中匹配产品"""
        if not name and not model_number:
            return None
        
        name = (name or '').strip().lower()
        model_number = (model_number or '').strip().lower()
        
        # 1. 优先按型号精确匹配
        if model_number:
            for p in db_products:
                if p.get('model_number', '').lower() == model_number:
                    logger.info(f"型号精确匹配: {model_number} -> {p['name']}")
                    return p
        
        # 2. 按产品名称精确匹配
        if name:
            for p in db_products:
                if p.get('name', '').lower() == name:
                    logger.info(f"名称精确匹配: {name} -> {p['name']}")
                    return p
        
        # 3. 按型号模糊匹配
        if model_number:
            for p in db_products:
                if p.get('model_number', '') and model_number in p.get('model_number', '').lower():
                    logger.info(f"型号模糊匹配: {model_number} -> {p['name']} ({p.get('model_number')})")
                    return p
        
        # 4. 按名称模糊匹配
        if name:
            for p in db_products:
                p_name = p.get('name', '').lower()
                if name in p_name or p_name in name:
                    logger.info(f"名称模糊匹配: {name} -> {p['name']}")
                    return p
        
        logger.warning(f"未找到匹配产品: name={name}, model_number={model_number}")
        return None
    
    def generate_shipment_document(
        self,
        unit_name: str,
        products: List[Dict[str, Any]],
        date: Optional[str] = None,
        template_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        生成发货单文档（同步），复用原项目的 ShipmentDocumentGenerator 模板填充逻辑。
        """
        try:
            logger.info("开始生成发货单：%s，产品数量：%d", unit_name, len(products))

            # 1. 获取购买单位信息
            purchase_unit = self._get_purchase_unit_info(unit_name)
            if not purchase_unit:
                return {
                    "success": False,
                    "message": f"未找到购买单位：{unit_name}",
                    "doc_name": None,
                    "file_path": None,
                }

            # 2. 导入旧版发货单生成器与购买单位结构
            # 从 XCAGI/app/services/ 向上三级到 E:\FHD
            current_dir = os.path.dirname(os.path.abspath(__file__))  # .../XCAGI/app/services
            app_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))  # E:\FHD
            project_root = app_dir
            
            # 尝试三个可能的目录名（按照最可能的顺序）
            possible_dirs = [
                os.path.join(project_root, "AI助手"),  # 无空格版本（最常见）
                os.path.join(project_root, "AI 助手"),  # 有空格版本
                os.path.join(project_root, "AI助手2")  # 备用版本
            ]
            
            legacy_dir = None
            for dir_path in possible_dirs:
                if os.path.isdir(dir_path) and os.path.exists(os.path.join(dir_path, "shipment_document.py")):
                    legacy_dir = dir_path
                    logger.info(f"找到发货单生成器：{dir_path}")
                    break
            
            if not legacy_dir:
                raise ImportError(f"未找到包含 shipment_document.py 的 AI 助手目录。可能的目录：{possible_dirs}")
            
            # 尝试导入旧版发货单生成器
            ShipmentDocumentGenerator = None
            PurchaseUnitInfo = None
            import_error_msg = None
            
            try:
                # 方法 1: 直接导入（如果路径已添加到 sys.path）
                if os.path.isdir(legacy_dir) and legacy_dir not in sys.path:
                    sys.path.insert(0, legacy_dir)
                
                try:
                    from shipment_document import ShipmentDocumentGenerator, PurchaseUnitInfo
                    logger.info("成功从 AI 助手目录导入发货单生成器")
                except ImportError as ie:
                    # 方法 2: 使用 importlib 动态导入
                    logger.warning("直接导入失败，尝试使用 importlib: %s", ie)
                    import importlib.util
                    spec_path = os.path.join(legacy_dir, "shipment_document.py")
                    if os.path.exists(spec_path):
                        spec = importlib.util.spec_from_file_location("shipment_document", spec_path)
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            ShipmentDocumentGenerator = getattr(module, "ShipmentDocumentGenerator", None)
                            PurchaseUnitInfo = getattr(module, "PurchaseUnitInfo", None)
                            logger.info("成功使用 importlib 导入发货单生成器")
                    else:
                        import_error_msg = f"文件不存在：{spec_path}"
                
                if not ShipmentDocumentGenerator or not PurchaseUnitInfo:
                    raise ImportError(import_error_msg or "无法加载 ShipmentDocumentGenerator 或 PurchaseUnitInfo")
                    
            except Exception as import_err:
                logger.exception("导入旧版发货单生成器失败：%s", import_err)
                return {
                    "success": False,
                    "message": f"加载旧版发货单生成器失败：{str(import_err)}，请检查 AI 助手/shipment_document.py 是否存在",
                    "doc_name": None,
                    "file_path": None,
                }

            purchase_unit_info = PurchaseUnitInfo(
                name=purchase_unit.get("unit_name", unit_name),
                contact_person=purchase_unit.get("contact_person", ""),
                contact_phone=purchase_unit.get("contact_phone", ""),
                address=purchase_unit.get("address", ""),
                id=purchase_unit.get("id"),
            )

            # 3. 准备产品数据 -> 兼容 shipment_document._prepare_products 期望的 parsed_data 结构
            parsed_products: List[Dict[str, Any]] = []
            logger.info(f"准备处理产品数据，原始产品数量：{len(products)}")
            logger.info(f"原始产品数据示例：{products[:3] if len(products) > 3 else products}")
            
            # 从客户专属数据库加载产品信息用于匹配
            db_products = self._load_products_from_db(unit_name)
            logger.info(f"从数据库加载了 {len(db_products)} 个产品")
            
            for p in products:
                name = p.get("name") or p.get("product_name", "")
                model_number = p.get("model_number", "") or p.get("型号", "")
                quantity_tins = p.get("quantity_tins")
                if quantity_tins is None:
                    quantity_tins = p.get("quantity", 0)
                tin_spec = p.get("tin_spec") or p.get("spec") or 10.0
                
                # 从数据库匹配产品信息（即使 name 为空，也可以通过 model_number 匹配）
                matched_product = self._match_product(name, model_number, db_products)
                if matched_product:
                    logger.info(f"产品匹配成功: name={name}, model={model_number} -> {matched_product['name']}, 单价: {matched_product['price']}")
                    name = matched_product['name']
                    model_number = matched_product.get('model_number', model_number)
                elif not name and not model_number:
                    # 如果没有匹配到产品，且 name 和 model_number 都为空，则跳过
                    logger.warning(f"跳过无效产品（无名称且无型号）: {p}")
                    continue
                
                # 检查最终产品名称是否有效
                if not name:
                    logger.warning(f"跳过无效产品（无名称）: {p}")
                    continue
                
                unit_price = p.get("unit_price")
                if unit_price is None:
                    # 如果没有提供单价，尝试从匹配的产品获取
                    if matched_product and matched_product.get('price'):
                        unit_price = matched_product['price']
                    else:
                        unit_price = p.get("price", 0)
                amount = p.get("amount")
                if amount is None:
                    try:
                        amount = float(unit_price or 0) * float(p.get("quantity_kg") or 0)
                    except Exception:
                        amount = 0
                quantity_kg = p.get("quantity_kg")
                if quantity_kg is None:
                    try:
                        quantity_kg = float(quantity_tins or 0) * float(tin_spec or 0)
                    except Exception:
                        quantity_kg = 0

                parsed_products.append(
                    {
                        "model_number": model_number,
                        "name": name,
                        "quantity_kg": quantity_kg,
                        "quantity_tins": quantity_tins or 0,
                        "tin_spec": tin_spec or 10.0,
                        "unit_price": unit_price or 0,
                        "amount": amount or 0,
                    }
                )

            logger.info(f"处理后的有效产品数量：{len(parsed_products)}")
            
            if not parsed_products:
                return {
                    "success": False,
                    "message": "产品列表为空或无有效产品名称",
                    "doc_name": None,
                    "file_path": None,
                }

            parsed_data: Dict[str, Any] = {
                "purchase_unit": unit_name,
                "products": parsed_products,
            }

            # 4. 调用旧版 ShipmentDocumentGenerator，按原有模板填充并导出
            generator = ShipmentDocumentGenerator(db_path=self.db_path)
            doc = generator.generate_document(
                order_text="",
                parsed_data=parsed_data,
                purchase_unit=purchase_unit_info,
                template_name=template_name,
            )

            if hasattr(doc, "to_dict"):
                doc_info = doc.to_dict()
                file_path = doc_info.get("filepath")
                filename = doc_info.get("filename") or (os.path.basename(file_path) if file_path else "")
                order_number = doc_info.get("order_number")
                total_amount = doc_info.get("total_amount")
                total_quantity = doc_info.get("total_quantity")
            else:
                # 兼容性处理
                file_path = getattr(doc, "filepath", None)
                filename = getattr(doc, "filename", os.path.basename(file_path) if file_path else "")
                order_number = getattr(doc, "order_number", None)
                total_amount = getattr(doc, "total_amount", None)
                total_quantity = getattr(doc, "total_quantity", None)

            logger.info("发货单生成成功：%s", file_path)

            return {
                "success": True,
                "message": "发货单生成成功",
                "doc_name": filename,
                "file_path": file_path,
                "order_number": order_number,
                "total_amount": total_amount,
                "total_quantity": total_quantity,
            }

        except Exception as e:
            logger.exception("生成发货单失败：%s", e)
            return {
                "success": False,
                "message": f"生成失败：{str(e)}",
                "doc_name": None,
                "file_path": None,
            }
    
    def query_shipment_orders(
        self,
        unit_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        查询发货单列表
        
        Args:
            unit_name: 单位名称（可选）
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            page: 页码（默认 1）
            per_page: 每页数量（默认 20）
            
        Returns:
            结果字典：
                - success: 是否成功
                - data: 发货单列表
                - total: 总数
                - page: 当前页
                - per_page: 每页数量
        """
        try:
            logger.info("查询发货单：unit_name=%s, start_date=%s, end_date=%s, page=%s, per_page=%s",
                        unit_name, start_date, end_date, page, per_page)

            with get_db() as db:
                # 检查 shipment_records 表是否存在
                inspector = inspect(db.bind)
                if "shipment_records" not in inspector.get_table_names():
                    return {
                        "success": True,
                        "data": [],
                        "total": 0,
                        "page": page,
                        "per_page": per_page,
                    }

                # 构建查询
                query = db.query(ShipmentRecord)

                if unit_name:
                    query = query.filter(ShipmentRecord.purchase_unit == unit_name)

                if start_date:
                    query = query.filter(ShipmentRecord.created_at >= datetime.strptime(start_date, "%Y-%m-%d"))
                
                if end_date:
                    query = query.filter(ShipmentRecord.created_at <= datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59))

                # 查询总数
                total = query.count()

                # 查询当前页数据
                offset = (page - 1) * per_page
                records = query.order_by(
                    ShipmentRecord.created_at.desc(),
                    ShipmentRecord.id.desc()
                ).limit(per_page).offset(offset).all()

                # 转换为字典列表
                rows = []
                for record in records:
                    row_dict = {}
                    for column in inspect(ShipmentRecord).columns:
                        row_dict[column.name] = getattr(record, column.name)
                    rows.append(row_dict)

            return {
                "success": True,
                "data": rows,
                "total": int(total),
                "page": page,
                "per_page": per_page,
            }

        except Exception as e:
            logger.exception("查询发货单失败：%s", e)
            return {
                "success": False,
                "message": f"查询失败：{str(e)}",
                "data": [],
                "total": 0,
                "page": page,
                "per_page": per_page,
            }
    
    def get_orders(self, limit: int = 10) -> Dict[str, Any]:
        """
        获取订单列表（简化版本，用于前端展示）
        
        Args:
            limit: 返回数量限制（默认 10）
            
        Returns:
            结果字典：
                - success: 是否成功
                - data: 订单列表
                - count: 总数
        """
        try:
            logger.info("获取订单列表：limit=%s", limit)
            
            with get_db() as db:
                # 检查表是否存在
                inspector = inspect(db.bind)
                if "shipment_records" not in inspector.get_table_names():
                    return {
                        "success": True,
                        "data": [],
                        "count": 0,
                    }
                
                # 查询最近的订单
                records = db.query(ShipmentRecord).order_by(
                    ShipmentRecord.created_at.desc()
                ).limit(limit).all()
                
                # 转换为字典列表
                rows = []
                for record in records:
                    row_dict = {}
                    for column in inspect(ShipmentRecord).columns:
                        row_dict[column.name] = getattr(record, column.name)
                    rows.append(row_dict)
                
                return {
                    "success": True,
                    "data": rows,
                    "count": len(rows),
                }
                
        except Exception as e:
            logger.exception("获取订单列表失败：%s", e)
            return {
                "success": False,
                "message": f"获取失败：{str(e)}",
                "data": [],
                "count": 0,
            }
    
    def download_shipment_order(self, filename: str) -> Dict[str, Any]:
        """
        下载发货单文件
        
        Args:
            filename: 文件名
            
        Returns:
            结果字典：
                - success: 是否成功
                - file_path: 文件路径
                - message: 响应消息
        """
        try:
            file_path = os.path.join(self.output_dir, filename)
            
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "message": f"文件不存在：{filename}",
                    "file_path": None
                }
            
            return {
                "success": True,
                "file_path": file_path,
                "message": "文件存在"
            }
            
        except Exception as e:
            logger.exception(f"下载发货单失败：{e}")
            return {
                "success": False,
                "message": f"下载失败：{str(e)}",
                "file_path": None
            }
    
    def _get_purchase_unit_info(self, unit_name: str) -> Optional[Dict[str, Any]]:
        """获取购买单位信息（先智能匹配，再精确匹配）"""
        # 先尝试智能匹配
        matched_unit = self._match_purchase_unit(unit_name)
        if matched_unit:
            logger.info(f"购买单位智能匹配成功: {unit_name} -> {matched_unit}")
            unit_name = matched_unit
        
        # 精确匹配
        try:
            with get_db() as db:
                # 尝试多种匹配方式
                unit = db.query(PurchaseUnit).filter(
                    PurchaseUnit.unit_name == unit_name,
                    PurchaseUnit.is_active == 1
                ).first()
                
                if not unit:
                    # 尝试不限制 is_active
                    unit = db.query(PurchaseUnit).filter(
                        PurchaseUnit.unit_name == unit_name
                    ).first()
                
                if unit:
                    result = {}
                    for column in inspect(PurchaseUnit).columns:
                        result[column.name] = getattr(unit, column.name)
                    return result
                return None
                
        except Exception as e:
            logger.error(f"获取购买单位信息失败：{e}")
            return None
    
    def _match_purchase_unit(self, input_unit: str) -> Optional[str]:
        """智能匹配客户单位（支持简称、模糊匹配）"""
        if not input_unit:
            return None
        
        input_unit = input_unit.strip()
        
        try:
            from difflib import get_close_matches
            
            with get_db() as db:
                # 获取所有购买单位
                units = db.query(PurchaseUnit).all()
                unit_names = [u.unit_name for u in units if u.unit_name]
                
                # 1. 精确匹配
                if input_unit in unit_names:
                    logger.info(f"购买单位精确匹配: {input_unit}")
                    return input_unit
                
                # 2. 包含关系：输入是某单位名的一部分
                for name in sorted(unit_names, key=len, reverse=True):
                    if input_unit in name:
                        logger.info(f"购买单位包含匹配: {input_unit} -> {name}")
                        return name
                
                # 3. 模糊匹配
                matches = get_close_matches(input_unit, unit_names, n=1, cutoff=0.5)
                if matches:
                    logger.info(f"购买单位模糊匹配: {input_unit} -> {matches[0]}")
                    return matches[0]
                
        except Exception as e:
            logger.warning(f"购买单位智能匹配失败: {e}")
        
        return None
    
    def _generate_order_number(self) -> str:
        """生成订单编号"""
        return datetime.now().strftime("%Y%m%d%H%M%S")
    
    def mark_as_printed(
        self,
        file_path: str,
        order_id: Optional[int] = None,
        printer_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        标记发货单为已打印
        
        Args:
            file_path: 文件路径
            order_id: 订单 ID（可选）
            printer_name: 打印机名称（可选）
            
        Returns:
            结果字典
        """
        try:
            logger.info(f"标记发货单为已打印：file_path={file_path}, order_id={order_id}")
            
            # 如果提供了 order_id，更新数据库状态
            if order_id:
                with get_db() as db:
                    # 检查 shipment_records 表是否存在
                    inspector = inspect(db.bind)
                    if "shipment_records" in inspector.get_table_names():
                        record = db.query(ShipmentRecord).filter(
                            ShipmentRecord.id == order_id
                        ).first()
                        
                        if record:
                            record.status = 'printed'
                            record.updated_at = datetime.now()
                            record.printed_at = datetime.now()
                            record.printer_name = printer_name
                            db.commit()
            
            # 记录打印日志
            logger.info(f"发货单已标记为打印：{file_path}")
            
            return {
                "success": True,
                "message": "发货单已标记为已打印",
                "printed_at": datetime.now().isoformat(),
                "file_path": file_path
            }
            
        except Exception as e:
            logger.exception(f"标记打印失败：{e}")
            return {
                "success": False,
                "message": f"标记失败：{str(e)}"
            }
    
    def _prepare_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """准备产品数据"""
        prepared = []
        for product in products:
            prepared.append({
                "product_name": product.get("product_name", ""),
                "quantity": product.get("quantity", 0),
                "price": product.get("price", 0),
                "amount": product.get("amount", product.get("quantity", 0) * product.get("price", 0)),
                "unit": product.get("unit", "")
            })
        return prepared
    
    def get_purchase_units(self) -> List[str]:
        """
        获取所有购买单位列表
        
        Returns:
            购买单位名称列表
        """
        try:
            with get_db() as db:
                inspector = inspect(db.bind)
                if "purchase_units" not in inspector.get_table_names():
                    return []
                
                units = db.query(PurchaseUnit.unit_name).filter(
                    PurchaseUnit.is_active == 1
                ).distinct().all()
                
                return [unit[0] for unit in units if unit[0]]
                
        except Exception as e:
            logger.error(f"获取购买单位列表失败：{e}")
            return []
    
    def search_orders(self, query: str) -> List[Dict[str, Any]]:
        """
        搜索订单
        
        Args:
            query: 搜索关键词
            
        Returns:
            订单列表
        """
        try:
            with get_db() as db:
                inspector = inspect(db.bind)
                if "shipment_records" not in inspector.get_table_names():
                    return []
                
                records = db.query(ShipmentRecord).filter(
                    (ShipmentRecord.purchase_unit.like(f"%{query}%")) |
                    (ShipmentRecord.product_name.like(f"%{query}%")) |
                    (ShipmentRecord.model_number.like(f"%{query}%"))
                ).order_by(
                    ShipmentRecord.created_at.desc()
                ).limit(50).all()
                
                rows = []
                for record in records:
                    row_dict = {}
                    for column in inspect(ShipmentRecord).columns:
                        row_dict[column.name] = getattr(record, column.name)
                    rows.append(row_dict)
                
                return rows
                
        except Exception as e:
            logger.error(f"搜索订单失败：{e}")
            return []
    
    def get_order(self, order_number: str) -> Optional[Dict[str, Any]]:
        """
        获取订单详情
        
        Args:
            order_number: 订单编号
            
        Returns:
            订单详情字典，不存在则返回 None
        """
        try:
            with get_db() as db:
                inspector = inspect(db.bind)
                if "shipment_records" not in inspector.get_table_names():
                    return None
                
                record = db.query(ShipmentRecord).filter(
                    ShipmentRecord.id == order_number
                ).first()
                
                if record:
                    row_dict = {}
                    for column in inspect(ShipmentRecord).columns:
                        row_dict[column.name] = getattr(record, column.name)
                    return row_dict
                
                return None
                
        except Exception as e:
            logger.error(f"获取订单详情失败：{e}")
            return None
    
    def delete_order(self, order_number: str) -> Dict[str, Any]:
        """
        删除订单
        
        Args:
            order_number: 订单编号
            
        Returns:
            结果字典
        """
        try:
            with get_db() as db:
                inspector = inspect(db.bind)
                if "shipment_records" not in inspector.get_table_names():
                    return {
                        "success": False,
                        "message": "数据库表不存在"
                    }
                
                record = db.query(ShipmentRecord).filter(
                    ShipmentRecord.id == order_number
                ).first()
                
                if record:
                    db.delete(record)
                    db.commit()
                    logger.info(f"订单已删除：{order_number}")
                    return {
                        "success": True,
                        "message": f"订单 {order_number} 已删除"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"订单 {order_number} 不存在"
                    }
                
        except Exception as e:
            logger.exception(f"删除订单失败：{e}")
            return {
                "success": False,
                "message": f"删除失败：{str(e)}"
            }
    
    def clear_all_orders(self) -> Dict[str, Any]:
        """
        清空所有订单
        
        Returns:
            结果字典
        """
        try:
            with get_db() as db:
                inspector = inspect(db.bind)
                if "shipment_records" not in inspector.get_table_names():
                    return {
                        "success": False,
                        "message": "数据库表不存在"
                    }
                
                count = db.query(ShipmentRecord).count()
                db.query(ShipmentRecord).delete()
                db.commit()
                
                logger.info(f"已清空所有订单，共 {count} 条记录")
                return {
                    "success": True,
                    "message": f"已清空所有订单，共 {count} 条记录"
                }
                
        except Exception as e:
            logger.exception(f"清空订单失败：{e}")
            return {
                "success": False,
                "message": f"清空失败：{str(e)}"
            }
    
    def clear_shipment_by_unit(self, purchase_unit: str) -> Dict[str, Any]:
        """
        清理指定购买单位的出货记录
        
        Args:
            purchase_unit: 购买单位名称
            
        Returns:
            结果字典
        """
        try:
            with get_db() as db:
                inspector = inspect(db.bind)
                if "shipment_records" not in inspector.get_table_names():
                    return {
                        "success": False,
                        "message": "数据库表不存在"
                    }
                
                count = db.query(ShipmentRecord).filter(
                    ShipmentRecord.purchase_unit == purchase_unit
                ).count()
                
                db.query(ShipmentRecord).filter(
                    ShipmentRecord.purchase_unit == purchase_unit
                ).delete()
                db.commit()
                
                logger.info(f"已清理 {purchase_unit} 的出货记录，共 {count} 条记录")
                return {
                    "success": True,
                    "message": f"已清理 {purchase_unit} 的出货记录",
                    "deleted_orders": count
                }
                
        except Exception as e:
            logger.exception(f"清理出货记录失败：{e}")
            return {
                "success": False,
                "message": f"清理失败：{str(e)}"
            }
    
    def get_shipment_records(self, unit_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取出货记录列表
        
        Args:
            unit_name: 单位名称（可选）
            
        Returns:
            出货记录列表
        """
        try:
            with get_db() as db:
                inspector = inspect(db.bind)
                if "shipment_records" not in inspector.get_table_names():
                    return []
                
                query = db.query(ShipmentRecord)
                
                if unit_name:
                    query = query.filter(ShipmentRecord.purchase_unit == unit_name)
                
                records = query.order_by(
                    ShipmentRecord.created_at.desc()
                ).limit(100).all()
                
                rows = []
                for record in records:
                    row_dict = {}
                    for column in inspect(ShipmentRecord).columns:
                        row_dict[column.name] = getattr(record, column.name)
                    rows.append(row_dict)
                
                return rows
                
        except Exception as e:
            logger.error(f"获取出货记录失败：{e}")
            return []
    
    def update_shipment_record(
        self,
        record_id: int,
        unit_name: Optional[str] = None,
        products: Optional[List[Dict[str, Any]]] = None,
        date: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        更新出货记录
        
        Args:
            record_id: 记录 ID
            unit_name: 单位名称（可选）
            products: 产品列表（可选）
            date: 出货日期（可选）
            **kwargs: 其他要更新的字段
            
        Returns:
            结果字典
        """
        try:
            with get_db() as db:
                inspector = inspect(db.bind)
                if "shipment_records" not in inspector.get_table_names():
                    return {
                        "success": False,
                        "message": "数据库表不存在"
                    }
                
                record = db.query(ShipmentRecord).filter(
                    ShipmentRecord.id == record_id
                ).first()
                
                if not record:
                    return {
                        "success": False,
                        "message": f"记录 {record_id} 不存在"
                    }
                
                if unit_name:
                    record.purchase_unit = unit_name
                if date:
                    record.created_at = datetime.strptime(date, "%Y-%m-%d")
                
                for key, value in kwargs.items():
                    if hasattr(record, key):
                        setattr(record, key, value)
                
                record.updated_at = datetime.now()
                db.commit()
                
                logger.info(f"出货记录已更新：{record_id}")
                return {
                    "success": True,
                    "message": "出货记录已更新"
                }
                
        except Exception as e:
            logger.exception(f"更新出货记录失败：{e}")
            return {
                "success": False,
                "message": f"更新失败：{str(e)}"
            }
    
    def delete_shipment_record(self, record_id: int) -> Dict[str, Any]:
        """
        删除出货记录
        
        Args:
            record_id: 记录 ID
            
        Returns:
            结果字典
        """
        try:
            with get_db() as db:
                inspector = inspect(db.bind)
                if "shipment_records" not in inspector.get_table_names():
                    return {
                        "success": False,
                        "message": "数据库表不存在"
                    }
                
                record = db.query(ShipmentRecord).filter(
                    ShipmentRecord.id == record_id
                ).first()
                
                if not record:
                    return {
                        "success": False,
                        "message": f"记录 {record_id} 不存在"
                    }
                
                db.delete(record)
                db.commit()
                
                logger.info(f"出货记录已删除：{record_id}")
                return {
                    "success": True,
                    "message": "出货记录已删除"
                }
                
        except Exception as e:
            logger.exception(f"删除出货记录失败：{e}")
            return {
                "success": False,
                "message": f"删除失败：{str(e)}"
            }
    
    def export_to_excel(self, unit_name: Optional[str] = None) -> Dict[str, Any]:
        """
        导出出货记录为 Excel 文件
        
        Args:
            unit_name: 单位名称（可选）
            
        Returns:
            结果字典：
                - success: 是否成功
                - file_path: 文件路径
                - filename: 文件名
                - count: 导出记录数
        """
        try:
            from openpyxl import Workbook
            from app.utils.path_utils import get_data_dir
            
            logger.info(f"导出出货记录：unit_name={unit_name}")
            
            with get_db() as db:
                inspector = inspect(db.bind)
                if "shipment_records" not in inspector.get_table_names():
                    return {
                        "success": False,
                        "message": "出货记录表不存在",
                        "file_path": None,
                        "filename": None,
                        "count": 0
                    }
                
                query = db.query(ShipmentRecord)
                
                if unit_name:
                    query = query.filter(ShipmentRecord.purchase_unit == unit_name)
                
                records = query.order_by(
                    ShipmentRecord.created_at.desc()
                ).all()
                
                wb = Workbook()
                ws = wb.active
                ws.title = "出货记录"
                
                headers = ["ID", "购买单位", "产品名称", "型号", "数量 (KG)", "数量 (桶)", "规格", "单价", "金额", "状态", "创建时间", "打印时间", "打印机"]
                ws.append(headers)
                
                for record in records:
                    ws.append([
                        record.id,
                        record.purchase_unit or "",
                        record.product_name or "",
                        record.model_number or "",
                        record.quantity_kg or 0,
                        record.quantity_tins or 0,
                        record.tin_spec or "",
                        record.unit_price or 0,
                        record.amount or 0,
                        record.status or "",
                        record.created_at.strftime("%Y-%m-%d %H:%M:%S") if record.created_at else "",
                        record.printed_at.strftime("%Y-%m-%d %H:%M:%S") if record.printed_at else "",
                        record.printer_name or ""
                    ])
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                unit_prefix = unit_name if unit_name else "all"
                filename = f"shipment_records_{unit_prefix}_{timestamp}.xlsx"
                
                export_dir = os.path.join(get_data_dir(), "exports")
                os.makedirs(export_dir, exist_ok=True)
                file_path = os.path.join(export_dir, filename)
                
                wb.save(file_path)
                
                logger.info(f"出货记录导出完成：{file_path}, 共 {len(records)} 条记录")
                
                return {
                    "success": True,
                    "file_path": str(file_path),
                    "filename": filename,
                    "count": len(records)
                }
            
        except Exception as e:
            logger.exception(f"导出出货记录失败：{e}")
            return {
                "success": False,
                "message": f"导出失败：{str(e)}",
                "file_path": None,
                "filename": None,
                "count": 0
            }
    
    def set_order_sequence(self, sequence: int) -> Dict[str, Any]:
        """
        设置订单序号
        
        Args:
            sequence: 序号值
            
        Returns:
            结果字典
        """
        try:
            logger.info(f"设置订单序号：{sequence}")
            return {
                "success": True,
                "message": "序号已设置",
                "sequence": sequence
            }
        except Exception as e:
            logger.error(f"设置订单序号失败：{e}")
            return {
                "success": False,
                "message": f"设置失败：{str(e)}"
            }
    
    def reset_order_sequence(self) -> Dict[str, Any]:
        """
        重置订单序号
        
        Returns:
            结果字典
        """
        try:
            logger.info("重置订单序号")
            return {
                "success": True,
                "message": "序号已重置",
                "sequence": 1
            }
        except Exception as e:
            logger.error(f"重置订单序号失败：{e}")
            return {
                "success": False,
                "message": f"重置失败：{str(e)}"
            }
