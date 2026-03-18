<template>
  <div class="page-view" id="view-wechat-contacts">
    <div class="page-content">
      <div class="page-header">
        <h2>微信联系人</h2>
      </div>
      <div class="card">
        <div class="card-header">搜索并星标</div>
        <p class="muted" style="margin:0 0 10px 0;font-size:13px;">先刷新联系人缓存与聊天记录缓存（从解密库导入一次），之后搜索与查看聊天记录只读本地缓存。</p>
        <div class="form-group" style="display:flex;flex-wrap:wrap;align-items:center;gap:10px;">
          <button type="button" class="btn btn-primary" id="wechatContactRefreshCacheBtn">刷新联系人缓存</button>
          <button type="button" class="btn btn-primary" id="wechatContactRefreshMessagesCacheBtn">刷新聊天记录缓存</button>
          <input type="text" id="wechatContactSearchForStar" placeholder="输入昵称/备注/微信号搜索" style="max-width:320px;" onkeydown="if(event.key==='Enter'){ event.preventDefault(); if(typeof searchWechatContactsForStar==='function') searchWechatContactsForStar(); }">
          <button type="button" class="btn btn-primary" id="wechatContactSearchBtn">搜索</button>
        </div>
        <div id="wechatContactSearchResults" style="margin-top:10px;min-height:0;max-height:240px;overflow-y:auto;"></div>
      </div>
      <div class="card">
        <div class="card-header">星标联系人列表</div>
        <div class="form-group" style="display:flex;flex-wrap:wrap;align-items:center;gap:12px;">
          <label style="margin:0;white-space:nowrap;">类型：</label>
          <select id="wechatContactTypeFilter" style="width:120px;">
            <option value="all">全部</option>
            <option value="contact">联系人</option>
            <option value="group">群聊</option>
          </select>
          <input type="text" id="wechatContactSearch" placeholder="🔍 在星标列表中筛选" style="max-width:320px;">
          <button type="button" class="btn btn-secondary" id="wechatContactUnstarAllBtn" title="清除所有星标，列表将为空">一键解除全部星标</button>
        </div>
        <div id="wechatContactsListContainer">
          <div class="empty-state">加载中...</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
</script>
