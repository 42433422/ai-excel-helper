"""
数据导入服务模块

提供从 Excel 提取的数据导入到数据库的服务。
"""

import logging
from datetime import datetime
from typing import Any

from app.db.models import Product
from app.db.session import get_db
from app.neuro_bus.event_publisher_mixin import NeuroEventPublisherMixin

logger = logging.getLogger(__name__)


class ProductImportService(NeuroEventPublisherMixin):
    """产品数据导入服务类"""

    def __init__(self):
        """初始化产品导入服务"""
        pass

    def clean_data(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        清洗数据

        Args:
            data: 原始数据列表

        Returns:
            清洗后的数据列表
        """
        cleaned = []
        for row in data:
            cleaned_row = {}
            for key, value in row.items():
                # 去除字符串两端空格
                if isinstance(value, str):
                    value = value.strip()
                # 处理空值
                if value == "" or value is None:
                    value = None
                cleaned_row[key] = value
            cleaned.append(cleaned_row)
        return cleaned

    def validate_data(self, data: list[dict[str, Any]]) -> tuple[list[dict], list[dict]]:
        """
        验证数据

        Args:
            data: 数据列表

        Returns:
            (valid_data, invalid_data) 有效数据和无效数据
        """
        valid = []
        invalid = []

        for row in data:
            errors = []

            # 检查必填字段
            if not row.get("product_code") and not row.get("product_name"):
                errors.append("产品编码或产品名称不能同时为空")

            # 检查价格格式
            if "unit_price" in row and row["unit_price"] is not None:
                try:
                    price = float(row["unit_price"])
                    if price < 0:
                        errors.append("单价不能为负数")
                except (ValueError, TypeError):
                    errors.append("单价格式不正确")

            if errors:
                invalid.append({"data": row, "errors": errors})
            else:
                valid.append(row)

        return valid, invalid

    def check_duplicates(
        self, data: list[dict[str, Any]], skip_duplicates: bool = True
    ) -> tuple[list[dict], list[dict]]:
        """
        检查重复数据

        Args:
            data: 数据列表
            skip_duplicates: 是否跳过重复项

        Returns:
            (new_data, duplicates) 新数据和重复数据
        """
        if not data:
            return [], []

        new_data = []
        duplicates = []

        with get_db() as db:
            for row in data:
                is_duplicate = False

                # 检查型号/编码是否重复（Excel 列名多为 product_code，库字段为 model_number）
                code = (row.get("product_code") or row.get("model_number") or "").strip()
                if code:
                    existing = db.query(Product).filter(Product.model_number == code).first()
                    if existing:
                        is_duplicate = True

                # 如果没有产品编码，检查产品名称 + 规格
                if not is_duplicate and row.get("product_name"):
                    query = db.query(Product).filter(Product.name == row["product_name"])
                    if row.get("specification"):
                        query = query.filter(Product.specification == row["specification"])
                    existing = query.first()
                    if existing:
                        is_duplicate = True

                if is_duplicate:
                    duplicates.append(row)
                else:
                    new_data.append(row)

        return new_data, duplicates

    def import_data(
        self,
        data: list[dict[str, Any]],
        skip_duplicates: bool = True,
        validate_before_import: bool = True,
        clean_data: bool = True,
        *,
        replace_attendance_detail_tagged: bool = False,
    ) -> dict[str, Any]:
        """
        导入产品数据

        Args:
            data: 数据列表
            skip_duplicates: 是否跳过重复项
            validate_before_import: 导入前是否验证
            clean_data: 是否清洗数据

        Returns:
            导入结果：
                - imported: 导入数量
                - skipped: 跳过数量
                - failed: 失败数量
                - details: 详细信息
        """
        result = {
            "imported": 0,
            "skipped": 0,
            "failed": 0,
            "details": {"skipped_items": [], "failed_items": []},
        }

        try:
            if replace_attendance_detail_tagged:
                tag = "__from_attendance_detail__"
                with get_db() as db:
                    deleted = (
                        db.query(Product)
                        .filter(Product.description == tag)
                        .delete(synchronize_session=False)
                    )
                logger.info("已移除此前考勤明细导入的人员记录 %s 条", deleted)

            # 1. 清洗数据
            if clean_data:
                data = self.clean_data(data)

            # 2. 验证数据
            if validate_before_import:
                valid_data, invalid_data = self.validate_data(data)
                result["failed"] = len(invalid_data)
                result["details"]["failed_items"] = invalid_data
                data = valid_data

            # 3. 检查重复
            if skip_duplicates:
                new_data, duplicates = self.check_duplicates(data, skip_duplicates=True)
                result["skipped"] = len(duplicates)
                result["details"]["skipped_items"] = [
                    d.get("product_code") or d.get("product_name") for d in duplicates
                ]
                data = new_data

            # 4. 批量导入
            if not data:
                return result

            with get_db() as db:
                for row in data:
                    try:
                        product = Product(
                            model_number=(
                                row.get("product_code") or row.get("model_number") or None
                            )
                            or None,
                            name=row.get("product_name"),
                            specification=row.get("specification"),
                            price=float(row.get("unit_price", 0) or 0),
                            unit=row.get("unit", "个") or "个",
                            description=row.get("remark", "") or row.get("description", "") or "",
                            is_active=1,
                            created_at=datetime.now(),
                            updated_at=datetime.now(),
                        )
                        db.add(product)
                        result["imported"] += 1
                    except Exception as e:
                        logger.error(f"导入产品失败：{e}")
                        result["failed"] += 1
                        result["details"]["failed_items"].append({"data": row, "error": str(e)})

                db.commit()

            try:
                from app.infrastructure.mods.hooks import trigger

                trigger("product.imported", count=result["imported"], products=data)
            except Exception as hook_err:
                logger.warning(f"Hook trigger failed: {hook_err}")

            logger.info(
                f"产品导入完成：成功{result['imported']}, "
                f"跳过{result['skipped']}, 失败{result['failed']}"
            )

        except Exception as e:
            logger.exception(f"导入产品数据失败：{e}")
            result["error"] = str(e)

        return result


from app.neuro_bus.bus import get_neuro_bus
from app.neuro_bus.events.base import EventPriority, NeuroEvent
from app.neuro_bus.neuro_service_instrumentation import instrument_service_layer_class

instrument_service_layer_class(ProductImportService, "app.services.product_import_service")
