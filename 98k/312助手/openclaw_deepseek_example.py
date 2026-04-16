"""
OpenClaw + DeepSeek 集成示例

这个文件展示了如何在 OpenClaw 中使用 DeepSeek MCP Server
"""

import requests
import json

# DeepSeek MCP Server 地址
DEEPSEEK_SERVER = "http://127.0.0.1:5001"

# OpenClaw Gateway 地址
OPENCLAW_GATEWAY = "ws://127.0.0.1:18789"


class DeepSeekClient:
    """DeepSeek API 客户端 - 用于 OpenClaw 集成"""
    
    def __init__(self, base_url=DEEPSEEK_SERVER):
        self.base_url = base_url
        self.session = requests.Session()
    
    def chat(self, message, use_tools=True, conversation_id="default"):
        """
        发送消息到 DeepSeek
        
        Args:
            message: 用户消息
            use_tools: 是否使用工具
            conversation_id: 会话 ID
        
        Returns:
            dict: AI 回复
        """
        try:
            response = self.session.post(
                f"{self.base_url}/chat",
                json={
                    "message": message,
                    "use_tools": use_tools,
                    "conversation_id": conversation_id
                },
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": f"服务器错误：{response.status_code}",
                    "reply": "抱歉，服务器出现错误"
                }
                
        except requests.exceptions.Timeout:
            return {
                "error": "请求超时",
                "reply": "抱歉，请求超时，请重试"
            }
        except Exception as e:
            return {
                "error": str(e),
                "reply": "抱歉，出现未知错误"
            }
    
    def get_customers(self):
        """获取客户列表"""
        return self._call_tool("get_customers", {})
    
    def search_products(self, keyword):
        """搜索产品"""
        return self._call_tool("search_products", {"keyword": keyword})
    
    def get_shipments(self, customer_name=None):
        """查询出货单"""
        return self._call_tool("get_shipments", {"customer_name": customer_name})
    
    def read_excel(self, file_path, sheet_name=None):
        """读取 Excel 文件"""
        return self._call_tool("read_excel", {
            "file_path": file_path,
            "sheet_name": sheet_name
        })
    
    def _call_tool(self, tool_name, parameters):
        """调用工具"""
        try:
            response = self.session.post(
                f"{self.base_url}/tools/{tool_name}",
                json={"parameters": parameters},
                timeout=30
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def health_check(self):
        """健康检查"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False


# ==================== OpenClaw 集成示例 ====================

def openclaw_skill_handler(message):
    """
    OpenClaw 技能处理器
    
    这个函数可以被 OpenClaw 调用，处理用户消息
    
    Args:
        message: 用户消息字符串
    
    Returns:
        str: AI 回复
    """
    client = DeepSeekClient()
    
    # 调用 DeepSeek
    result = client.chat(message, use_tools=True)
    
    # 返回回复
    if "reply" in result:
        return result["reply"]
    else:
        return f"错误：{result.get('error', '未知错误')}"


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("DeepSeek Client 使用示例")
    print("=" * 60)
    
    client = DeepSeekClient()
    
    # 示例 1：健康检查
    print("\n1. 健康检查")
    if client.health_check():
        print("✅ DeepSeek 服务器在线")
    else:
        print("❌ DeepSeek 服务器离线")
    
    # 示例 2：简单对话
    print("\n2. 简单对话")
    result = client.chat("你好，请介绍一下你自己", use_tools=False)
    print(f"回复：{result.get('reply', 'N/A')}")
    
    # 示例 3：查询客户
    print("\n3. 查询客户列表")
    result = client.get_customers()
    if "result" in result:
        customers = result["result"].get("customers", [])
        print(f"找到 {len(customers)} 个客户:")
        for customer in customers:
            print(f"  - {customer.get('name', 'N/A')}")
    
    # 示例 4：搜索产品
    print("\n4. 搜索产品")
    result = client.search_products("A001")
    if "result" in result:
        products = result["result"].get("products", [])
        print(f"找到 {len(products)} 个产品:")
        for product in products:
            print(f"  - {product.get('name', 'N/A')} ({product.get('model', 'N/A')})")
    
    # 示例 5：智能对话（带工具）
    print("\n5. 智能对话（带工具）")
    result = client.chat("帮我查询一下有哪些客户", use_tools=True)
    print(f"回复：{result.get('reply', 'N/A')}")
    
    print("\n" + "=" * 60)
    print("示例结束")
    print("=" * 60)


# ==================== OpenClaw Canvas 配置示例 ====================

"""
在 OpenClaw Canvas 中配置 DeepSeek 集成：

1. 添加 HTTP Request 节点
   - URL: http://127.0.0.1:5001/chat
   - Method: POST
   - Headers:
     - Content-Type: application/json
   - Body:
     {
       "message": "{{user_input}}",
       "use_tools": true,
       "conversation_id": "{{session_id}}"
     }

2. 添加 JSON Parse 节点
   - 解析 HTTP 响应
   - 提取 reply 字段

3. 添加 Response 节点
   - 返回 AI 回复给用户

完整的 OpenClaw 流程：
用户消息 → HTTP Request → DeepSeek MCP Server → 
DeepSeek API → JSON Parse → Response → 用户
"""


# ==================== 高级用法 ====================

class AdvancedDeepSeekIntegration:
    """
    高级 DeepSeek 集成
    
    提供更丰富的功能和更好的错误处理
    """
    
    def __init__(self):
        self.client = DeepSeekClient()
        self.conversation_history = {}
    
    def chat_with_context(self, user_id, message):
        """
        带上下文的对话
        
        Args:
            user_id: 用户 ID
            message: 用户消息
        
        Returns:
            str: AI 回复
        """
        # 这里可以实现更复杂的上下文管理
        # 目前简化为每次都是新对话
        result = self.client.chat(message, use_tools=True, conversation_id=user_id)
        return result.get('reply', '抱歉，我无法回复')
    
    def query_data(self, query_type, **params):
        """
        查询数据
        
        Args:
            query_type: 查询类型 (customers, products, shipments)
            params: 查询参数
        
        Returns:
            dict: 查询结果
        """
        if query_type == "customers":
            return self.client.get_customers()
        elif query_type == "products":
            return self.client.search_products(params.get("keyword", ""))
        elif query_type == "shipments":
            return self.client.get_shipments(params.get("customer_name"))
        else:
            return {"error": f"未知查询类型：{query_type}"}
    
    def process_excel(self, file_path, analysis_type="summary"):
        """
        处理 Excel 文件
        
        Args:
            file_path: Excel 文件路径
            analysis_type: 分析类型
        
        Returns:
            dict: 分析结果
        """
        result = self.client.read_excel(file_path)
        
        if "error" in result:
            return result
        
        # 这里可以添加更多的分析逻辑
        # 目前直接返回 Excel 数据
        return result


# 测试高级集成
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("高级集成示例")
    print("=" * 60)
    
    integration = AdvancedDeepSeekIntegration()
    
    # 示例：查询数据
    print("\n查询客户数据:")
    result = integration.query_data("customers")
    print(f"结果：{json.dumps(result, ensure_ascii=False, indent=2)}")
