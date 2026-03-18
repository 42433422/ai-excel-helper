#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标签生成模块
用于从订单数据生成BarTender标签
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
from bartender_integrator import BarTenderIntegrator

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LabelGenerator:
    """
    标签生成器
    从订单数据生成BarTender标签
    """
    
    def __init__(self, template_path: str):
        """
        初始化标签生成器
        :param template_path: BarTender模板文件路径
        """
        self.template_path = template_path
        self.integrator = BarTenderIntegrator()
        
        # 检查模板文件是否存在
        if not os.path.exists(template_path):
            logger.error(f"模板文件不存在: {template_path}")
            raise FileNotFoundError(f"模板文件不存在: {template_path}")
    
    def generate_labels(self, order_data: Dict) -> List[str]:
        """
        从订单数据生成标签
        :param order_data: 订单数据
        :return: 生成的标签文件列表
        """
        try:
            logger.info(f"开始生成标签，订单数据: {order_data}")
            
            # 获取产品列表
            products = order_data.get("products", [])
            
            if not products:
                logger.error("订单中没有产品信息")
                return []
            
            generated_files = []
            
            # 遍历产品，生成标签
            for product in products:
                # 准备标签数据
                label_data = self._prepare_label_data(order_data, product)
                
                # 生成标签
                output_file = self._generate_single_label(label_data, product)
                if output_file:
                    generated_files.append(output_file)
            
            logger.info(f"成功生成 {len(generated_files)} 个标签文件")
            return generated_files
        except Exception as e:
            logger.error(f"生成标签失败: {e}")
            return []
    
    def _prepare_label_data(self, order_data: Dict, product: Dict) -> Dict[str, str]:
        """
        准备标签数据
        :param order_data: 订单数据
        :param product: 产品数据
        :return: 标签数据
        """
        # 获取购买单位信息
        purchase_unit = order_data.get("purchase_unit", "")
        
        # 获取当前日期
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # 准备标签数据
        label_data = {
            "ProductNumber": product.get("model_number", ""),
            "ProductName": product.get("name", ""),
            "ProductionDate": current_date,
            "Spec": f"{product.get('tin_spec', 10.0)}kg/桶",
            "PurchaseUnit": purchase_unit,
            "Quantity": str(product.get("quantity_tins", 0)) + "桶",
            "TotalWeight": f"{product.get('quantity_kg', 0.0)}kg"
        }
        
        logger.info(f"准备的标签数据: {label_data}")
        return label_data
    
    def _generate_single_label(self, label_data: Dict[str, str], product: Dict) -> Optional[str]:
        """
        生成单个标签
        :param label_data: 标签数据
        :param product: 产品数据
        :return: 生成的标签文件路径
        """
        try:
            # 生成输出文件名
            output_dir = "outputs"
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            product_name = product.get("name", "未知产品").replace(" ", "_").replace("/", "_")
            output_filename = f"{output_dir}/{product_name}_{timestamp}.pdf"
            
            logger.info(f"生成标签: {output_filename}")
            logger.info(f"标签数据: {label_data}")
            
            # 由于当前版本的BarTender集成模块还在开发中，这里暂时只生成标签数据文件
            # 后续可以替换为实际的BarTender标签生成代码
            
            # 保存标签数据到文件（用于调试）
            data_filename = f"{output_dir}/{product_name}_{timestamp}_data.txt"
            with open(data_filename, "w", encoding="utf-8") as f:
                for key, value in label_data.items():
                    f.write(f"{key}: {value}\n")
            
            logger.info(f"标签数据已保存到: {data_filename}")
            
            # 返回生成的文件路径
            return data_filename
        except Exception as e:
            logger.error(f"生成单个标签失败: {e}")
            return None
    
    def analyze_template(self) -> Optional[Dict]:
        """
        分析模板文件
        :return: 模板分析结果
        """
        try:
            return self.integrator.analyze_template(self.template_path)
        except Exception as e:
            logger.error(f"分析模板失败: {e}")
            return None


# 测试代码
if __name__ == "__main__":
    # 模板路径
    template_path = "c:/Users/97088/Desktop/新建文件夹 (4)/AI助手/8520F哑光白面.btw"
    
    # 示例订单数据
    order_data = {
        "purchase_unit": "温总",
        "products": [
            {
                "model_number": "NC50F",
                "name": "NC哑光清面漆",
                "quantity_tins": 3,
                "tin_spec": 25.0,
                "quantity_kg": 75.0
            }
        ]
    }
    
    try:
        # 创建标签生成器
        generator = LabelGenerator(template_path)
        
        # 生成标签
        generated_files = generator.generate_labels(order_data)
        
        if generated_files:
            print("✅ 标签生成成功")
            for file in generated_files:
                print(f"  生成文件: {file}")
        else:
            print("❌ 标签生成失败")
    except Exception as e:
        print(f"❌ 错误: {e}")
