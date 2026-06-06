# 行业解决方案 Mod（taxonomy）

本目录用于约定 **`taxonomy.category: industry_solution`** 的 Mod 如何命名、编排文档与对接营销站；**物理包仍放在 `mods/<mod-id>/`**（不在此目录重复一份源码），此处提供模板与衔接说明。

## 约定

1. **manifest**：在 `manifest.json` 中填写可选字段 `taxonomy`（见 [`../manifest-schema.json`](../manifest-schema.json)）。  
   - `industry_vertical`：稳定英文 slug，便于路由与检索。  
   - `tier: template`：行业模板/脚手架尚未对客户交付时使用。  
   - `market_slug`：可选；供静态站案例卡片或锚点与 [`cases.html`](../../cases.html) 联动。

2. **审核**：上架前建议走 [`eskill-prototype/collaborative-mod-review`](../../eskill-prototype/collaborative-mod-review/README.md) 协同审核，再经 `employee-pack-curator` 注册。

3. **跨宿主**：若计划分发到 MODstore 以外宿主，补充 `cross_platform` 与 `META-INF/adapters/`（见 [`docs/adr/0004-xcemp-cross-platform-adapters.md`](../../docs/adr/0004-xcemp-cross-platform-adapters.md)）。

## 模板

- [`_TEMPLATE/manifest.snippet.json`](_TEMPLATE/manifest.snippet.json)：可复制到完整 `manifest.json` 的片段示例。

## 与静态站（site-content-editor）

行业包 **审核通过并上架** 后，由 **site-content-editor** 依据 manifest 与策展说明更新案例/解决方案文案；衔接任务说明见：

[`yuangon/site-and-marketing/site-content-editor/tasks/industry-mod-market-copy-handoff.md`](../../yuangon/site-and-marketing/site-content-editor/tasks/industry-mod-market-copy-handoff.md)。
