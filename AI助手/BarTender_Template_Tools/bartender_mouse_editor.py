#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BarTender 文字位置鼠标编辑器
功能：
1. 从BarTender窗口截图中识别文字位置
2. 提供GUI界面，允许通过鼠标拖放来调整文字位置
3. 生成位置映射文件
"""

import sys
import os
import argparse
import logging
import numpy as np
import cv2
from PIL import Image, ImageGrab, ImageTk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import win32gui
import win32con
import win32api
from typing import Dict, List, Optional, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bartender_mouse_editor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BarTenderWindowRecognizer:
    """BarTender 窗口识别器"""
    
    def __init__(self):
        self.bartend_class = "BarTender10x"  # BarTender 窗口类名
        self.bartend_title = "BarTender"
    
    def find_bartender_windows(self) -> List[Dict]:
        """查找所有 BarTender 窗口"""
        windows = []
        
        def enum_callback(hwnd, windows_list):
            if win32gui.IsWindowVisible(hwnd):
                class_name = win32gui.GetClassName(hwnd)
                title = win32gui.GetWindowText(hwnd)
                
                # 检查是否是 BarTender 窗口
                if 'bartend' in class_name.lower() or 'BarTender' in title:
                    rect = win32gui.GetWindowRect(hwnd)
                    window_info = {
                        'hwnd': hwnd,
                        'title': title,
                        'class': class_name,
                        'left': rect[0],
                        'top': rect[1],
                        'right': rect[2],
                        'bottom': rect[3],
                        'width': rect[2] - rect[0],
                        'height': rect[3] - rect[1]
                    }
                    windows_list.append(window_info)
            
            return True
        
        win32gui.EnumWindows(enum_callback, windows)
        logger.info(f"找到 {len(windows)} 个 BarTender 窗口")
        return windows
    
    def capture_window(self, hwnd: int) -> Image.Image:
        """截取窗口内容"""
        try:
            # 获取窗口位置
            rect = win32gui.GetWindowRect(hwnd)
            
            # 使用 ImageGrab 截取窗口
            img = ImageGrab.grab(rect)
            logger.info(f"成功截取窗口，尺寸: {img.size}")
            return img
            
        except Exception as e:
            logger.error(f"截取窗口失败: {str(e)}")
            raise Exception(f"截取窗口失败: {str(e)}")

class TextPositionEditor:
    """文字位置编辑器"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("BarTender 文字位置编辑器")
        self.root.geometry("1000x800")
        
        # 初始化数据
        self.image = None
        self.image_tk = None
        self.text_items = []
        self.selected_item = None
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.ocr_reader = None
        
        # 初始化OCR
        self.init_ocr()
        
        # 创建菜单
        self.create_menu()
        
        # 创建主框架
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建画布
        self.canvas = tk.Canvas(self.main_frame, bg="white")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 创建滚动条
        self.scroll_x = ttk.Scrollbar(self.main_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.scroll_y = ttk.Scrollbar(self.main_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定滚动条
        self.canvas.config(xscrollcommand=self.scroll_x.set, yscrollcommand=self.scroll_y.set)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        
        # 创建右侧面板
        self.right_panel = tk.Frame(self.root, width=250, bg="#f0f0f0")
        self.right_panel.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建文字列表
        self.create_text_list()
        
        # 创建控制按钮
        self.create_control_buttons()
        
        # 绑定鼠标事件
        self.canvas.bind("<Button-1>", self.on_mouse_click)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        
        # BarTender 窗口识别器
        self.window_recognizer = BarTenderWindowRecognizer()
    
    def create_menu(self):
        """创建菜单"""
        menubar = tk.Menu(self.root)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="从BarTender窗口截图", command=self.capture_from_window)
        file_menu.add_command(label="打开图片文件", command=self.open_image_file)
        file_menu.add_command(label="保存位置映射", command=self.save_position_map)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        menubar.add_cascade(label="文件", menu=file_menu)
        
        # 编辑菜单
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="清空所有文字", command=self.clear_all_text)
        edit_menu.add_command(label="刷新文字识别", command=self.refresh_text_recognition)
        menubar.add_cascade(label="编辑", menu=edit_menu)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="关于", command=self.show_about)
        menubar.add_cascade(label="帮助", menu=help_menu)
        
        self.root.config(menu=menubar)
    
    def create_text_list(self):
        """创建文字列表"""
        tk.Label(self.right_panel, text="文字列表", bg="#f0f0f0", font=("Arial", 12, "bold")).pack(pady=10)
        
        self.text_listbox = tk.Listbox(self.right_panel, height=20)
        self.text_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.text_listbox.bind("<<ListboxSelect>>", self.on_text_select)
    
    def init_ocr(self):
        """初始化OCR识别器"""
        try:
            import easyocr
            self.ocr_reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
            logger.info("OCR识别器初始化成功")
        except Exception as e:
            logger.error(f"OCR识别器初始化失败: {str(e)}")
            messagebox.showwarning("警告", f"OCR初始化失败: {str(e)}")
            self.ocr_reader = None
    
    def create_control_buttons(self):
        """创建控制按钮"""
        # 添加文字按钮
        tk.Button(self.right_panel, text="添加文字", command=self.add_text).pack(fill=tk.X, padx=10, pady=5)
        
        # 删除文字按钮
        tk.Button(self.right_panel, text="删除选中文字", command=self.delete_selected_text).pack(fill=tk.X, padx=10, pady=5)
        
        # 刷新按钮
        tk.Button(self.right_panel, text="刷新界面", command=self.refresh_canvas).pack(fill=tk.X, padx=10, pady=5)
        
        # 保存按钮
        tk.Button(self.right_panel, text="保存位置", command=self.save_position_map).pack(fill=tk.X, padx=10, pady=20, ipady=5)
        
        # 修改文字内容按钮
        tk.Button(self.right_panel, text="修改文字内容", command=self.edit_selected_text).pack(fill=tk.X, padx=10, pady=5)
    
    def capture_from_window(self):
        """从BarTender窗口截图"""
        windows = self.window_recognizer.find_bartender_windows()
        
        if not windows:
            messagebox.showwarning("警告", "未找到BarTender窗口")
            return
        
        # 选择第一个窗口
        window = windows[0]
        try:
            self.image = self.window_recognizer.capture_window(window['hwnd'])
            self.display_image()
            self.recognize_text()
            messagebox.showinfo("成功", f"已从窗口 '{window['title']}' 截图")
        except Exception as e:
            messagebox.showerror("错误", f"截图失败: {str(e)}")
    
    def open_image_file(self):
        """打开图片文件"""
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp"), ("All files", "*.*")]
        )
        if file_path:
            try:
                self.image = Image.open(file_path)
                self.display_image()
                self.recognize_text()
            except Exception as e:
                messagebox.showerror("错误", f"打开图片失败: {str(e)}")
    
    def display_image(self):
        """显示图片"""
        if not self.image:
            return
        
        # 调整图片大小以适应窗口
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        img_width, img_height = self.image.size
        scale = min(canvas_width / img_width, canvas_height / img_height, 1.0)
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        resized_image = self.image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        self.image_tk = ImageTk.PhotoImage(resized_image)
        
        # 清除画布
        self.canvas.delete("all")
        
        # 显示图片
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.image_tk)
        
        # 设置画布滚动区域
        self.canvas.config(scrollregion=(0, 0, new_width, new_height))
    
    def recognize_text(self):
        """使用OCR识别文字"""
        if not self.image:
            return
        
        if not self.ocr_reader:
            logger.warning("OCR识别器未初始化，使用模拟数据")
            # 使用模拟数据作为备选
            self.text_items = [
                {
                    'id': 1,
                    'text': '3712',
                    'x': 100,
                    'y': 100,
                    'width': 100,
                    'height': 40,
                    'color': '#000000',
                    'font': 'Arial',
                    'font_size': 16
                },
                {
                    'id': 2,
                    'text': '产品名称：6821A白底',
                    'x': 100,
                    'y': 150,
                    'width': 200,
                    'height': 30,
                    'color': '#000000',
                    'font': 'Arial',
                    'font_size': 12
                }
            ]
        else:
            try:
                logger.info("正在使用OCR识别文字...")
                # 将PIL图像转换为numpy数组
                img_array = np.array(self.image)
                
                # 使用OCR识别文字
                results = self.ocr_reader.readtext(img_array)
                
                # 处理识别结果
                self.text_items = []
                for i, result in enumerate(results):
                    bbox, text, confidence = result
                    
                    # 过滤低置信度结果
                    if confidence > 0.5:
                        # 计算文字框坐标
                        x1, y1 = int(bbox[0][0]), int(bbox[0][1])
                        x2, y2 = int(bbox[2][0]), int(bbox[2][1])
                        width = x2 - x1
                        height = y2 - y1
                        
                        # 添加文字项
                        self.text_items.append({
                            'id': i + 1,
                            'text': text,
                            'x': x1,
                            'y': y1,
                            'width': width,
                            'height': height,
                            'color': '#000000',
                            'font': 'Arial',
                            'font_size': 12
                        })
                
                logger.info(f"OCR识别完成，识别到 {len(self.text_items)} 个文字项")
            except Exception as e:
                logger.error(f"OCR识别失败: {str(e)}")
                messagebox.showerror("错误", f"OCR识别失败: {str(e)}")
                # 使用模拟数据作为备选
                self.text_items = [
                    {
                        'id': 1,
                        'text': '3712',
                        'x': 100,
                        'y': 100,
                        'width': 100,
                        'height': 40,
                        'color': '#000000',
                        'font': 'Arial',
                        'font_size': 16
                    }
                ]
        
        self.update_text_list()
        self.draw_text_items()
    
    def edit_selected_text(self):
        """修改选中文字的内容"""
        if not self.selected_item:
            messagebox.showwarning("警告", "请先选择要修改的文字")
            return
        
        # 弹出对话框让用户输入新的文字内容
        current_text = self.selected_item['text']
        new_text = tk.simpledialog.askstring(
            "修改文字", 
            "请输入新的文字内容：",
            initialvalue=current_text
        )
        
        if new_text is not None and new_text != current_text:
            # 更新文字内容
            self.selected_item['text'] = new_text
            
            # 更新界面
            self.update_text_list()
            self.refresh_canvas()
            logger.info(f"文字内容已修改：{current_text} -> {new_text}")
    
    def update_text_list(self):
        """更新文字列表"""
        self.text_listbox.delete(0, tk.END)
        for item in self.text_items:
            self.text_listbox.insert(tk.END, f"{item['id']}: {item['text']}")
    
    def draw_text_items(self):
        """绘制文字项"""
        for item in self.text_items:
            self.draw_text_item(item)
    
    def draw_text_item(self, item):
        """绘制单个文字项"""
        # 绘制背景框
        if item == self.selected_item:
            bg_color = "#ffff00"
            border_color = "#ff0000"
        else:
            bg_color = "#ffffff"
            border_color = "#000000"
        
        # 绘制矩形框
        self.canvas.create_rectangle(
            item['x'], item['y'],
            item['x'] + item['width'], item['y'] + item['height'],
            fill=bg_color, outline=border_color, width=2,
            tags=f"text_box_{item['id']}"
        )
        
        # 绘制文字
        self.canvas.create_text(
            item['x'] + 10, item['y'] + 20,
            anchor=tk.W,
            text=item['text'],
            fill=item['color'],
            font=(item['font'], item['font_size']),
            tags=f"text_{item['id']}"
        )
        
        # 绘制拖拽控制点
        handle_size = 8
        self.canvas.create_rectangle(
            item['x'] + item['width'] - handle_size, item['y'] + item['height'] - handle_size,
            item['x'] + item['width'] + handle_size, item['y'] + item['height'] + handle_size,
            fill="#ff0000", outline="#000000", width=2,
            tags=f"handle_{item['id']}"
        )
    
    def on_mouse_click(self, event):
        """鼠标点击事件"""
        # 获取点击位置
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        
        # 检查是否点击了文字项
        self.selected_item = None
        for item in self.text_items:
            # 检查是否点击了文字框
            if (item['x'] <= x <= item['x'] + item['width'] and
                item['y'] <= y <= item['y'] + item['height']):
                self.selected_item = item
                break
        
        # 刷新画布
        self.refresh_canvas()
        
        # 记录拖拽起始位置
        self.drag_start_x = x
        self.drag_start_y = y
        self.dragging = True
    
    def on_mouse_drag(self, event):
        """鼠标拖拽事件"""
        if not self.dragging or not self.selected_item:
            return
        
        # 计算拖拽偏移量
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        delta_x = x - self.drag_start_x
        delta_y = y - self.drag_start_y
        
        # 更新文字位置
        self.selected_item['x'] += delta_x
        self.selected_item['y'] += delta_y
        
        # 刷新画布
        self.refresh_canvas()
        
        # 更新拖拽起始位置
        self.drag_start_x = x
        self.drag_start_y = y
    
    def on_mouse_release(self, event):
        """鼠标释放事件"""
        self.dragging = False
    
    def on_text_select(self, event):
        """文字列表选择事件"""
        selection = self.text_listbox.curselection()
        if selection:
            index = selection[0]
            if 0 <= index < len(self.text_items):
                self.selected_item = self.text_items[index]
                self.refresh_canvas()
    
    def add_text(self):
        """添加文字"""
        if not self.image:
            messagebox.showwarning("警告", "请先打开图片或从窗口截图")
            return
        
        # 弹出对话框让用户输入文字
        text = tk.simpledialog.askstring("添加文字", "请输入文字内容：")
        if text:
            # 创建新文字项
            new_id = max([item['id'] for item in self.text_items]) + 1 if self.text_items else 1
            new_item = {
                'id': new_id,
                'text': text,
                'x': 50,
                'y': 50,
                'width': 200,
                'height': 30,
                'color': '#000000',
                'font': 'Arial',
                'font_size': 12
            }
            
            # 添加到文字列表
            self.text_items.append(new_item)
            self.selected_item = new_item
            
            # 更新界面
            self.update_text_list()
            self.refresh_canvas()
    
    def delete_selected_text(self):
        """删除选中文字"""
        if not self.selected_item:
            messagebox.showwarning("警告", "请先选择要删除的文字")
            return
        
        # 从列表中删除
        self.text_items.remove(self.selected_item)
        self.selected_item = None
        
        # 更新界面
        self.update_text_list()
        self.refresh_canvas()
    
    def clear_all_text(self):
        """清空所有文字"""
        if messagebox.askyesno("确认", "确定要清空所有文字吗？"):
            self.text_items = []
            self.selected_item = None
            self.update_text_list()
            self.refresh_canvas()
    
    def refresh_text_recognition(self):
        """刷新文字识别"""
        if not self.image:
            messagebox.showwarning("警告", "请先打开图片或从窗口截图")
            return
        
        self.recognize_text()
        messagebox.showinfo("成功", "文字识别已刷新")
    
    def refresh_canvas(self):
        """刷新画布"""
        self.display_image()
        self.draw_text_items()
    
    def save_position_map(self):
        """保存位置映射"""
        if not self.text_items:
            messagebox.showwarning("警告", "没有文字项可保存")
            return
        
        # 选择保存路径
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    # 写入表头
                    f.write("ID,文字内容,X坐标,Y坐标,宽度,高度,颜色,字体,字体大小\n")
                    
                    # 写入数据
                    for item in self.text_items:
                        f.write(f"{item['id']},{item['text']},{item['x']},{item['y']},{item['width']},{item['height']},{item['color']},{item['font']},{item['font_size']}\n")
                
                messagebox.showinfo("成功", f"位置映射已保存到 {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {str(e)}")
    
    def on_canvas_configure(self, event):
        """画布配置事件"""
        if self.image:
            self.display_image()
    
    def show_about(self):
        """显示关于信息"""
        messagebox.showinfo(
            "关于",
            "BarTender 文字位置编辑器\n\n" +
            "功能：\n" +
            "1. 从BarTender窗口截图中识别文字位置\n" +
            "2. 提供GUI界面，允许通过鼠标拖放来调整文字位置\n" +
            "3. 生成位置映射文件\n\n" +
            "版本：1.0\n" +
            "作者：AI助手"
        )

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='BarTender 文字位置鼠标编辑器')
    parser.add_argument('--image', type=str, help='输入图片文件路径')
    args = parser.parse_args()
    
    # 创建GUI窗口
    root = tk.Tk()
    editor = TextPositionEditor(root)
    
    # 如果指定了图片文件，直接打开
    if args.image and os.path.exists(args.image):
        try:
            editor.image = Image.open(args.image)
            editor.display_image()
            editor.recognize_text()
        except Exception as e:
            messagebox.showerror("错误", f"打开图片失败: {str(e)}")
    
    # 运行GUI主循环
    root.mainloop()

if __name__ == "__main__":
    main()