"""
发货单相关 Celery 任务模块

包含大批量发货单生成、打印等异步任务。
"""

from typing import List, Dict, Any, Optional
import logging
import os

from app.extensions import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def generate_shipment_order(
    self,
    unit_name: str,
    products: List[Dict[str, Any]],
    date: Optional[str] = None
) -> Dict[str, Any]:
    """
    生成发货单（异步任务）
    
    Args:
        unit_name: 单位名称
        products: 产品列表，每个产品包含：
            - product_name: 产品名称
            - quantity: 数量
            - price: 价格（可选）
        date: 发货日期（可选，默认今天）
        
    Returns:
        结果字典：
            - success: 是否成功
            - doc_name: 文档名称
            - file_path: 文件路径
            - message: 响应消息
    """
    try:
        logger.info(f"开始生成发货单：{unit_name}, 产品数量：{len(products)}")
        
        # 调用服务层生成发货单
        from app.services.shipment_service import ShipmentService
        service = ShipmentService()
        result = service.generate_shipment_document(
            unit_name=unit_name,
            products=products,
            date=date
        )
        
        logger.info(f"发货单生成完成：{result}")
        return result
        
    except Exception as e:
        logger.exception(f"生成发货单失败：{e}")
        try:
            self.retry(exc=e, countdown=60)
        except self.MaxRetriesExceededError:
            logger.error("生成发货单达到最大重试次数")
            return {
                "success": False,
                "message": f"生成失败：{str(e)}",
                "doc_name": None,
                "file_path": None
            }


@celery_app.task(bind=True, max_retries=3)
def generate_batch_shipment_orders(
    self,
    orders: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    批量生成发货单
    
    Args:
        orders: 订单列表，每个订单包含：
            - unit_name: 单位名称
            - products: 产品列表
            - date: 发货日期（可选）
            
    Returns:
        结果字典：
            - success: 是否成功
            - total: 总订单数
            - succeeded: 成功数量
            - failed: 失败数量
            - results: 每个订单的结果
    """
    try:
        logger.info(f"开始批量生成发货单，订单数：{len(orders)}")
        
        results = []
        succeeded = 0
        failed = 0
        
        for order in orders:
            try:
                result = generate_shipment_order(
                    unit_name=order.get("unit_name"),
                    products=order.get("products", []),
                    date=order.get("date")
                )
                results.append(result)
                if result.get("success"):
                    succeeded += 1
                else:
                    failed += 1
            except Exception as e:
                logger.exception(f"生成单个发货单失败：{e}")
                failed += 1
                results.append({
                    "success": False,
                    "message": str(e)
                })
        
        logger.info(f"批量生成完成：成功 {succeeded}, 失败 {failed}")
        
        return {
            "success": failed == 0,
            "total": len(orders),
            "succeeded": succeeded,
            "failed": failed,
            "results": results
        }
        
    except Exception as e:
        logger.exception(f"批量生成发货单失败：{e}")
        try:
            self.retry(exc=e, countdown=120)
        except self.MaxRetriesExceededError:
            logger.error("批量生成发货单达到最大重试次数")
            return {
                "success": False,
                "message": f"批量生成失败：{str(e)}",
                "total": len(orders),
                "succeeded": 0,
                "failed": len(orders),
                "results": []
            }


@celery_app.task(bind=True, max_retries=3)
def print_shipment_document(
    self,
    file_path: str,
    printer_name: str | None = None,
    copies: int = 1
) -> Dict[str, Any]:
    """
    打印发货单
    
    Args:
        file_path: 文件路径
        printer_name: 打印机名称（可选，使用默认打印机）
        copies: 打印份数
        
    Returns:
        结果字典：
            - success: 是否成功
            - message: 响应消息
    """
    try:
        logger.info(f"开始打印发货单：{file_path}, 打印机：{printer_name}, 份数：{copies}")
        
        # 1. 验证文件存在
        import os
        if not os.path.exists(file_path):
            return {
                "success": False,
                "message": f"文件不存在：{file_path}"
            }
        
        # 2. 标记为已打印（更新数据库状态）
        from app.services.shipment_service import ShipmentService
        service = ShipmentService()
        result = service.mark_as_printed(file_path=file_path)
        
        # 3. 记录打印日志
        logger.info(f"发货单已标记为打印状态：{file_path}")
        
        # 注意：实际的物理打印需要在客户端完成
        # 这里只提供服务器端的打印状态管理
        # 如果需要服务器端打印，可以使用以下库：
        # - pywin32 (Windows)
        # - cups (Linux)
        # - python-escpos (小票打印机)
        
        result = {
            "success": True,
            "message": "发货单已标记为已打印，请在客户端完成物理打印",
            "file_path": file_path,
            "printed_at": result.get("printed_at")
        }
        
        logger.info(f"打印完成：{result}")
        return result
        
    except Exception as e:
        logger.exception(f"打印发货单失败：{e}")
        try:
            self.retry(exc=e, countdown=30)
        except self.MaxRetriesExceededError:
            logger.error("打印发货单达到最大重试次数")
            return {
                "success": False,
                "message": f"打印失败：{str(e)}"
            }


@celery_app.task
def cleanup_old_shipment_documents(days: int = 90) -> int:
    """
    清理旧的发货单文件
    
    Args:
        days: 保留天数
        
    Returns:
        清理的文件数量
    """
    try:
        logger.info(f"开始清理 {days} 天前的发货单文件")
        
        import os
        import time
        from datetime import datetime, timedelta
        from app.services.shipment_service import ShipmentService
        
        service = ShipmentService()
        output_dir = service.output_dir
        
        if not os.path.exists(output_dir):
            logger.info(f"发货单输出目录不存在：{output_dir}")
            return 0
        
        # 计算删除截止日期
        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned_count = 0
        
        # 遍历目录中的所有文件
        for filename in os.listdir(output_dir):
            file_path = os.path.join(output_dir, filename)
            
            if not os.path.isfile(file_path):
                continue
            
            # 获取文件修改时间
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            # 如果文件早于截止日期，则删除
            if file_mtime < cutoff_date:
                try:
                    os.remove(file_path)
                    cleaned_count += 1
                    logger.info(f"已删除旧发货单：{filename}")
                except Exception as e:
                    logger.warning(f"删除文件失败 {filename}: {e}")
        
        logger.info(f"清理完成，共清理 {cleaned_count} 个文件")
        return cleaned_count
        
    except Exception as e:
        logger.exception(f"清理旧文件失败：{e}")
        return 0
