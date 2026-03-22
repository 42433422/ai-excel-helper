# 上下文意图识别模块分析文档

## 一、模块概述

意图识别模块(`intent_service.py`)是 XCAGI AI 对话系统的核心组件，负责解析用户消息、识别用户意图、判断是否包含否定指令，并决定后续处理流程。

**核心文件位置**: `e:\FHD\XCAGI\app\services\intent_service.py`

---

## 二、支持的意图类型

### 2.1 特殊意图（直接响应，不进入工具）

| 意图类型 | 识别函数 | 说明 |
|---------|---------|------|
| **问候语** | `is_greeting()` | 直接回复问候，不触发任何工具 |
| **告别语** | `is_goodbye()` | 结束会话，不再处理其他意图 |
| **帮助请求** | `is_help_request()` | 可走硬规则或 AI 生成帮助信息 |

**问候语关键词**:
```
你好、您好、嗨、嗨喽、hello、hi、早上好、下午好、晚上好、在吗、在么、有人吗、在不在
```

**告别语关键词**:
```
再见、拜拜、bye、先这样、没事了、谢谢再见、好的谢谢、先忙
```

### 2.2 工具意图（匹配后触发对应工具）

| 意图 ID | 工具 Key | 优先级 | 否定检测 | 关键词示例 |
|--------|----------|-------|---------|-----------|
| `shipment_generate` | `shipment_generate` | 12 (最高) | ✓ | 生成发货单、开发货单、开单、打单 |
| `wechat_send` | `wechat_send` | 10 | ✓ | 发给他、发送、发微信 |
| `shipment_template` | `shipment_template` | 9 | ✗ | 发货单模板、模板、当前模板 |
| `excel_decompose` | `excel_decompose` | 9 | ✗ | 分解excel、解析模板、词条提取 |
| `shipments` | `shipments` | 8 | ✗ | 出货、订单、发货记录 |
| `products` | `products` | 7 | ✗ | 产品、商品、型号、产品列表 |
| `customers` | `customers` | 6 | ✗ | 客户、顾客、用户列表、单位 |
| `show_images` | `show_images` | 6 | ✗ | 图片、照片、查看图片 |
| `show_videos` | `show_videos` | 6 | ✗ | 视频、录像、查看视频 |
| `print_label` | `print_label` | 5 | ✓ | 打印、标签、打印标签 |
| `upload_file` | `upload_file` | 5 | ✓ | 上传、导入、解析、上传文件 |
| `materials` | `materials` | 4 | ✗ | 原材料、库存、库存查询 |

### 2.3 Hint 意图（仅作为上下文提示，不直接触发工具）

| 意图 ID | 说明 | 关键词 |
|--------|------|--------|
| `template_query` | 模板查询 | 发货单模板、当前模板、哪个模板 |
| `customer_export` | 客户导出 | 导出excel、导出表格、导出客户列表 |
| `customer_list` | 客户列表 | 查看用户列表、客户列表 |
| `customer_edit` | 客户编辑 | 改成、修改、更新、设为 |
| `customer_supplement` | 客户补充 | 联系人、电话、手机、地址 |

---

## 三、否定检测机制

### 3.1 否定前缀列表

```
不要、别、不用、不需要、不必、取消、别给我、别帮我、不用了、不要了、
算了、不生成、不开发、不导入、不上传、不想、不用帮我、别弄、不用弄、不用做、不要做
```

### 3.2 否定短语列表

```
不要生成、别生成、不用生成、不要开发货单、别开发货单、不要开单、别开单、
不要上传、别上传、不用上传、不要导入、别导入、不要打印、别打印、不用打印、
取消打印、不打印、不要打标签
```

### 3.3 否定检测逻辑

**否定检测规则**:
1. **整句匹配**: 消息包含否定短语 → 否定
2. **句首否定**: 消息以否定前缀开头 → 否定
3. **动作前否定**: 否定前缀出现在动作关键词之前 → 否定

**示例**:
| 消息 | 是否否定 | 影响的工具 |
|------|---------|-----------|
| 不要生成发货单 | ✓ | shipment_generate |
| 别打印标签 | ✓ | print_label |
| 不用开单 | ✓ | shipment_generate |
| 上传文件 | ✗ | upload_file |

---

## 四、意图识别流程

### 4.1 主流程图

```
用户消息输入
     │
     ▼
┌─────────────────────────────────────┐
│ 1. 问候/再见/帮助检测                  │
│    - is_greeting()                   │
│    - is_goodbye()                    │
│    - is_help_request()               │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│ 2. 特殊格式检测                        │
│    "发货单+订单信息"格式                │
│    (如: 发货单七彩乐园 1桶 9803规格12)   │
│    → 直接识别为 shipment_generate     │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│ 3. 工具意图匹配 (_match_tool_intents)  │
│    - 遍历 TOOL_INTENTS               │
│    - 关键词命中                       │
│    - 按优先级(priority)排序            │
│    - 取最高优先级作为主意图             │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│ 4. 否定检测 (若 block_if_negated=True)│
│    - is_negation(message, action_kw) │
│    - 否定 → tool_key = None          │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│ 5. Hint 意图匹配 (_match_hint_intents)│
│    - 补充 intent_hints               │
│    - 不覆盖 tool_key                  │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│ 6. 口语化订单保底规则                   │
│    - 打印+型号/规格组合                │
│    - 缺少桶数的开单信息                │
│    - 口语化发货指令组合                │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│ 7. 模糊检测                           │
│    - 消息长度≤4字符                   │
│    - 无任何意图匹配                    │
│    - 无问候/再见                       │
└─────────────────────────────────────┘
     │
     ▼
   输出结果
```

