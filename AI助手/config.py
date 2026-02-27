# 配置文件
import os

# Excel自动化配置
EXCEL_CONFIG = {
    "excel_path": "C:\\Program Files\\Microsoft Office\\root\\Office16\\EXCEL.EXE",  # Excel可执行文件路径
    "save_path": "C:\\Users\\Public\\Documents\\",  # 文件保存路径
    "window_title": "Microsoft Excel",  # Excel窗口标题
    "fixed_position": (100, 100),  # 固定位置坐标（x, y）
    "window_size": (1200, 800),  # 窗口大小（宽度, 高度）
}

# OmniParser配置
OMNIPARSER_CONFIG = {
    "model_path": "./OmniParser/models/omniparser-v2",  # 模型路径
    "confidence_threshold": 0.8,  # 置信度阈值
    "screen_capture_area": (0, 0, 1920, 1080),  # 屏幕捕获区域（x1, y1, x2, y2）
}

# AI模型配置
# 支持的模型：deepseek, openai
AI_CONFIG = {
    "model_name": "deepseek",  # AI模型名称
    "api_key": os.environ.get("DEEPSEEK_API_KEY", "your-api-key-here"),  # 从环境变量获取DeepSeek API密钥
    "base_url": "https://api.deepseek.com/v1",  # DeepSeek API基础URL（包含v1前缀）
    "temperature": 0.7,  # 生成温度
    "max_tokens": 1000,  # 最大生成 tokens
}

# 如果你使用OpenAI模型，请使用以下配置
# AI_CONFIG = {
#     "model_name": "openai",  # AI模型名称
#     "api_key": "sk-xxx",  # OpenAI API密钥
#     "base_url": "https://api.openai.com/v1",  # OpenAI API基础URL
#     "temperature": 0.7,  # 生成温度
#     "max_tokens": 1000,  # 最大生成 tokens
# }

# 日志配置
LOG_CONFIG = {
    "level": "INFO",  # 日志级别
    "file_path": "./logs/ai_excel.log",  # 日志文件路径
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # 日志格式
}
