# TabBar 图标创建指南

由于无法直接生成 PNG 图片，请按以下步骤手动创建图标：

## 方法一：使用在线工具（推荐）

1. 访问 [iconfont.cn](https://www.iconfont.cn)
2. 搜索以下图标：
   - 首页（home）
   - 分类（category）
   - 购物车（cart）
   - 用户/个人中心（profile）
3. 下载 PNG 格式，尺寸 81x81
4. 准备两套：一套灰色（#999999），一套蓝色（#1890ff）
5. 放入 `e:\FHD\WXCC\assets\tab\` 目录

## 方法二：使用微信开发者工具

1. 打开微信开发者工具
2. 新建项目时会自动生成默认图标
3. 复制默认图标到 `e:\FHD\WXCC\assets\tab\` 目录

## 方法三：使用设计工具

使用 Figma、Sketch、Photoshop 等工具设计：
- 尺寸：81x81 像素
- 格式：PNG 透明背景
- 颜色：
  - 未选中：#999999
  - 选中：#1890ff

## 需要的文件列表

```
assets/tab/
├── home.png              (灰色)
├── home-active.png       (蓝色)
├── category.png          (灰色)
├── category-active.png   (蓝色)
├── cart.png              (灰色)
├── cart-active.png       (蓝色)
├── profile.png           (灰色)
└── profile-active.png    (蓝色)
```

## 临时解决方案

如果急需测试，可以暂时移除 app.json 中的 iconPath 和 selectedIconPath，只显示文字：

编辑 `app.json`，将 tabBar 配置修改为：

```json
"tabBar": {
  "color": "#999999",
  "selectedColor": "#1890ff",
  "list": [
    {
      "pagePath": "pages/index/index",
      "text": "首页"
    },
    {
      "pagePath": "pages/category/category",
      "text": "分类"
    },
    {
      "pagePath": "pages/cart/cart",
      "text": "购物车"
    },
    {
      "pagePath": "pages/my/index/index",
      "text": "我的"
    }
  ]
}
```
