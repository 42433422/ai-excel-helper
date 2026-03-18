<template>
  <div class="page-view" id="view-settings">
    <div class="page-content">
      <div class="page-header">
        <h2>系统设置</h2>
      </div>
      <div class="card">
        <div class="card-header">基本设置</div>
        <div class="form-group">
          <label>系统名称</label>
          <input type="text" value="AI-Excel Helper 出货单管理系统" disabled>
        </div>
        <div class="form-group">
          <label>数据库路径</label>
          <input type="text" value="products.db" disabled>
        </div>
        <div class="form-group">
          <label>AI 模型</label>
          <select id="aiModel">
            <option value="deepseek">DeepSeek</option>
            <option value="local">本地模型 (需配置)</option>
          </select>
        </div>
        <button class="btn btn-primary" id="saveSettingsBtn">保存设置</button>
      </div>
      <div class="card" id="distillationVersionsCard">
        <div class="card-header">蒸馏模型版本 <small style="opacity:0.8">专业版对话会参与蒸馏，此处可查看训练产物</small></div>
        <div id="distillationVersionsContent">
          <p class="muted">加载中...</p>
        </div>
      </div>
      <div class="card">
        <div class="card-header">关于</div>
        <p>AI-Excel Helper 出货单智能处理系统</p>
        <p>版本: 1.0.0</p>
      </div>
    </div>
  </div>
</template>

<script setup>
</script>
