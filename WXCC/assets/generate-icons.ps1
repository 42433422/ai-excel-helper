# 微信小程序 TabBar 图标生成脚本
# 使用 System.Drawing 创建简单的 PNG 图标

Add-Type -AssemblyName System.Drawing

function New-TabIcon {
    param(
        [string]$IconName,
        [string]$Text,
        [string]$Color,
        [bool]$IsActive
    )
    
    # 创建 81x81 的位图
    $bitmap = New-Object System.Drawing.Bitmap(81, 81)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    
    # 设置抗锯齿
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    
    # 透明背景
    $graphics.Clear([System.Drawing.Color]::Transparent)
    
    # 创建画刷
    $brush = New-Object System.Drawing.SolidBrush([System.Drawing.ColorTranslator]::FromHtml($Color))
    
    # 创建字体
    $font = New-Object System.Drawing.Font("Arial", 40, [System.Drawing.FontStyle]::Bold)
    
    # 绘制文字
    $stringFormat = New-Object System.Drawing.StringFormat
    $stringFormat.Alignment = [System.Drawing.StringAlignment]::Center
    $stringFormat.LineAlignment = [System.Drawing.StringAlignment]::Center
    
    $rect = New-Object System.Drawing.Rectangle(0, 0, 81, 81)
    $graphics.DrawString($Text, $font, $brush, $rect, $stringFormat)
    
    # 保存为 PNG
    $outputPath = "e:\FHD\WXCC\assets\tab\$IconName.png"
    $bitmap.Save($outputPath, [System.Drawing.Imaging.ImageFormat]::Png)
    
    # 释放资源
    $graphics.Dispose()
    $bitmap.Dispose()
    $brush.Dispose()
    $font.Dispose()
    
    Write-Host "已创建图标：$outputPath"
}

# 创建首页图标
New-TabIcon -IconName "home" -Text "🏠" -Color "#999999" -IsActive $false
New-TabIcon -IconName "home-active" -Text "🏠" -Color "#1890ff" -IsActive $true

# 创建分类图标
New-TabIcon -IconName "category" -Text "📂" -Color "#999999" -IsActive $false
New-TabIcon -IconName "category-active" -Text "📂" -Color "#1890ff" -IsActive $true

# 创建购物车图标
New-TabIcon -IconName "cart" -Text "🛒" -Color "#999999" -IsActive $false
New-TabIcon -IconName "cart-active" -Text "🛒" -Color "#1890ff" -IsActive $true

# 创建个人中心图标
New-TabIcon -IconName "profile" -Text "👤" -Color "#999999" -IsActive $false
New-TabIcon -IconName "profile-active" -Text "👤" -Color "#1890ff" -IsActive $true

Write-Host "所有图标已创建完成！"
