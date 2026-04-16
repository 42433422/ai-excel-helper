<template>
  <div class="page-view" id="view-orders">
    <div class="page-content">
      <div class="page-header">
        <h2>出货单记录</h2>
        <button class="btn btn-danger" id="clearAllOrdersBtn">清空全部</button>
      </div>
      <div class="search-box">
        <input type="text" id="orderSearch" placeholder="搜索客户名...">
        <input type="date" id="orderDate">
      </div>
      <div class="card">
        <table class="data-table">
          <thead>
            <tr>
              <th>单号</th>
              <th>客户</th>
              <th>日期</th>
              <th>金额</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody id="ordersTableBody">
            <tr><td colspan="6" class="empty-state">加载中...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
</script>
