# xcagi-host-foundation-employee

宿主**基础能力预装员工**（`artifact: employee_pack`），不是可单独选购的 9 个 bridge Mod。

- 安装本员工包 → 宿主从内置 `mods/` 种子目录复制 9 个 bridge 到本机 `mods/` 并加载。
- MOD 商店 Catalog **隐藏** `xcagi-*-bridge` 等基础设施件，仅展示本员工包 + 行业 Mod + 工作流员工。

与 `POST /api/mod-store/install-host-foundation` 及引导页「一键装齐」共用同一套 `materialize_host_foundation_bridges()` 逻辑。
