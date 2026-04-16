FHD 最小 Vue 产品页：一级读锁 + 列表演示
========================================

1) 后端：在启动后端的 shell 中设置 FHD_DB_READ_TOKEN（可用 scripts/fhd-set-database-url.ps1 点源），重启后端。

2) 自检：  .\scripts\verify-db-read-lock.ps1

3) 本仓库演示前端：
   cd frontend
   npm install
   npm run dev
   浏览器打开 http://127.0.0.1:5173 （Vite 将 /api 代理到 http://127.0.0.1:8000）

--------------------------------------------------------------------
主 XCAGI 工程里点「产品管理」仍 403 — 原因与处理
--------------------------------------------------------------------

原因：一级读锁默认开启，浏览器请求 /api/products/list 等未带请求头 X-FHD-Db-Read-Token。

必做（二选一或都做）：

A) 全局 axios 合并读头（否则永远 403）
   从本仓库拷贝：
     frontend/src/api/attachAxiosDbReadInterceptor.ts
     frontend/src/components/fhd/dbTokenHeaders.ts
   在主工程创建 axios 实例之后执行：
     import { attachAxiosDbReadInterceptor } from "…/attachAxiosDbReadInterceptor";
     attachAxiosDbReadInterceptor(api);

B) 全局弹窗输入口令（否则不知道往 localStorage 写什么）
   拷贝 frontend/src/components/fhd/GlobalReadTokenPrompt.vue
   在 App.vue 根模板增加（与 router-view 并列）：
     <GlobalReadTokenPrompt :api-base="你的API根或空字符串同源" />
   各页在解锁后监听事件常量 FHD_DB_READ_UNLOCKED_EVENT（见 dbTokenHeaders.ts）再重新请求列表。

应急（仅本机调试、不改代码）：
   浏览器 F12 → Console 执行：
     localStorage.setItem("xcagi_db_read_token","61408693");
   （若你改了 FHD_DB_READ_TOKEN，把字符串改成与之一致。）然后 Ctrl+F5 强刷。

临时关闭一级锁（不推荐生产）：
   环境变量 FHD_DISABLE_DB_READ_LOCK=1，重启后端。
