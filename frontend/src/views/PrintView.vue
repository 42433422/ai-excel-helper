<template>
  <div class="page-view" id="view-print">
    <div class="page-content">
      <div class="page-header">
        <h2>标签打印</h2>
      </div>
      <div class="card">
        <div class="card-header">生成标签</div>
        <div class="form-group">
          <label>选择产品型号</label>
          <select id="printProductSelect">
            <option value="">请选择产品</option>
          </select>
        </div>
        <div class="form-group">
          <label>打印数量</label>
          <input type="number" id="printQuantity" value="1" min="1">
        </div>
        <button class="btn btn-primary" id="printLabelBtn">打印标签</button>
      </div>
    </div>
  </div>
</template>

<script setup>
</script>
