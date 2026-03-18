"""
DeepSeek API 配置
请将以下配置修改为您的API密钥
"""

import os

# DeepSeek API 密钥
# 请访问 https://platform.deepseek.com/api-keys 获取您的API密钥
# 建议将API密钥设置为环境变量 DEEPSEEK_API_KEY
deepseek_api_key = os.environ.get('DEEPSEEK_API_KEY', '')
if deepseek_api_key:
    DEEPSEEK_API_KEY = deepseek_api_key
else:
    DEEPSEEK_API_KEY = 'your-api-key-here'  # 请替换为您的API密钥或使用环境变量

# API基础地址（通常不需要修改）
DEEPSEEK_API_BASE = 'https://api.deepseek.com/v1'

# 默认模型
DEEPSEEK_MODEL = 'deepseek-chat'

# 其他配置
ENABLE_AI_FEATURES = True  # 启用AI功能
AI_TEMPERATURE = 0.7       # AI回复的随机性（0-1，越高越有创意）
MAX_TOKENS = 2000          # 最大回复token数

# 配置说明：
# 1. 将 DEEPSEEK_API_KEY 替换为您真实的API密钥
# 2. 保存文件
# 3. 重启服务器
