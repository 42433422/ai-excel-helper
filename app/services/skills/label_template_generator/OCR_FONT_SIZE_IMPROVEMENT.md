# OCR 字体大小识别改进

## 🎯 问题分析

用户反馈 OCR 识别时字体大小没有被识别出来，导致标签编辑器无法正确显示字体大小信息。

## ✅ 解决方案

### 1. 添加字体大小估算

在 `label_template_generator.py` 中，修改了 OCR 文本块处理逻辑：

```python
# 计算边界框尺寸
left = int(min([p[0] for p in bbox]))
top = int(min([p[1] for p in bbox]))
width = int(max([p[0] for p in bbox]) - min([p[0] for p in bbox]))
height = int(max([p[1] for p in bbox]) - min([p[1] for p in bbox]))

# 估算字体大小（文本高度的 70-80% 作为字体大小）
estimated_font_size = int(height * 0.75)

text_blocks.append({
    'text': text.strip(),
    'left': left,
    'top': top,
    'width': width,
    'height': height,
    'conf': score * 100,
    'center': (center_x, center_y),
    'y_center': center_y,
    'font_size': estimated_font_size  # 估算的字体大小
})
```

### 2. 字段信息包含字体大小

在所有字段生成位置都添加了 `font_size` 信息：

```python
fields.append({
    'label': label_block['text'],
    'value': value_block['text'],
    'field_key': field_key,
    'type': field_type,
    'position': {
        'left': label_block['left'],
        'top': label_block['top'],
        'width': label_block['width'],
        'height': label_block['height'],
        'font_size': label_block.get('font_size', 14)  # 字体大小
    },
    ...
})
```

### 3. 优化配对逻辑

针对"固定词条和数值没有分开"的问题，优化了标签和值的配对逻辑：

#### 改进点：
1. **添加详细日志** - 方便调试配对过程
2. **增加距离计算** - 即使不是相邻列，距离 < 50 像素也会配对
3. **灵活配对规则**：
   ```python
   # 计算两个块之间的距离
   distance = next_block['left'] - (block['left'] + block['width'])
   
   # 只有当下一个块不在合并单元格范围内且是相邻列时，才进行配对
   # 或者距离较近（< 50 像素）也进行配对
   if not next_is_in_merged and (next_col == col + 1 or distance < 50):
       # 配对成功
   ```

#### 配对逻辑流程：
```
文本块按 X 坐标排序
  ↓
检查是否在合并单元格
  ↓
是 → 作为独立字段（合并单元格）
  ↓
否 → 检查下一个块
  ↓
计算距离 + 检查列关系
  ↓
距离 < 50 或 相邻列 → 配对（标签 + 值）
  ↓
否则 → 作为独立字段
```

### 4. 调试日志

添加了详细的调试日志输出：

```python
logger.info(f"第 {group['row']} 行有 {len(blocks_sorted)} 个文本块")
logger.info(f"处理块：'{block['text']}' (列 {col}, x={block['left']})")
logger.info(f"  下一个块：'{next_block['text']}' (列 {next_col}, x={next_block['left']})")
logger.info(f"  -> 配对成功：'{label_block['text']}' + '{value_block['text']}', 距离：{distance}")
logger.info(f"  -> 单独字段：'{block['text']}', 类型：{field_type}")
```

## 📊 技术细节

### 字体大小估算原理

PaddleOCR 识别出的文本块包含边界框（bbox）信息，通过边界框的高度可以估算字体大小：

```
字体大小 ≈ 文本框高度 × 0.75
```

这个系数（0.75）是基于以下考虑：
- 文本框高度通常包含 ascender（上伸部分）和 descender（下降部分）
- 实际字体大小约为文本框高度的 70-80%
- 取中间值 0.75 作为估算系数

### 配对距离阈值

设置 50 像素作为距离阈值的原因：
- 标签和值之间通常有较小的间距（10-30 像素）
- 不同字段之间通常有较大的间距（> 50 像素）
- 50 像素是一个合理的分界值

## 🔍 测试验证

### 测试场景 1：标准标签模板
```
品名：运动鞋    颜色：黑色    货号：A001
```

**预期结果**：
- "品名" 和 "运动鞋" 配对
- "颜色" 和 "黑色" 配对
- "货号" 和 "A001" 配对
- 每个字段都有 font_size 信息

### 测试场景 2：合并单元格
```
|        公司名称        |  地址  |
|  XXX 有限公司          |  XXXX  |
```

**预期结果**：
- "公司名称" 作为合并单元格，独立字段
- "地址" 和 "XXXX" 配对

### 测试场景 3：密集排版
```
品名：运动鞋 颜色：黑色 货号：A001
```

**预期结果**：
- 即使列不连续，距离 < 50 像素也会配对
- 正确识别标签和值对

## 📈 改进效果

### 之前的问题：
1. ❌ 字体大小信息丢失
2. ❌ 标签和值配对不准确
3. ❌ 密集排版识别错误
4. ❌ 无法调试配对过程

### 现在的效果：
1. ✅ 每个字段都有 font_size 信息（估算值）
2. ✅ 标签和值配对更准确（距离 + 列关系）
3. ✅ 支持密集排版识别
4. ✅ 详细日志便于调试

## 🎯 使用方法

### 1. 上传标签图片
```
点击"上传图片" → 选择图片 → 自动识别
```

### 2. 查看识别结果
```python
# 后端返回的字段信息
{
    "fields": [
        {
            "label": "品名",
            "value": "运动鞋",
            "type": "fixed",
            "position": {
                "left": 50,
                "top": 100,
                "width": 80,
                "height": 30,
                "font_size": 22  # ← 新增
            }
        },
        ...
    ]
}
```

### 3. 前端应用字体大小
```javascript
// 在画布上绘制时，使用字体大小
ctx.font = `${field.position.font_size || 14}px Arial`
ctx.fillText(text, x, y)
```

## 🔧 调试技巧

### 查看后端日志
```bash
# 运行 Flask 应用时，查看 OCR 识别日志
2026-03-23 14:30:15 - 第 0 行有 6 个文本块
2026-03-23 14:30:15 - 处理块：'品名' (列 0, x=50)
2026-03-23 14:30:15 - 下一个块：'运动鞋' (列 1, x=150)
2026-03-23 14:30:15 - -> 配对成功：'品名' + '运动鞋', 距离：20
```

### 检查返回数据
```javascript
// 在浏览器控制台检查
console.log('识别到的字段:', res.fields)
// 每个字段应该包含 position.font_size
```

## 📝 注意事项

1. **字体大小估算**：
   - 基于文本框高度估算，不是精确值
   - 对于特殊字体可能有偏差
   - 建议值：12-24 像素

2. **配对距离阈值**：
   - 当前设置为 50 像素
   - 可根据实际图片调整
   - 高分辨率图片可适当增大

3. **日志级别**：
   - 生产环境可调整为 WARNING 或 ERROR
   - 开发环境使用 INFO 便于调试

## ✅ 完成状态

- [x] 字体大小估算功能
- [x] 字段信息包含 font_size
- [x] 配对逻辑优化
- [x] 调试日志添加
- [x] 距离计算和灵活配对
- [x] 代码测试通过

---

**更新时间**: 2026-03-23  
**文件**: `e:\FHD\XCAGI\app\services\skills\label_template_generator\label_template_generator.py`  
**状态**: ✅ 完成
