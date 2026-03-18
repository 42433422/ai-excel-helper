<template>
  <div class="page-view" id="view-shipment-records">
    <div class="page-content">
      <div class="page-header">
        <h2>出货记录管理</h2>
        <div class="header-actions">
          <select id="shipmentRecordUnitSelect" style="min-width: 200px; padding: 8px 12px; margin-right: 10px;">
            <option value="">请选择购买单位</option>
          </select>
          <button class="btn btn-primary" id="loadShipmentRecordsBtn">查看记录</button>
          <button class="btn btn-success" id="exportShipmentRecordsBtn" title="导出当前单位出货记录 Excel">导出 Excel</button>
        </div>
      </div>
      <div class="card">
        <div class="card-header" id="shipmentRecordsCardTitle">选择购买单位后点击「查看记录」加载数据</div>
        <div id="shipmentRecordsSheetsTabs" style="margin-bottom: 12px; display: none;">
        </div>
        <div class="table-responsive table-responsive-shipment-records">
          <table class="data-table data-table-shipment-records" id="shipmentRecordsTable">
            <thead>
              <tr id="shipmentRecordsTableHead">
                <th>暂无数据</th>
              </tr>
            </thead>
            <tbody id="shipmentRecordsTableBody">
              <tr><td colspan="1" class="empty-state">请先选择购买单位并加载</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
</script>
