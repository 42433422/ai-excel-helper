#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BarTender 集成模块
用于从订单数据自动填充 BarTender 模板，生成标签
"""

import os
import logging
import win32com.client
from typing import Dict, List, Optional

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BarTenderIntegrator:
    """BarTender 集成器"""
    
    def __init__(self):
        """
        初始化 BarTender 集成器
        """
        self.bartender_app = None
        self.format = None
    
    def connect(self):
        """
        连接到 BarTender 应用程序
        :return: 是否连接成功
        """
        try:
            # 创建 BarTender 应用实例
            self.bartender_app = win32com.client.Dispatch("BarTender.Application")
            logger.info("成功连接到 BarTender 应用")
            return True
        except Exception as e:
            logger.error(f"连接 BarTender 失败: {e}")
            return False
    
    def open_template(self, template_path: str):
        """
        打开指定的 BarTender 模板文件
        :param template_path: 模板文件路径
        :return: 是否打开成功
        """
        try:
            if not os.path.exists(template_path):
                logger.error(f"模板文件不存在: {template_path}")
                return False
            
            # 打开模板
            self.format = self.bartender_app.Formats.Open(template_path, False, "")
            logger.info(f"成功打开模板文件: {template_path}")
            return True
        except Exception as e:
            logger.error(f"打开模板文件失败: {e}")
            return False
    
    def get_template_info(self):
        """
        获取模板的基本信息
        :return: 模板信息字典
        """
        try:
            if not self.format:
                logger.error("模板未打开")
                return {}
            
            info = {}
            # 获取模板的基本属性
            info["name"] = self.format.Name
            info["path"] = self.format.Path
            info["page_count"] = self.format.PageCount
            info["objects_count"] = self.format.Objects.Count
            
            # 获取所有对象信息
            objects_info = []
            for i in range(self.format.Objects.Count):
                obj = self.format.Objects.Item(i + 1)
                objects_info.append({
                    "name": obj.Name,
                    "type": obj.Type,
                    "left": obj.Left,
                    "top": obj.Top,
                    "width": obj.Width,
                    "height": obj.Height
                })
            info["objects"] = objects_info
            
            logger.info(f"模板信息: {info}")
            return info
        except Exception as e:
            logger.error(f"获取模板信息失败: {e}")
            return {}
    
    def get_substrings(self):
        """
        获取模板中的所有子字符串
        :return: 子字符串列表
        """
        try:
            if not self.format:
                logger.error("模板未打开")
                return []
            
            substrings = []
            # 获取所有子字符串
            for i in range(self.format.SubStrings.Count):
                substr = self.format.SubStrings.Item(i + 1)
                substrings.append({
                    "name": substr.Name,
                    "value": substr.Value,
                    "type": substr.Type,
                    "length": substr.Length
                })
            
            logger.info(f"模板中的子字符串: {substrings}")
            return substrings
        except Exception as e:
            logger.error(f"获取子字符串失败: {e}")
            return []
    
    def get_named_substrings(self):
        """
        获取模板中的所有命名子字符串
        :return: 命名子字符串列表
        """
        try:
            if not self.format:
                logger.error("模板未打开")
                return []
            
            named_substrings = []
            # 获取所有命名子字符串
            for i in range(self.format.NamedSubStrings.Count):
                substr = self.format.NamedSubStrings.Item(i + 1)
                named_substrings.append({
                    "name": substr.Name,
                    "value": substr.Value,
                    "type": substr.Type,
                    "length": substr.Length
                })
            
            logger.info(f"模板中的命名子字符串: {named_substrings}")
            return named_substrings
        except Exception as e:
            logger.error(f"获取命名子字符串失败: {e}")
            return []
    
    def close_template(self):
        """
        关闭模板
        :return: 是否关闭成功
        """
        try:
            if self.format:
                self.format.Close(1)  # 1 = 不保存更改
                self.format = None
                logger.info("成功关闭模板")
                return True
        except Exception as e:
            logger.error(f"关闭模板失败: {e}")
            return False
        return True
    
    def disconnect(self):
        """
        断开与 BarTender 应用的连接
        :return: 是否断开成功
        """
        try:
            self.close_template()
            
            if self.bartender_app:
                self.bartender_app = None
                logger.info("成功断开 BarTender 连接")
            return True
        except Exception as e:
            logger.error(f"断开 BarTender 连接失败: {e}")
            return False
    
    def analyze_template(self, template_path: str):
        """
        分析模板文件，获取模板的详细信息
        :param template_path: 模板文件路径
        :return: 模板分析结果
        """
        try:
            # 连接到 BarTender
            if not self.connect():
                return None
            
            # 打开模板
            if not self.open_template(template_path):
                self.disconnect()
                return None
            
            # 获取模板信息
            template_info = self.get_template_info()
            
            # 获取子字符串
            substrings = self.get_substrings()
            
            # 获取命名子字符串
            named_substrings = self.get_named_substrings()
            
            # 断开连接
            self.disconnect()
            
            # 返回分析结果
            return {
                "template_info": template_info,
                "substrings": substrings,
                "named_substrings": named_substrings
            }
        except Exception as e:
            logger.error(f"分析模板失败: {e}")
            self.disconnect()
            return None


# 测试代码
if __name__ == "__main__":
    # 模板路径
    template_path = "c:/Users/97088/Desktop/新建文件夹 (4)/AI助手/8520F哑光白面.btw"
    
    print("=== BarTender 模板集成模块 ===")
    print(f"模板文件: {template_path}")
    print(f"文件存在: {os.path.exists(template_path)}")
    print()
    
    # 创建集成器
    integrator = BarTenderIntegrator()
    
    # 分析模板
    result = integrator.analyze_template(template_path)
    
    if result:
        print("✅ 模板分析成功")
        print()
        
        # 打印模板信息（避免KeyError）
        print("模板基本信息:")
        template_info = result['template_info']
        if template_info:
            for key, value in template_info.items():
                print(f"  {key}: {value}")
        else:
            print("  无法获取模板详细信息（可能是BarTender版本兼容性问题）")
        print()
        
        # 打印子字符串信息
        print(f"子字符串数量: {len(result['substrings'])}")
        if result['substrings']:
            print("子字符串列表:")
            for i, substr in enumerate(result['substrings']):
                print(f"  {i+1}. {substr}")
        print()
        
        # 打印命名子字符串信息
        named_substrings = result['named_substrings']
        print(f"命名子字符串数量: {len(named_substrings)}")
        if named_substrings:
            print("命名子字符串列表:")
            for substr in named_substrings:
                print(f"  {substr['name']}: {substr['value']}")
        else:
            print("  模板中没有命名子字符串，可能需要在BarTender中手动添加")
            print("  请在BarTender中打开模板，添加以下命名数据源：")
            print("  - ProductNumber: 产品编号")
            print("  - ProductName: 产品名称")
            print("  - ProductionDate: 生产日期")
            print("  - Spec: 产品规格")
    else:
        print("❌ 模板分析失败")
        print("  请确保BarTender软件已安装并正在运行")
        print("  请确保模板文件路径正确")
        print("  请确保当前用户有足够的权限访问BarTender")
    print()
    print("=== 分析完成 ===")