### 4.2 核心识别函数

```python
recognize_intents(message: str) -> Dict[str, Any]
```

**返回值结构**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `primary_intent` | str/None | 主意图 ID（如 shipment_generate） |
| `tool_key` | str/None | 建议触发的工具 key，否定时为 None |
| `intent_hints` | List[str] | 上下文提示意图列表 |
| `is_negated` | bool | 是否为否定式指令 |
| `is_greeting` | bool | 是否为问候语 |
| `is_goodbye` | bool | 是否为告别语 |
| `is_help` | bool | 是否为帮助请求 |
| `is_likely_unclear` | bool | 是否为模糊/短句 |
| `all_matched_tools` | List[tuple] | 所有匹配的工具列表 |

### 4.3 优先级机制

1. **特殊格式检测** > **普通工具匹配** > **保底规则**
2. 同一工具意图内部，按 `priority` 字段降序排列
3. 相同优先级时，关键词更长的优先

---

## 五、特殊处理规则

### 5.1 发货单+订单信息格式

**识别条件**:
- 消息以"发货单/送货单/出货单"开头
- 长度 > 5 字符
- 包含订单特征词：桶、规格、公斤、kg、件、箱

**示例**:
| 输入 | 识别结果 |
|------|---------|
| 发货单七彩乐园 1桶 9803规格12 | shipment_generate |
| 送货单某某公司 3箱 | shipment_generate |

### 5.2 口语化订单结构（ASR保底）

**识别条件**:
- 当前工具为 None/products/shipments
- 包含"桶"和"规格"
- 包含数字样（阿拉伯数字或中文数字）

**示例**:
| 输入 | 识别结果 |
|------|---------|
| 七彩乐园的一桶酒吧零三的规格28 | shipment_generate |

### 5.3 打印+型号/规格（缺桶数）

**识别条件**:
- 当前工具为 products
- 包含"打印"关键词
- 包含"型号+规格"数字样
- 不包含桶/箱/件等数量容器词

**示例**:
| 输入 | 识别结果 |
|------|---------|
| 打印一下七彩乐园的9803规格28 | shipment_generate |

### 5.4 口语化发货指令

**识别条件**:
- 当前工具为 None 或 products
- 包含发货动作词（打印、发货单、送货单、出货单、开单、打单）
- 同时满足以下2个以上：
  - 含编号/型号 + 3-6位数字
  - 含规格 + 数字
  - 含"桶" + 数字

**示例**:
| 输入 | 识别结果 |
|------|---------|
| 给我打印一下七彩乐园发货单，编号9803，规格28，一共3桶 | shipment_generate |

---

## 六、输出示例

### 6.1 正常工具触发
```json
{
  "primary_intent": "shipment_generate",
  "tool_key": "shipment_generate",
  "intent_hints": ["shipment_generate"],
  "is_negated": false,
  "is_greeting": false,
  "is_goodbye": false,
  "is_help": false,
  "is_likely_unclear": false,
  "all_matched_tools": [["shipment_generate", "shipment_generate"]]
}
```

### 6.2 否定指令
```json
{
  "primary_intent": "shipment_generate",
  "tool_key": null,
  "intent_hints": ["shipment_generate"],
  "is_negated": true,
  "is_greeting": false,
  "is_goodbye": false,
  "is_help": false,
  "is_likely_unclear": false,
  "all_matched_tools": [["shipment_generate", "shipment_generate"]]
}
```

### 6.3 问候语
```json
{
  "primary_intent": null,
  "tool_key": null,
  "intent_hints": [],
  "is_negated": false,
  "is_greeting": true,
  "is_goodbye": false,
  "is_help": false,
  "is_likely_unclear": false,
  "all_matched_tools": []
}
```

### 6.4 模糊短句
```json
{
  "primary_intent": null,
  "tool_key": null,
  "intent_hints": [],
  "is_negated": false,
  "is_greeting": false,
  "is_goodbye": false,
  "is_help": false,
  "is_likely_unclear": true,
  "all_matched_tools": []
}
```

---

## 七、外部接口

### 7.1 核心函数

```python
# 全流程意图识别入口
recognize_intents(message: str) -> Dict[str, Any]

# 简化的工具 key 获取（带否定检测）
get_tool_key_with_negation_check(message: str) -> Optional[str]
```

### 7.2 路由层调用

在 `ai_chat.py` 中通过 `/intent/test` 接口调用：

```python
# POST /intent/test
{
  "message": "生成发货单"
}
```

---

## 八、流程处理对照表

| 场景 | 主意图 | 工具 Key | is_negated | 后续处理 |
|------|--------|----------|------------|---------|
| 你好 | None | None | false | 直接回复问候 |
| 再见 | None | None | false | 结束会话 |
| 生成发货单 | shipment_generate | shipment_generate | false | 触发发货单生成 |
| 不要生成发货单 | shipment_generate | **None** | true | 不触发工具，AI回复 |
| 查看客户列表 | customers | customers | false | 触发客户列表查询 |
| 客户有哪些 | customers | customers | false | 触发客户列表查询 |
| 发给他：你好 | wechat_send | wechat_send | false | 触发微信发送 |
| 当前用的模板 | shipment_template | shipment_template | false | 返回模板信息 |
| 上传Excel | upload_file | upload_file | false | 触发文件上传 |
| 打印标签 | print_label | print_label | false | 触发标签打印 |
| 嗯 | None | None | false | is_likely_unclear=true，AI兜底 |
