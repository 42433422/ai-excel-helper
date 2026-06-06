# XCAGI 客户运维与支持约定（桌面版）

面向**签约客户现场**：版本核对、升级回滚、日志与诊断包、支持口径。Web / Docker 自托管见 `[DEPLOYMENT.md](../DEPLOYMENT.md)`。

---

## 1. 版本号与变更说明（须与安装包一致）


| 内容    | 单一事实来源                                 | 客户核对方式              |
| ----- | -------------------------------------- | ------------------- |
| 语义化版本 | 仓库根目录 `[VERSION.md](../../VERSION.md)` | 与安装程序「关于」或属性中的版本号一致 |
| 详细变更  | `[CHANGELOG.md](../../CHANGELOG.md)`   | 发版邮件 / 发行说明附同一版本小节  |


**发版自检（供应商侧）**：更新安装包前执行 `VERSION.md` 中的 `rg` 扫描命令，保证 `pyproject.toml`、`frontend/package.json`、`desktop/package.json`、`app/fastapi_app.py` 等与 `**CHANGELOG` 顶部版本**一致。

**客户侧**：升级前请记录当前版本号；若与供应商提供的发行说明版本不符，勿覆盖安装，先联系支持。

---

## 2. 升级与回滚（含桌面自动更新）

### 2.1 自动更新（electron-updater）

- 供应商配置 `**XCAGI_UPDATE_URL`**（generic 更新仓）后，壳程序会周期性检查更新；下载完成后可选择「立即重启安装」。
- **可选安全项**：`XCAGI_UPDATE_ED25519_PUBLIC_KEY` 与元数据二次签名校验（见 `desktop/updater.ts`）。
- **通道**：`XCAGI_UPDATE_CHANNEL`（默认 `stable`）。

### 2.2 建议升级步骤（客户）

1. **备份**：退出 XCAGI，复制整个数据目录（见下文「日志与数据位置」中的路径），或至少复制 `backups/` 下最近一次 `.db` 备份。
2. **安装新版本**：运行供应商提供的安装包；首次启动时会尝试运行迁移（安装前可在壳内触发带备份的迁移流程）。
3. **验证**：登录核心业务流程（与合同中约定的验收用例一致）。

### 2.3 回滚

- **理想做法**：用升级前的数据目录备份还原后，安装**上一发行版**的安装包（供应商保留 N-1 安装包下载链接）。
- **数据库**：桌面库默认为 `data/xcagi.db`；若新版本迁移失败，在供应商指导下可用 `backups/` 中的 `**xcagi-<version>-<时间戳>.db`** 替换（先停应用再操作）。
- **不支持**：在同一目录上反复混装不同渠道的非正式发布包；请以供应商指定的 GA / 补丁构建为准。

### 2.4 专用安装包下载器（Windows）

当浏览器/网盘拉取大包不稳定、需走代理，或应用内更新因证书/策略失败时，可使用发行目录 **`tools/XcagiDownloader.exe`**（与 Windows 安装包同批构建）：

- **更新仓地址**：与 **`XCAGI_UPDATE_URL`** 一致（指向包含 **`latest.yml`** 与 **`XCAGI-Setup-*.exe`** 的目录）；内网镜像保持与官方相同的目录结构即可。
- **可选 Ed25519**：与桌面 **`XCAGI_UPDATE_ED25519_PUBLIC_KEY`** 相同配置；填写后要求 `latest.yml` 含二次签名。
- **日志**：`%AppData%\XCAGI\downloader\downloader.log`；静默安装参数与镜像约定详见 [`tools/XcagiDownloader/README.md`](../../tools/XcagiDownloader/README.md)。

---

## 3. 日志位置与一键导出诊断包

### 3.1 数据与日志目录（桌面）

由 Electron `**userData`** 传入后端，典型路径：


| 系统      | 用户数据根目录（默认）                                  |
| ------- | -------------------------------------------- |
| Windows | `%APPDATA%\XCAGI` 或由安装配置指定                   |
| macOS   | `~/Library/Application Support/XCAGI`        |
| Linux   | `$XDG_CONFIG_HOME/XCAGI` 或 `~/.config/XCAGI` |


其下常用子目录（应用启动时会创建）：


| 子目录               | 用途                  |
| ----------------- | ------------------- |
| `data/xcagi.db`   | 桌面主库                |
| `logs/xcagi.log`  | 后端滚动日志（桌面模式启用文件日志后） |
| `backups/`        | 迁移或更新前生成的 SQLite 备份 |
| `uploads/`        | 上传文件                |
| `mods/`、`models/` | 扩展与模型               |


菜单 **「打开数据目录」** 可直接打开上述根路径。

### 3.2 诊断包（技术支持）

- **菜单**：`XCAGI` → **「导出诊断包…」**，保存为 ZIP。
- **HTTP（仅本机）**：`GET http://127.0.0.1:<端口>/api/desktop/support-bundle`（桌面模式；端口默认与壳一致，见环境变量 `XCAGI_DESKTOP_PORT`）。

ZIP 内含 `**manifest.json`**（环境、路径摘要、备份文件名列表）及 `**logs/**` 下近期日志节选；**不包含**数据库正文。若支持人员需要库结构分析，请在指导下另行传送 `backups/` 中的 `.db` 文件。

---

## 4. 有限 SLA 话术模板（供应商 ↔ 客户）

以下内容仅为**商务与技术沟通的范式**，具体数字须填入合同或 SLA 附件。

> **服务时间**：中国大陆工作日 **10:00–18:00**（法定节假日除外），支持渠道：邮件 / 约定 IM / 工单系统。  
> **响应分级**：  
>
> - **P1（系统不可用、数据无法读写）**：× 小时内首次响应，× 工作日内提供规避方案或补丁计划。  
> - **P2（功能降级、部分用户受影响）**：× 小时内首次响应，计划在 × 个工作日内修复或提供临时方案。  
> - **P3（咨询、改进建议）**：× 个工作日内响应。  
> **补丁**：严重缺陷（P1）以「安全修复构建」形式提供；客户须在测试环境验证后再上线。  
> **不包含**：第三方网络 / 云厂商故障、客户自行修改二进制或数据库、未按文档配置的私有化魔改。

请将上述「×」替换为双方约定数值；避免口头无限承诺。

---

## 5. 相关代码锚点（供应商维护）

- 桌面壳菜单与导出：`desktop/main.ts`
- 更新逻辑：`desktop/updater.ts`
- 路径与环境：`app/desktop_runtime/paths.py`
- 诊断包：`app/desktop_runtime/support_bundle.py`、`GET /api/desktop/support-bundle`
- 文件日志：`app/desktop_runtime/logging_setup.py`