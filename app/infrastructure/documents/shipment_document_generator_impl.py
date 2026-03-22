from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from PIL import Image, ImageDraw, ImageFont

from app.application.ports.shipment_document_generator import ShipmentDocumentGeneratorPort
from app.db.models import Product, PurchaseUnit
from app.db.session import get_db
from app.domain.shipment.shipment_product_parser import prepare_parsed_products
from app.infrastructure.documents.legacy_shipment_document import (
    load_legacy_shipment_document_generator,
)
from app.infrastructure.lookups.purchase_unit_resolver import (
    ResolvedPurchaseUnit,
    resolve_purchase_unit,
)
from app.utils.path_utils import get_app_data_dir, get_base_dir, get_resource_path

logger = logging.getLogger(__name__)


class SimpleLabelGenerator:
    """简单的标签生成器，使用 PIL 直接绘制标签图片"""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.width = 900
        self.height = 600
        self.bg_color = (255, 255, 255)
        self.border_color = (0, 0, 0)
        self.text_color = (0, 0, 0)

    def _get_font(self, size: int):
        font_paths = [
            "msyhbd.ttf",
            "simhei.ttf",
            "simsun.ttc",
            "arial.ttf",
            "times.ttf",
        ]
        for font_path in font_paths:
            try:
                return ImageFont.truetype(font_path, size)
            except:
                continue

        import sys
        if sys.platform == 'win32':
            win_fonts = [
                "C:\\Windows\\Fonts\\msyhbd.ttf",
                "C:\\Windows\\Fonts\\simhei.ttf",
                "C:\\Windows\\Fonts\\simsun.ttc",
                "C:\\Windows\\Fonts\\msyh.ttf",
            ]
            for font_path in win_fonts:
                try:
                    return ImageFont.truetype(font_path, size)
                except:
                    continue

        return ImageFont.load_default()

    def generate_label(self, product_data: Dict[str, Any], order_number: str, label_index: int = 1) -> Optional[str]:
        try:
            image = Image.new('RGB', (self.width, self.height), self.bg_color)
            draw = ImageDraw.Draw(image)

            draw.rectangle([0, 0, self.width - 1, self.height - 1], outline=self.border_color, width=3)

            product_name = product_data.get('name', '') or product_data.get('product_name', '')
            has_ratio = not any(keyword in product_name for keyword in ['剂', '料'])

            y_pn = 25
            h_pn = 70
            y_name = y_pn + h_pn + 20
            h_name = 62

            if has_ratio:
                y_ratio = y_name + h_name + 20
                h_ratio = 94
                y_date = y_ratio + h_ratio + 20
                h_date = 62
                y_spec = y_date + h_date + 20
                h_spec = 62
                y_footer = y_spec + h_spec + 20
            else:
                y_pn = 25
                h_pn = 100
                y_name = y_pn + h_pn
                h_name = 100
                y_date = y_name + h_name
                h_date = 100
                y_spec = y_date + h_date
                h_spec = 100

            label_x = 20
            label_width = 180
            col1_x = 180
            col1_width = 320
            col2_x = 500
            col2_width = 150
            col3_x = 650

            if has_ratio:
                draw.line([label_x + label_width, y_pn, label_x + label_width, y_spec + h_spec], fill=self.border_color, width=2)
                draw.line([col2_x + col2_width, y_date, col2_x + col2_width, y_spec + h_spec], fill=self.border_color, width=2)
                draw.line([col1_x + col1_width, y_date, col1_x + col1_width, y_spec + h_spec], fill=self.border_color, width=2)
            else:
                draw.line([label_x + label_width, y_pn, label_x + label_width, 599], fill=self.border_color, width=2)
                draw.line([col2_x + col2_width, y_date, col2_x + col2_width, 599], fill=self.border_color, width=2)

            draw.line([20, y_pn + h_pn, 880, y_pn + h_pn], fill=self.border_color, width=2)
            draw.line([20, y_name + h_name, 880, y_name + h_name], fill=self.border_color, width=2)

            if has_ratio:
                draw.line([20, y_ratio + h_ratio, 880, y_ratio + h_ratio], fill=self.border_color, width=2)

            draw.line([20, y_date + h_date, 880, y_date + h_date], fill=self.border_color, width=2)
            draw.line([20, y_spec + h_spec, 880, y_spec + h_spec], fill=self.border_color, width=2)

            pn_value_font = self._get_font(70)
            draw.text((45, y_pn + 12), "产品编号", font=self._get_font(40), fill=self.text_color)
            pn_value = product_data.get('model_number', '') or product_data.get('product_number', '')
            pn_bbox = draw.textbbox((0, 0), pn_value, font=pn_value_font)
            pn_width = pn_bbox[2] - pn_bbox[0]
            pn_x = 200 + (680 - pn_width) // 2
            draw.text((pn_x, y_pn + 12), pn_value, font=pn_value_font, fill=self.text_color)

            name_value_font = self._get_font(58)
            draw.text((45, y_name + 12), "产品名称", font=self._get_font(40), fill=self.text_color)
            name_bbox = draw.textbbox((0, 0), product_name, font=name_value_font)
            name_width = name_bbox[2] - name_bbox[0]
            name_x = 200 + (680 - name_width) // 2
            draw.text((name_x, y_name + 12), product_name, font=name_value_font, fill=self.text_color)

            if has_ratio:
                ratio_label = "参考配比"
                ratio_label_font = self._get_font(32)
                draw.text((45, y_ratio + 10), ratio_label, font=ratio_label_font, fill=self.text_color)
                ratio_text = product_data.get('ratio', '1 : 0.5-0.6 : 0.5-0.8')
                ratio_value_font = self._get_font(38)
                ratio_bbox = draw.textbbox((0, 0), ratio_text, font=ratio_value_font)
                ratio_width = ratio_bbox[2] - ratio_bbox[0]
                ratio_x = 200 + (680 - ratio_width) // 2
                draw.text((ratio_x, y_ratio + 10), ratio_text, font=ratio_value_font, fill=self.text_color)

            date_font = self._get_font(38)
            production_date = datetime.now().strftime("%Y.%m.%d")
            draw.text((45, y_date + 12), "生产日期", font=date_font, fill=self.text_color)
            draw.text((210, y_date + 12), production_date, font=date_font, fill=self.text_color)
            draw.text((520, y_date + 12), "保质期", font=date_font, fill=self.text_color)
            draw.text((670, y_date + 12), "6个月", font=date_font, fill=self.text_color)

            tin_spec = product_data.get('tin_spec', 0)
            quantity_tins = product_data.get('quantity_tins', 0)
            specification = f"{tin_spec}±0.1KG/桶" if tin_spec else "20±0.1KG/桶"
            draw.text((45, y_spec + 12), "产品规格", font=date_font, fill=self.text_color)
            draw.text((210, y_spec + 12), specification, font=date_font, fill=self.text_color)
            draw.text((520, y_spec + 12), "检验员", font=date_font, fill=self.text_color)
            draw.text((670, y_spec + 12), "合格", font=date_font, fill=self.text_color)

            if has_ratio:
                footer_text = "请充分搅拌均匀后使用"
                footer_font = self._get_font(48)
                footer_bbox = draw.textbbox((0, 0), footer_text, font=footer_font)
                footer_width = footer_bbox[2] - footer_bbox[0]
                footer_height = footer_bbox[3] - footer_bbox[1]
                footer_x = 20 + (860 - footer_width) // 2
                footer_y = y_footer + (h_spec - footer_height) // 2
                draw.text((footer_x, footer_y), footer_text, font=footer_font, fill=self.text_color)

            os.makedirs(self.output_dir, exist_ok=True)
            safe_name = product_name.replace("/", "_").replace(" ", "_")[:20]
            filename = f"{order_number}_第{label_index}项_{safe_name}.png"
            output_path = os.path.join(self.output_dir, filename)
            image.save(output_path)
            logger.info(f"标签已生成: {output_path}")
            return filename

        except Exception as e:
            logger.error(f"生成标签失败: {e}")
            return None

    def generate_labels_for_order(self, order_number: str, products: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        labels = []
        for i, product in enumerate(products, 1):
            filename = self.generate_label(product, order_number, i)
            if filename:
                labels.append({
                    "filename": filename,
                    "order_number": order_number,
                    "label_number": str(i)
                })
        return labels


class LegacyShipmentDocumentGenerator(ShipmentDocumentGeneratorPort):
    """
    基于旧版 AI助手/shipment_document.py 的文档生成适配器。

    约束：
    - 产品匹配只使用主库 `products` 表（不再走客户专属 sqlite 库）
    - 单位名统一从 `customers` 解析/规范化
    """

    def __init__(self):
        # 模板/外部资源统一放在 XCAGI/resources 下，避免依赖项目外目录
        # 兼容期：如果 resources 下不存在，再回退到 XCAGI/AI助手/uploads（仍在项目内）
        from app.utils.path_utils import get_resource_path

        resources_template_dir = get_resource_path("ai_assistant", "uploads")
        legacy_template_dir = os.path.join(get_base_dir(), "AI助手", "uploads")
        self.template_dir = resources_template_dir if os.path.isdir(resources_template_dir) else legacy_template_dir
        self.output_dir = os.path.join(get_app_data_dir(), "shipment_outputs")
        os.makedirs(self.output_dir, exist_ok=True)

    def _load_products_from_main_db(self) -> List[Dict[str, Any]]:
        products: List[Dict[str, Any]] = []
        with get_db() as db:
            rows = db.query(Product).filter(Product.is_active == 1).all()
            for p in rows:
                products.append(
                    {
                        "id": p.id,
                        "model_number": p.model_number or "",
                        "name": p.name or "",
                        "price": float(p.price) if p.price else 0.0,
                        "specification": p.specification or "",
                        "brand": p.brand or "",
                        "unit": p.unit or "",
                    }
                )
        return products

    def generate(
        self,
        *,
        unit_name: str,
        products: List[Dict[str, Any]],
        date: Optional[str] = None,
        template_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        # 1) 统一单位名来源：purchase_units 主库
        resolved = resolve_purchase_unit(unit_name)
        if not resolved:
            return {
                "success": False,
                "message": f"未找到购买单位：{unit_name}",
                "doc_name": None,
                "file_path": None,
            }

        # 2) 加载 legacy 生成器
        loaded = load_legacy_shipment_document_generator(caller_file=__file__)
        ShipmentDocumentGenerator = loaded.ShipmentDocumentGenerator
        PurchaseUnitInfo = loaded.PurchaseUnitInfo

        # 3) 构造 purchase_unit_info
        purchase_unit_info = PurchaseUnitInfo(
            name=resolved.unit_name,
            contact_person=resolved.contact_person,
            contact_phone=resolved.contact_phone,
            address=resolved.address,
            id=resolved.id,
        )

        # 4) 产品匹配（仅主库 products）
        db_products = self._load_products_from_main_db()
        parsed_products: List[Dict[str, Any]] = prepare_parsed_products(
            input_products=products,
            db_products=db_products,
        )

        if not parsed_products:
            return {
                "success": False,
                "message": "产品列表为空或无有效产品名称",
                "doc_name": None,
                "file_path": None,
            }

        parsed_data: Dict[str, Any] = {"purchase_unit": resolved.unit_name, "products": parsed_products}

        # 5) 调用 legacy 生成逻辑
        from app.db.init_db import get_db_path

        generator = ShipmentDocumentGenerator(db_path=get_db_path("products.db"))
        doc = generator.generate_document(
            order_text="",
            parsed_data=parsed_data,
            purchase_unit=purchase_unit_info,
            template_name=template_name,
        )

        if hasattr(doc, "to_dict"):
            info = doc.to_dict()
            file_path = info.get("filepath")
            filename = info.get("filename") or (os.path.basename(file_path) if file_path else "")
            order_number = info.get("order_number")
            total_amount = info.get("total_amount")
            total_quantity = info.get("total_quantity")
        else:
            file_path = getattr(doc, "filepath", None)
            filename = getattr(doc, "filename", os.path.basename(file_path) if file_path else "")
            order_number = getattr(doc, "order_number", None)
            total_amount = getattr(doc, "total_amount", None)
            total_quantity = getattr(doc, "total_quantity", None)

        # 6) 生成标签图片
        labels_dir = get_resource_path("ai_assistant", "商标导出")
        label_generator = SimpleLabelGenerator(labels_dir)
        generated_labels = label_generator.generate_labels_for_order(
            order_number=order_number or filename.replace(".xlsx", ""),
            products=parsed_products
        )

        return {
            "success": True,
            "message": "发货单生成成功",
            "doc_name": filename,
            "file_path": file_path,
            "order_number": order_number,
            "total_amount": total_amount,
            "total_quantity": total_quantity,
            "purchase_unit": resolved.unit_name,
            "unit_id": resolved.id,
            "parsed_products": parsed_products,
            "labels": generated_labels,
        }

