<template>
  <div class="page-view" id="view-template-preview">
    <div class="page-content">
      <div class="page-header">
        <h2>模板预览</h2>
        <p class="muted" style="margin:0;font-size:13px;">2 个标签模板 + 2 个 Excel 模板（发货单、出货记录）</p>
      </div>
      <div class="template-preview-section">
        <h3 class="template-preview-section-title">标签模板（2 个）</h3>
        <div class="template-preview-grid">
          <div class="template-preview-card">
            <div class="template-preview-card-icon">🏷️</div>
            <div class="template-preview-card-title">产品标签模板</div>
            <div class="template-preview-card-desc">按产品型号生成并打印产品标签，支持单张或批量。</div>
            <div class="template-preview-actions">
              <button type="button" class="btn btn-primary btn-sm template-preview-action" data-template-action="view-print">查看</button>
              <button type="button" class="btn btn-secondary btn-sm template-preview-action" data-template-action="open-print">打开标签打印</button>
            </div>
          </div>
          <div class="template-preview-card">
            <div class="template-preview-card-icon">📦</div>
            <div class="template-preview-card-title">商标 / 订单标签模板</div>
            <div class="template-preview-card-desc">生成发货单时一并生成的商标标签，可从「商标导出」下载或打印。</div>
            <div class="template-preview-actions">
              <button type="button" class="btn btn-primary btn-sm template-preview-action" data-template-action="view-labels-export">查看</button>
              <button type="button" class="btn btn-secondary btn-sm template-preview-action" data-template-action="show-labels-export">打开商标导出</button>
            </div>
          </div>
        </div>
      </div>
      <div class="template-preview-section">
        <h3 class="template-preview-section-title">Excel 模板（2 个）</h3>
        <div class="template-preview-grid">
          <div class="template-preview-card" data-template-id="shipment_template">
            <div class="template-preview-card-icon">📋</div>
            <div class="template-preview-card-title">发货单模板</div>
            <div class="template-preview-card-desc">当前使用的发货单 Excel 模板，支持抬头、购货单位、词条提取与金额计算。</div>
            <div class="template-preview-actions">
              <button type="button" class="btn btn-primary btn-sm template-preview-action" data-template-action="open-excel-preview" data-template-id="shipment_template">打开预览</button>
              <button type="button" class="btn btn-secondary btn-sm template-preview-action" data-template-action="view-template-overview">查看</button>
              <button type="button" class="btn btn-secondary btn-sm template-preview-action" data-template-action="show-template-overview">新窗口概览</button>
            </div>
          </div>
          <div class="template-preview-card" data-template-id="shipment_record">
            <div class="template-preview-card-icon">📊</div>
            <div class="template-preview-card-title">出货记录模板</div>
            <div class="template-preview-card-desc">按单位导出的出货记录 Excel，用于对账与留档。</div>
            <div class="template-preview-actions">
              <button type="button" class="btn btn-primary btn-sm template-preview-action" data-template-action="open-excel-preview" data-template-id="shipment_record">打开预览</button>
              <button type="button" class="btn btn-secondary btn-sm template-preview-action" data-template-action="view-shipment-records">查看</button>
              <button type="button" class="btn btn-secondary btn-sm template-preview-action" data-template-action="open-shipment-records">打开出货记录</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
</script>
