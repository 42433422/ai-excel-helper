# 图片资源占位符生成指南

由于无法直接生成图片文件，以下是快速创建占位图的方法：

## 方法一：使用在线工具（推荐）

### 1. 轮播图占位
访问 https://via.placeholder.com 生成：
- https://via.placeholder.com/750x400/1890ff/ffffff?text=Banner+1
- https://via.placeholder.com/750x400/096dd9/ffffff?text=Banner+2
- https://via.placeholder.com/750x400/1890ff/ffffff?text=Banner+3

### 2. 分类图标占位
访问 https://placehold.co 生成：
- https://placehold.co/100x100/1890ff/ffffff?text=All
- https://placehold.co/100x100/1890ff/ffffff?text=Paint
- https://placehold.co/100x100/1890ff/ffffff?text=Curing
- https://placehold.co/100x100/1890ff/ffffff?text=Diluent
- https://placehold.co/100x100/1890ff/ffffff?text=Auxiliary
- https://placehold.co/100x100/1890ff/ffffff?text=Tool

### 3. 商品图片占位
- https://placehold.co/800x800/f5f5f5/999999?text=Product+1
- https://placehold.co/800x800/f5f5f5/999999?text=Product+2
- https://placehold.co/800x800/f5f5f5/999999?text=Product+3

## 方法二：使用微信开发者工具

1. 打开微信开发者工具
2. 新建一个空白小程序
3. 复制项目中的图片资源
4. 粘贴到 `e:\FHD\WXCC\assets\` 目录

## 方法三：手动创建简单占位图

### 使用画图工具（Windows Paint）

1. 打开画图工具
2. 创建对应尺寸的画布
3. 填充颜色
4. 添加文字（可选）
5. 保存为 JPG/PNG

### 使用 PowerShell 创建纯色 PNG

```powershell
# 需要 System.Drawing
Add-Type -AssemblyName System.Drawing

function New-PlaceholderImage {
    param(
        [string]$Path,
        [int]$Width,
        [int]$Height,
        [string]$Color
    )
    
    $bitmap = New-Object System.Drawing.Bitmap($Width, $Height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $brush = New-Object System.Drawing.SolidBrush([System.Drawing.ColorTranslator]::FromHtml($Color))
    
    $graphics.Clear($Color)
    $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    
    $graphics.Dispose()
    $bitmap.Dispose()
    $brush.Dispose()
}

# 创建示例图片
New-PlaceholderImage -Path "e:\FHD\WXCC\assets\empty.png" -Width 200 -Height 200 -Color "#f0f0f0"
```

## 方法四：修改代码使用网络图片

临时修改页面代码，使用网络占位图：

### 修改 pages/index/index.js

```javascript
data: {
  banners: [
    { image: 'https://via.placeholder.com/750x400?text=Banner+1' },
    { image: 'https://via.placeholder.com/750x400?text=Banner+2' },
    { image: 'https://via.placeholder.com/750x400?text=Banner+3' }
  ],
  // ...
}
```

### 修改 pages/category/category.js

```javascript
data: {
  categories: [
    { icon: 'https://placehold.co/100x100?text=All', name: '全部' },
    { icon: 'https://placehold.co/100x100?text=Paint', name: '涂料' },
    // ...
  ]
}
```

## 快速测试步骤

1. **清除缓存**：工具 → 清除缓存 → 清除全部缓存
2. **重新编译**：点击编译按钮
3. **查看效果**：检查图片是否正常显示

## 推荐做法

建议尽快替换为实际的业务图片：

1. **轮播图**：活动海报、产品推荐
2. **分类图标**：统一的图标风格
3. **商品图片**：实际产品照片

## 图片优化

替换图片时注意：
- 压缩图片大小
- 使用合适的格式
- 保持统一的视觉风格
- 符合品牌调性
