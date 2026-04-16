# 个人微信（PC 版）MCP 配置说明

在 Cursor 里使用个人微信 PC 版收发消息，需要先安装一个微信 MCP 服务端，并保证 **微信已启动并登录**（窗口不要最小化）。

---

## 前置条件

- Windows 10/11
- Python 3.8 或以上（命令行能执行 `python` 或 `py`）
- 微信 PC 版已安装、已登录，且窗口处于可见状态

---

## 方案一：mcp_server_wechat（推荐，一条命令安装）

**功能**：获取聊天记录、发送单条/多条消息、群发消息。

### 1. 安装

```powershell
pip install mcp_server_wechat
```

### 2. 准备一个目录（可选）

用于存放/读取历史记录，例如：`E:\FHD\wechat_history`（可先建好空文件夹）。

### 3. 在 Cursor 里添加 MCP 配置

- 打开 Cursor：**Settings → MCP**，或直接编辑 MCP 配置文件。
- 配置文件位置（二选一）：
  - **全局**：`C:\Users\你的用户名\.cursor\mcp.json`
  - **仅当前项目**：`e:\FHD\.cursor\mcp.json`

在 `mcpServers` 里增加 `wechat` 段（若已有其他 MCP，只追加即可）：

```json
"wechat": {
  "command": "python",
  "args": [
    "-m",
    "mcp_server_wechat",
    "--folder-path=E:\\FHD\\wechat_history"
  ]
}
```

- 把 `E:\\FHD\\wechat_history` 改成你实际用的目录（Windows 路径里反斜杠要写成 `\\`）。
- 若不需要历史记录目录，可去掉 `--folder-path=...` 这一项。

### 4. 重启 Cursor

保存配置后重启 Cursor，在 MCP 列表里把「微信」对应项设为 **Enabled**。

---

## 方案二：WeChat-MCP-Server（支持新版 NT 微信 4.0+）

**功能**：发送消息、定时发送、剪贴板输入（减少输入法问题）。支持传统版和 NT 架构微信 4.0+。

### 1. 克隆并安装依赖

```powershell
cd E:\FHD
git clone https://github.com/linxiajin08/WeChat-MCP-Server.git
cd WeChat-MCP-Server
pip install -r requirements.txt
```

### 2. 记下 mcp_server.py 的路径

例如：`E:\FHD\WeChat-MCP-Server\src\mcp_server.py`（以你克隆后的实际路径为准）。

### 3. 在 Cursor 的 mcp.json 里添加

```json
"wechat": {
  "command": "python",
  "args": [
    "E:\\FHD\\WeChat-MCP-Server\\src\\mcp_server.py"
  ]
}
```

路径请按你本机实际路径修改，且使用双反斜杠 `\\`。

### 4. 重启 Cursor 并启用该 MCP

同上，在 MCP 设置里启用「wechat」。

---

## Windows 下若 Python 启动报错

若直接写 `"command": "python"` 不生效，可改为通过 cmd 调用：

```json
"wechat": {
  "command": "cmd",
  "args": [
    "/c",
    "python",
    "-m",
    "mcp_server_wechat",
    "--folder-path=E:\\FHD\\wechat_history"
  ]
}
```

或对方案二：

```json
"wechat": {
  "command": "cmd",
  "args": [
    "/c",
    "python",
    "E:\\FHD\\WeChat-MCP-Server\\src\\mcp_server.py"
  ]
}
```

---

## 故障排除：`[WinError 2] 系统找不到指定的文件`

说明：pywechat 需要知道 `WeChat.exe` 的路径。已做两处修改：

1. **自动尝试常见路径**：若注册表里没有微信路径，会自动依次尝试：
   - `C:\Program Files\Tencent\WeChat\WeChat.exe`
   - `C:\Program Files (x86)\Tencent\WeChat\WeChat.exe`
   - `%LOCALAPPDATA%\Tencent\WeChat\WeChat.exe`

2. **环境变量 `WECHAT_PATH`**：若微信装在其他盘或自定义目录，可指定完整 exe 路径：
   - 系统属性 → 环境变量 → 用户变量 → 新建变量名 `WECHAT_PATH`，值为 `D:\xxx\WeChat.exe`（按你本机实际路径填写）。
   - 或在启动 Cursor 前在 PowerShell 里执行：`$env:WECHAT_PATH = "D:\你的路径\WeChat.exe"`

3. **写注册表（可选）**：用官方安装包安装一次微信会自动写入；若为绿色版可手动添加：
   - `Win+R` → `regedit` → 在 `HKEY_CURRENT_USER\Software` 下新建项 `Tencent\WeChat`；
   - 在 `WeChat` 下新建字符串值 `InstallPath`，数值为微信所在目录（如 `D:\WeChat`）；
   - 新建 DWORD `LANG_ID`，数值为 `4`（简体中文）。

---

## 使用注意

1. **微信必须先打开并登录**，且主窗口不要最小化到托盘。
2. 配置或路径修改后，需要**重启 Cursor** 才能生效。
3. 首次使用若报错，检查：  
   - 本机 `python` / `py` 是否在 PATH 里；  
   - 路径、JSON 引号和逗号是否正确。

配置完成后，在 Cursor 里即可通过 MCP 工具调用微信（发送消息、获取记录等，视你选的方案而定）。

---

## 方案三：纯 CV 发送（截图 + 点击/粘贴，绕过 UI 与白幕）

当 Qt 版 Weixin 或防护白幕导致方案一不可用时，可用**纯 CV**：只截屏、用 OCR 或启发式定位，再点击 + 粘贴发送，不依赖 UI 控件树。

- 项目内已提供 **`E:\FHD\wechat_cv`** 模块与 MCP 入口。
- 依赖：`pywin32`、`pyautogui`、`Pillow`；可选 `easyocr`（中文 OCR）。
- 在 `mcp.json` 的 `mcpServers` 里增加（与现有 wechat 并存）：

```json
"wechat-cv": {
  "command": "C:\\Program Files\\Python311\\python.exe",
  "args": ["E:\\FHD\\wechat_cv\\run_mcp_cv.py"]
}
```

- 使用前：**把微信窗口置于前台，并先手动打开与对方的聊天**，再在 Cursor 里调用 **wechat_cv_send_current**（发到当前聊天）或 **wechat_cv_send_to_friend**（先搜索再发）。
- 详见：`E:\FHD\wechat_cv\README.md`。
