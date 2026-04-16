"""
DeepSeek API 配置文件
用于配置 DeepSeek API 的密钥、基础 URL、模型参数等
"""
import os

# DeepSeek API 密钥
# 请访问 https://platform.deepseek.com/api-keys 获取您的 API 密钥
# 建议将 API 密钥设置为环境变量 DEEPSEEK_API_KEY
deepseek_api_key = os.environ.get('DEEPSEEK_API_KEY', '')
if deepseek_api_key:
    DEEPSEEK_API_KEY = deepseek_api_key
else:
    # 如果环境变量未设置，使用默认密钥（不推荐用于生产环境）
    DEEPSEEK_API_KEY = 'sk-5670fc1d73c74f21b4948d7496b7bf16'

# API 基础地址（通常不需要修改）
DEEPSEEK_API_BASE = 'https://api.deepseek.com/v1'

# 默认模型
DEEPSEEK_MODEL = 'deepseek-chat'

# 其他配置
ENABLE_AI_FEATURES = True  # 启用 AI 功能
AI_TEMPERATURE = 0.7       # AI 回复的随机性（0-1，越高越有创意）
MAX_TOKENS = 2000          # 最大回复 token 数
TIMEOUT = 60               # API 请求超时时间（秒）

# OpenClaw 集成配置
OPENCLAW_COMPATIBLE = True  # 启用 OpenClaw 兼容模式
OPENCLAW_API_PORT = 5001    # OpenClaw HTTP API 监听端口
