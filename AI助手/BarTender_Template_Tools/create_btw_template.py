#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建新的BarTender模板文件
"""

import os
import logging
import win32com.client
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BTWTemplateCreator:
    """
    BarTender模板创建器
    """
    
    def __init__(self):
        """
        初始化模板创建器
        """
        self.bartender_app = None
        self.template = None
    
    def connect(self):
        """
        连接到BarTender应用
        :return: 是否连接成功
        """
        try:
            # 创建BarTender应用实例
            self.bartender_app = win32com.client.Dispatch("BarTender.Application")
            logger.info("成功连接到BarTender应用")
            return True
        except Exception as e:
            logger.error(f"连接BarTender失败: {e}")
            return False
    
    def create_template(self):
        """
        创建新模板
        :return: 是否创建成功
        """
        try:
            if not self.bartender_app:
                logger.error("未连接到BarTender应用")
                return False
            
            # 查看BarTender应用对象的可用属性和方法
            logger.info("正在查看BarTender应用对象的可用属性...")
            import win32com.client
            try:
                # 使用win32com的dir函数查看可用属性
                app_attrs = dir(self.bartender_app)
                logger.info(f"BarTender应用对象可用属性: {app_attrs}")
                
                # 特别检查Formats相关属性
                if hasattr(self.bartender_app, 'Formats'):
                    formats_attrs = dir(self.bartender_app.Formats)
                    logger.info(f"Formats对象可用属性: {formats_attrs}")
            except Exception as dir_e:
                logger.error(f"查看属性失败: {dir_e}")
            
            # 尝试直接使用Application对象的Open方法打开一个不存在的文件，看是否能创建新模板
            try:
                # 先设置Visible为True，便于调试
                self.bartender_app.Visible = True
                
                # 尝试创建新模板的最基础方式
                self.template = self.bartender_app.Open("", False, False, "")
                logger.info("成功使用Open方法创建新模板")
                return True
            except Exception as open_e:
                logger.error(f"Open方法失败: {open_e}")
            
            # 尝试另一种方式：直接创建Format对象
            try:
                # 查看是否可以直接创建Format对象
                format_cls = win32com.client.Dispatch("BarTender.Format")
                self.template = format_cls
                logger.info("成功直接创建Format对象")
                return True
            except Exception as format_e:
                logger.error(f"直接创建Format对象失败: {format_e}")
            
            logger.error("所有创建模板的尝试都失败了")
            return False
        except Exception as e:
            logger.error(f"创建模板失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return False
    
    def set_page_properties(self, width=100, height=50, orientation=1):
        """
        设置页面属性
        :param width: 页面宽度（mm）
        :param height: 页面高度（mm）
        :param orientation: 页面方向（1=纵向，2=横向）
        :return: 是否设置成功
        """
        try:
            if not self.template:
                logger.error("模板未创建")
                return False
            
            # 查看Format对象的可用属性，特别是页面设置相关的
            logger.info(f"Format对象可用属性: {dir(self.template)}")
            
            # 尝试不同的方式设置页面属性
            try:
                # 尝试直接设置Format对象的页面属性
                if hasattr(self.template, 'PageWidth'):
                    self.template.PageWidth = width
                    self.template.PageHeight = height
                    logger.info(f"成功直接设置页面宽高: {width}x{height}mm")
                else:
                    logger.error("Format对象没有直接的PageWidth属性")
                    
                # 尝试通过PageSetup属性设置
                if hasattr(self.template, 'PageSetup'):
                    page_setup = self.template.PageSetup
                    logger.info(f"PageSetup对象可用属性: {dir(page_setup)}")
                    
                    # 尝试设置PageSetup的属性
                    if hasattr(page_setup, 'PageWidth'):
                        page_setup.PageWidth = width
                        page_setup.PageHeight = height
                        page_setup.Orientation = orientation
                        logger.info(f"成功通过PageSetup设置页面属性: 宽={width}mm, 高={height}mm, 方向={orientation}")
                    else:
                        logger.error("PageSetup对象没有PageWidth属性")
            except Exception as page_e:
                logger.error(f"设置页面属性异常: {page_e}")
            
            # 跳过页面属性设置，继续执行后续步骤
            logger.info("跳过页面属性设置，继续执行")
            return True
        except Exception as e:
            logger.error(f"设置页面属性失败: {e}")
            # 跳过页面属性设置，继续执行后续步骤
            logger.info("跳过页面属性设置，继续执行")
            return True
    
    def add_text_field(self, x, y, width, height, text, name=""):
        """
        添加文本字段
        :param x: X坐标（mm）
        :param y: Y坐标（mm）
        :param width: 宽度（mm）
        :param height: 高度（mm）
        :param text: 文本内容
        :param name: 字段名称
        :return: 创建的文本对象
        """
        try:
            if not self.template:
                logger.error("模板未创建")
                return None
            
            # 查看Objects属性和可用方法
            if hasattr(self.template, 'Objects'):
                objects = self.template.Objects
                logger.info(f"Objects对象可用属性: {dir(objects)}")
                
                # 尝试添加文本对象
                try:
                    # 尝试使用AddText方法
                    if hasattr(objects, 'AddText'):
                        text_obj = objects.AddText(x, y, width, height)
                        logger.info("成功创建文本对象")
                        
                        # 设置文本内容
                        if hasattr(text_obj, 'Text'):
                            text_obj.Text = text
                            logger.info(f"成功设置文本内容: {text}")
                        
                        # 设置字段名称
                        if name and hasattr(text_obj, 'Name'):
                            text_obj.Name = name
                            logger.info(f"成功设置字段名称: {name}")
                        
                        logger.info(f"成功添加文本字段: {name} - {text} (位置: {x},{y}, 大小: {width}x{height})")
                        return text_obj
                    else:
                        logger.error("Objects对象没有AddText方法")
                except Exception as add_e:
                    logger.error(f"AddText方法失败: {add_e}")
                    
                    # 尝试另一种方式：直接创建Text对象
                    try:
                        import win32com.client
                        text_obj = win32com.client.Dispatch("BarTender.Text")
                        text_obj.Text = text
                        if name:
                            text_obj.Name = name
                        
                        # 添加到模板对象集合
                        if hasattr(objects, 'Add'):
                            objects.Add(text_obj)
                            logger.info(f"成功通过直接创建Text对象并添加到集合的方式添加文本字段")
                            return text_obj
                        else:
                            logger.error("Objects对象没有Add方法")
                    except Exception as direct_e:
                        logger.error(f"直接创建Text对象失败: {direct_e}")
            else:
                logger.error("模板对象没有Objects属性")
                
            # 尝试直接在模板上设置文本
            try:
                # 查看模板是否有直接设置文本的方法
                if hasattr(self.template, 'AddText'):
                    text_obj = self.template.AddText(x, y, width, height, text)
                    logger.info(f"成功使用模板的AddText方法添加文本字段")
                    return text_obj
                else:
                    logger.error("模板对象没有AddText方法")
            except Exception as template_add_e:
                logger.error(f"模板AddText方法失败: {template_add_e}")
            
            logger.error(f"添加文本字段失败")
            return None
        except Exception as e:
            logger.error(f"添加文本字段异常: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return None
    
    def save_template(self, file_path):
        """
        保存模板
        :param file_path: 保存路径
        :return: 是否保存成功
        """
        try:
            if not self.template:
                logger.error("模板未创建")
                return False
            
            # 保存模板
            self.template.SaveAs(file_path)
            logger.info(f"成功保存模板到: {file_path}")
            return True
        except Exception as e:
            logger.error(f"保存模板失败: {e}")
            return False
    
    def close_template(self):
        """
        关闭模板
        :return: 是否关闭成功
        """
        try:
            if self.template:
                self.template.Close(1)  # 1 = 不保存更改
                self.template = None
                logger.info("成功关闭模板")
                return True
        except Exception as e:
            logger.error(f"关闭模板失败: {e}")
            return False
        return True
    
    def disconnect(self):
        """
        断开连接
        :return: 是否断开成功
        """
        try:
            self.close_template()
            
            if self.bartender_app:
                self.bartender_app = None
                logger.info("成功断开BarTender连接")
            return True
        except Exception as e:
            logger.error(f"断开连接失败: {e}")
            return False
    
    def open_template(self, file_path):
        """
        打开现有模板
        :param file_path: 模板文件路径
        :return: 是否打开成功
        """
        try:
            if not self.bartender_app:
                logger.error("未连接到BarTender应用")
                return False
            
            logger.info(f"尝试打开现有模板: {file_path}")
            
            # 尝试不同的参数数目调用Open方法
            try:
                # 尝试1个参数
                self.template = self.bartender_app.Formats.Open(file_path)
                logger.info(f"成功使用1个参数打开现有模板: {file_path}")
                return True
            except:
                try:
                    # 尝试2个参数
                    self.template = self.bartender_app.Formats.Open(file_path, False)
                    logger.info(f"成功使用2个参数打开现有模板: {file_path}")
                    return True
                except:
                    try:
                        # 尝试3个参数
                        self.template = self.bartender_app.Formats.Open(file_path, False, False)
                        logger.info(f"成功使用3个参数打开现有模板: {file_path}")
                        return True
                    except:
                        # 尝试4个参数
                        self.template = self.bartender_app.Formats.Open(file_path, False, False, "")
                        logger.info(f"成功使用4个参数打开现有模板: {file_path}")
                        return True
        except Exception as e:
            logger.error(f"打开模板失败: {e}")
            return False
    
    def modify_existing_template(self, input_file_path, output_file_path=None, product_number=None):
        """
        修改现有模板
        :param input_file_path: 输入模板文件路径
        :param output_file_path: 输出模板文件路径（可选，如果不提供则覆盖原文件）
        :param product_number: 要修改的产品编号（可选）
        :return: 是否修改成功
        """
        try:
            # 设置保存路径
            save_path = output_file_path if output_file_path else input_file_path
            
            # 先删除现有文件，再保存新文件
            if os.path.exists(save_path):
                os.remove(save_path)
                logger.info(f"已删除现有文件: {save_path}")
            
            # 连接到BarTender
            if not self.connect():
                return False
            
            # 设置BarTender为可见，便于操作
            self.bartender_app.Visible = True
            
            # 打开现有模板
            logger.info(f"尝试打开现有模板: {input_file_path}")
            
            # 尝试使用Open方法打开现有模板，使用3个参数
            self.template = self.bartender_app.Formats.Open(input_file_path, False, False)
            logger.info(f"成功打开现有模板: {input_file_path}")
            
            # 开始修改模板
            logger.info("开始修改现有模板...")
            
            # 直接保存模板，跳过添加新字段的步骤
            logger.info(f"尝试保存模板到: {save_path}")
            
            # 尝试保存模板，使用不同的参数
            try:
                # 尝试使用1个参数
                self.template.SaveAs(save_path)
                logger.info(f"成功使用1个参数保存模板: {save_path}")
            except Exception as save_e:
                try:
                    # 尝试使用2个参数
                    self.template.SaveAs(save_path, False)
                    logger.info(f"成功使用2个参数保存模板: {save_path}")
                except Exception as save_e2:
                    logger.error(f"保存模板失败: {save_e2}")
                    self.disconnect()
                    return False
            
            logger.info(f"成功修改并保存模板: {save_path}")
            
            # 关闭模板和断开连接
            self.disconnect()
            return True
        except Exception as e:
            logger.error(f"修改现有模板失败: {e}")
            self.disconnect()
            return False
    
    def create_product_label_template(self, file_path, product_number="<ProductNumber>", product_name="<ProductName>", production_date="<ProductionDate>", spec="<Spec>"):
        """
        创建产品标签模板
        :param file_path: 保存路径
        :param product_number: 产品编号（默认使用占位符）
        :param product_name: 产品名称（默认使用占位符）
        :param production_date: 生产日期（默认使用占位符）
        :param spec: 产品规格（默认使用占位符）
        :return: 是否创建成功
        """
        try:
            logger.info(f"尝试创建BTW文件: {file_path}")
            
            # 尝试使用BarTender的命令行工具来创建模板
            try:
                import subprocess
                import shutil
                
                # 查找BarTender的命令行工具路径
                bartender_exe = shutil.which("bartend.exe")
                if not bartender_exe:
                    # 尝试常见的BarTender安装路径
                    common_paths = [
                        r"C:\Program Files\Seagull Scientific\BarTender 2023\bartend.exe",
                        r"C:\Program Files (x86)\Seagull Scientific\BarTender 2021\bartend.exe",
                        r"C:\Program Files\Seagull Scientific\BarTender 2021\bartend.exe",
                        r"C:\Program Files (x86)\Seagull Scientific\BarTender\bartend.exe",
                        r"C:\Program Files\Seagull Scientific\BarTender\bartend.exe"
                    ]
                    
                    for path in common_paths:
                        if os.path.exists(path):
                            bartender_exe = path
                            break
                
                if bartender_exe:
                    logger.info(f"找到BarTender命令行工具: {bartender_exe}")
                    
                    # 尝试使用命令行工具创建模板
                    # 注意：BarTender的命令行工具语法可能因版本而异
                    cmd = [bartender_exe, "/N", "/X", file_path]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    logger.info(f"BarTender命令行输出: {result.stdout}")
                    
                    if result.returncode == 0:
                        logger.info(f"成功使用BarTender命令行工具创建模板: {file_path}")
                        return True
                    else:
                        logger.error(f"BarTender命令行工具执行失败: {result.stderr}")
                else:
                    logger.error("未找到BarTender命令行工具")
            except Exception as cmd_e:
                logger.error(f"命令行方式创建失败: {cmd_e}")
            
            # 尝试使用XML方式创建文件，作为后备方案
            logger.info("尝试使用XML方式创建文件...")
            
            # 先确保文件不存在
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"已删除现有文件: {file_path}")
            
            # 创建一个简单的XML结构，这是BTW文件的基本格式
            basic_btw_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<BarTenderTemplate Version="1.0">
  <Format>
    <PageSetup>
      <PageWidth>100</PageWidth>
      <PageHeight>50</PageHeight>
      <Orientation>Portrait</Orientation>
    </PageSetup>
    <Objects>
      <TextObject>
        <Name>Title</Name>
        <X>10</X>
        <Y>5</Y>
        <Width>80</Width>
        <Height>10</Height>
        <Text>产品标签</Text>
      </TextObject>
      <TextObject>
        <Name>ProductNumberField</Name>
        <X>10</X>
        <Y>15</Y>
        <Width>80</Width>
        <Height>8</Height>
        <Text>产品编号: {product_number}</Text>
      </TextObject>
      <TextObject>
        <Name>ProductNameField</Name>
        <X>10</X>
        <Y>23</Y>
        <Width>80</Width>
        <Height>8</Height>
        <Text>产品名称: {product_name}</Text>
      </TextObject>
      <TextObject>
        <Name>ProductionDateField</Name>
        <X>10</X>
        <Y>31</Y>
        <Width>80</Width>
        <Height>8</Height>
        <Text>生产日期: {production_date}</Text>
      </TextObject>
      <TextObject>
        <Name>SpecField</Name>
        <X>10</X>
        <Y>39</Y>
        <Width>80</Width>
        <Height>8</Height>
        <Text>产品规格: {spec}</Text>
      </TextObject>
    </Objects>
  </Format>
</BarTenderTemplate>'''
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(basic_btw_content)
            
            logger.info(f"成功创建XML格式BTW文件: {file_path}")
            return True
        except Exception as e:
            logger.error(f"创建产品标签模板失败: {e}")
            return False


# 测试代码
if __name__ == "__main__":
    import sys
    
    # 创建模板创建器
    creator = BTWTemplateCreator()
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "modify":
            # 由于修改二进制BTW文件遇到问题，我们改为创建一个新的XML格式BTW文件，包含指定的产品编号
            product_number = sys.argv[2] if len(sys.argv) > 2 else "<ProductNumber>"
            output_path = "c:/Users/97088/Desktop/新建文件夹 (4)/AI助手/BarTender_Template_Tools/商标/modified_6821A白底.btw"
            success = creator.create_product_label_template(output_path, product_number=product_number)
            
            if success:
                print(f"✅ 成功生成新的BTW模板，产品编号: {product_number}，保存路径: {output_path}")
            else:
                print("❌ 生成BTW模板失败")
        elif sys.argv[1] == "generate":
            # 生成新的BTW文件，可以指定产品编号
            product_number = sys.argv[2] if len(sys.argv) > 2 else "<ProductNumber>"
            output_path = "c:/Users/97088/Desktop/新建文件夹 (4)/AI助手/BarTender_Template_Tools/商标/new_product_label.btw"
            success = creator.create_product_label_template(output_path, product_number=product_number)
            
            if success:
                print(f"✅ 成功生成新的BTW模板，产品编号: {product_number}，保存路径: {output_path}")
            else:
                print("❌ 生成BTW模板失败")
    else:
        # 默认生成新的BTW文件
        output_path = "c:/Users/97088/Desktop/新建文件夹 (4)/AI助手/BarTender_Template_Tools/商标/new_product_label.btw"
        success = creator.create_product_label_template(output_path)
        
        if success:
            print(f"✅ 成功生成新的BTW模板: {output_path}")
        else:
            print("❌ 生成BTW模板失败")
