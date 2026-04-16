# 图片资源说明

## 需要的图片资源

请在以下位置添加对应的图片文件：

### 轮播图 (assets/banner/)
- `banner/1.jpg` - 轮播图 1（建议尺寸：750x400）
- `banner/2.jpg` - 轮播图 2
- `banner/3.jpg` - 轮播图 3

### 分类图标 (assets/category/)
- `category/all.png` - 全部分类图标（建议尺寸：100x100）
- `category/paint.png` - 涂料图标
- `category/curing.png` - 固化剂图标
- `category/diluent.png` - 稀释剂图标
- `category/auxiliary.png` - 助剂图标
- `category/tool.png` - 工具图标

### 商品图片 (assets/product/)
- `product/1.jpg` - 商品示例图 1（建议尺寸：800x800）
- `product/2.jpg` - 商品示例图 2
- `product/3.jpg` - 商品示例图 3
- `product/default.jpg` - 默认商品图片

### 其他资源
- `empty.png` - 空状态图标（建议尺寸：200x200）

## 图片要求

### 轮播图
- **格式**: JPG
- **尺寸**: 750x400 像素
- **质量**: 80% 压缩
- **内容**: 活动海报、产品推荐等

### 分类图标
- **格式**: PNG（透明背景）
- **尺寸**: 100x100 像素
- **风格**: 简洁线性或面性图标
- **颜色**: 与主题色协调

### 商品图片
- **格式**: JPG
- **尺寸**: 800x800 像素（正方形）
- **质量**: 80% 压缩
- **背景**: 纯白或透明

## 临时解决方案

### 方法一：使用占位图服务

可以使用在线占位图服务临时测试：

```xml
<!-- 轮播图 -->
<image src="https://via.placeholder.com/750x400?text=Banner" />

<!-- 分类图标 -->
<image src="https://via.placeholder.com/100x100?text=Icon" />

<!-- 商品图片 -->
<image src="https://via.placeholder.com/800x800?text=Product" />
```

### 方法二：使用设计工具生成

1. **使用 Figma**
   - 访问 [figma.com](https://figma.com)
   - 创建对应尺寸的画布
   - 设计简单的占位图
   - 导出为 JPG/PNG

2. **使用 Photoshop**
   - 新建对应尺寸的画布
   - 填充颜色或添加文字
   - 导出为 JPG/PNG

### 方法三：使用示例图片

可以从以下网站下载免费示例图片：

- [unsplash.com](https://unsplash.com) - 高质量免费图片
- [pexels.com](https://pexels.com) - 免费素材图片
- [pixabay.com](https://pixabay.com) - 免费图片库

## 图片优化建议

1. **压缩图片**
   - 使用 [tinypng.com](https://tinypng.com) 压缩 PNG
   - 使用 [squoosh.app](https://squoosh.app) 压缩 JPG

2. **格式选择**
   - 照片类：JPG
   - 图标类：PNG
   - 动图类：GIF 或 WebP

3. **大小控制**
   - 单张图片不超过 200KB
   - 轮播图不超过 100KB
   - 图标不超过 20KB

## 检查清单

添加图片后，请检查：

- [ ] 所有图片文件已创建
- [ ] 图片尺寸符合要求
- [ ] 图片格式正确
- [ ] 图片路径正确
- [ ] 图片大小合理
- [ ] 在开发者工具中预览效果

## 文件结构

```
assets/
├── banner/
│   ├── 1.jpg
│   ├── 2.jpg
│   └── 3.jpg
├── category/
│   ├── all.png
│   ├── paint.png
│   ├── curing.png
│   ├── diluent.png
│   ├── auxiliary.png
│   └── tool.png
├── product/
│   ├── 1.jpg
│   ├── 2.jpg
│   ├── 3.jpg
│   └── default.jpg
└── empty.png
```
