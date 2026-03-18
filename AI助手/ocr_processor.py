# OCR处理器模块 - 使用硅基流动视觉大模型API
import os
import base64
import logging
import re
import requests

logger = logging.getLogger(__name__)

class OCRProcessor:
    """OCR处理器 - 使用硅基流动视觉大模型API"""

    def __init__(self):
        # 硅基流动API配置
        # 请从环境变量 SILICON_API_KEY 获取或使用自己的API Key
        self.api_key = os.environ.get("SILICON_API_KEY", "your-api-key-here")
        self.base_url = "https://api.siliconflow.cn/v1"
        self.model = "Qwen/Qwen2.5-VL-72B-Instruct"  # 72B参数视觉大模型，性能更强
        
    def process_image(self, image_path):
        """处理图片并提取文本"""
        try:
            logger.info(f"开始处理图片: {image_path}")

            # 读取图片并转换为base64
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            # 构建prompt
            prompt = """请识别这张销售合同图片中的信息，提取以下内容：
1. 客户名称（在"客户"或"MESSRS"后面的手写文字）
2. 产品列表，每个产品包含：
   - 产品名称（品名列的手写文字）
   - 规格（规格列的数字）
   - 数量（数量列的数字）

请按以下JSON格式返回：
{
  "customer": "客户名称",
  "products": [
    {"name": "产品1名称", "spec": "规格1", "quantity": "数量1"},
    {"name": "产品2名称", "spec": "规格2", "quantity": "数量2"}
  ]
}

只返回JSON，不要其他说明。"""

            # 调用硅基流动API
            result = self.call_vision_api(image_data, prompt)
            
            logger.info(f"API返回结果: {result}")
            
            # 解析结果
            parsed_result = self.parse_api_response(result)
            
            logger.info(f"解析结果: {parsed_result}")
            return parsed_result

        except Exception as e:
            logger.error(f"OCR处理失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            # 返回空结果而不是抛出异常
            return {"customer": "", "products": []}

    def call_vision_api(self, image_base64, prompt):
        """调用硅基流动视觉API"""
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            "temperature": 0.3,
            "max_tokens": 2048,
            "stream": False
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            
            if 'choices' in data and len(data['choices']) > 0:
                return data['choices'][0]['message']['content']
            else:
                logger.error(f"API返回格式错误: {data}")
                return ""
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API请求失败: {e}")
            raise

    def parse_api_response(self, response_text):
        """解析API返回的文本"""
        result = {
            "customer": "",
            "products": []
        }
        
        if not response_text:
            return result
        
        try:
            # 尝试提取JSON部分
            # 查找JSON代码块
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析整个文本
                json_str = response_text
            
            # 清理文本
            json_str = json_str.strip()
            
            # 解析JSON
            import json
            data = json.loads(json_str)
            
            if 'customer' in data:
                result['customer'] = data['customer']
            
            if 'products' in data and isinstance(data['products'], list):
                result['products'] = data['products']
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            logger.error(f"原始文本: {response_text}")
        except Exception as e:
            logger.error(f"解析失败: {e}")
        
        return result
