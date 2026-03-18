# 屏幕捕获模块
import os
import time
import numpy as np
from typing import Optional, Tuple, List
from PIL import Image, ImageGrab
import logging
import threading
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ScreenCaptor:
    """屏幕捕获器"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.capture_area = self.config.get("screen_capture_area", (0, 0, 1920, 1080))
        self.screenshot_dir = Path("screenshots")
        self.screenshot_dir.mkdir(exist_ok=True)
        self.last_screenshot: Optional[Image.Image] = None
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.frame_count = 0
        self._lock = threading.Lock()

    def capture(self, area: Tuple[int, int, int, int] = None) -> Optional[np.ndarray]:
        """
        捕获屏幕图像

        Args:
            area: 可选的区域 (x1, y1, x2, y2)

        Returns:
            numpy数组格式的图像，失败返回None
        """
        try:
            if area is None:
                area = self.capture_area

            # 截取屏幕
            screenshot = ImageGrab.grab(bbox=area)

            # 转换为numpy数组
            img_array = np.array(screenshot)

            # 保存最近一次截图
            with self._lock:
                self.last_screenshot = screenshot

            self.frame_count += 1
            return img_array

        except Exception as e:
            logger.error(f"屏幕截取失败: {e}")
            return None

    def capture_pil(self, area: Tuple[int, int, int, int] = None) -> Optional[Image.Image]:
        """捕获屏幕并返回PIL图像"""
        try:
            if area is None:
                area = self.capture_area

            screenshot = ImageGrab.grab(bbox=area)
            with self._lock:
                self.last_screenshot = screenshot
            return screenshot

        except Exception as e:
            logger.error(f"屏幕截取失败: {e}")
            return None

    def capture_and_save(self, filename: str = None, area: Tuple[int, int, int, int] = None) -> Optional[str]:
        """捕获屏幕并保存到文件"""
        try:
            screenshot = self.capture_pil(area)
            if screenshot is None:
                return None

            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                filename = f"screenshot_{timestamp}.png"

            filepath = self.screenshot_dir / filename
            screenshot.save(str(filepath))
            logger.info(f"截图已保存: {filepath}")

            return str(filepath)

        except Exception as e:
            logger.error(f"截图保存失败: {e}")
            return None

    def get_diff(self, old_screenshot: np.ndarray, new_screenshot: np.ndarray,
                 threshold: int = 30) -> float:
        """
        计算两帧图像的差异

        Args:
            old_screenshot: 旧图像
            new_screenshot: 新图像
            threshold: 差异阈值

        Returns:
            差异比例 (0.0 - 1.0)
        """
        try:
            if old_screenshot.shape != new_screenshot.shape:
                return 1.0

            # 计算差异
            diff = np.abs(old_screenshot.astype(np.int32) - new_screenshot.astype(np.int32))
            diff_mask = diff > threshold
            diff_ratio = np.sum(diff_mask) / diff.size

            return diff_ratio

        except Exception as e:
            logger.error(f"差异计算失败: {e}")
            return 1.0

    def detect_changes(self, threshold: float = 0.01) -> bool:
        """检测屏幕是否有变化"""
        try:
            new_screenshot = self.capture()
            if new_screenshot is None:
                return False

            if self.last_screenshot is None:
                self.last_screenshot = new_screenshot
                return True

            # 转换last_screenshot为numpy数组
            last_array = np.array(self.last_screenshot)

            diff_ratio = self.get_diff(last_array, new_screenshot)
            has_change = diff_ratio > threshold

            if has_change:
                self.last_screenshot = Image.fromarray(new_screenshot)

            return has_change

        except Exception as e:
            logger.error(f"变化检测失败: {e}")
            return False

    def start_monitoring(self, callback: callable, interval: float = 1.0):
        """开始持续监控"""
        if self.is_monitoring:
            logger.warning("监控已在进行中")
            return

        self.is_monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(callback, interval),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"开始屏幕监控，间隔: {interval}秒")

    def _monitor_loop(self, callback: callable, interval: float):
        """监控循环"""
        while self.is_monitoring:
            try:
                screenshot = self.capture()
                if screenshot is not None:
                    callback(screenshot)
            except Exception as e:
                logger.error(f"监控回调失败: {e}")

            time.sleep(interval)

    def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("屏幕监控已停止")

    def capture_region(self, x: int, y: int, width: int, height: int) -> Optional[np.ndarray]:
        """捕获指定区域"""
        area = (x, y, x + width, y + height)
        return self.capture(area)

    def get_display_info(self) -> dict:
        """获取显示信息"""
        try:
            import screeninfo
            monitors = screeninfo.get_monitors()

            return {
                "monitor_count": len(monitors),
                "monitors": [
                    {
                        "name": m.name,
                        "width": m.width,
                        "height": m.height,
                        "x": m.x,
                        "y": m.y
                    }
                    for m in monitors
                ]
            }

        except ImportError:
            logger.warning("screeninfo模块未安装，使用默认显示信息")
            return {
                "monitor_count": 1,
                "monitors": [{"name": "primary", "width": 1920, "height": 1080, "x": 0, "y": 0}]
            }

        except Exception as e:
            logger.error(f"获取显示信息失败: {e}")
            return {"monitor_count": 0, "monitors": []}


class RegionMatcher:
    """区域匹配器 - 用于检测特定区域的内容变化"""

    def __init__(self):
        self.templates: dict = {}

    def add_template(self, name: str, template: np.ndarray):
        """添加模板"""
        self.templates[name] = template

    def find_regions(self, screenshot: np.ndarray, threshold: float = 0.8) -> List[dict]:
        """
        在截图中查找匹配区域

        Returns:
            匹配区域列表，每个元素包含位置和置信度
        """
        results = []

        try:
            import cv2

            gray_screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

            for name, template in self.templates.items():
                if len(template.shape) == 3:
                    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                else:
                    template_gray = template

                # 模板匹配
                result = cv2.matchTemplate(gray_screenshot, template_gray, cv2.TM_CCOEFF_NORMED)
                locations = np.where(result >= threshold)

                for y, x in zip(*locations):
                    results.append({
                        "name": name,
                        "x": int(x),
                        "y": int(y),
                        "width": template_gray.shape[1],
                        "height": template_gray.shape[0],
                        "confidence": float(result[y, x])
                    })

        except ImportError:
            logger.warning("OpenCV未安装，无法进行区域匹配")

        return results

    def clear_templates(self):
        """清除所有模板"""
        self.templates.clear()
