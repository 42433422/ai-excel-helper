# 工具函数
import os
import logging
import time
from config import LOG_CONFIG

# 设置日志
def setup_logger():
    """设置日志配置"""
    # 创建日志目录
    log_dir = os.path.dirname(LOG_CONFIG["file_path"])
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 配置日志
    logging.basicConfig(
        level=getattr(logging, LOG_CONFIG["level"]),
        format=LOG_CONFIG["format"],
        handlers=[
            logging.FileHandler(LOG_CONFIG["file_path"], encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

# 获取当前时间戳
def get_timestamp():
    """获取当前时间戳"""
    return time.time()

# 格式化时间
def format_time(timestamp=None):
    """格式化时间"""
    if timestamp is None:
        timestamp = get_timestamp()
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))

# 检查文件是否存在
def file_exists(file_path):
    """检查文件是否存在"""
    return os.path.isfile(file_path)

# 检查目录是否存在
def dir_exists(dir_path):
    """检查目录是否存在"""
    return os.path.isdir(dir_path)

# 创建目录
def create_dir(dir_path):
    """创建目录"""
    if not dir_exists(dir_path):
        os.makedirs(dir_path)

# 获取文件名称（不含扩展名）
def get_filename_without_ext(file_path):
    """获取文件名称（不含扩展名）"""
    return os.path.splitext(os.path.basename(file_path))[0]

# 获取文件扩展名
def get_file_extension(file_path):
    """获取文件扩展名"""
    return os.path.splitext(file_path)[1]

# 生成唯一文件名
def generate_unique_filename(prefix="", suffix="", ext=""):
    """生成唯一文件名"""
    timestamp = int(get_timestamp() * 1000)
    filename = f"{prefix}{timestamp}{suffix}{ext if ext else ''}"
    return filename

# 延迟执行
def delay(seconds):
    """延迟执行"""
    time.sleep(seconds)

# 坐标转换
def convert_coordinates(x, y, scale=1.0):
    """坐标转换"""
    return (int(x * scale), int(y * scale))

# 验证坐标是否在指定区域内
def is_coordinate_in_area(x, y, area):
    """验证坐标是否在指定区域内"""
    x1, y1, x2, y2 = area
    return x1 <= x <= x2 and y1 <= y <= y2

# 计算两点之间的距离
def calculate_distance(x1, y1, x2, y2):
    """计算两点之间的距离"""
    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
