# 虚拟麦克风驱动安装指南

## 问题说明
自动下载失败，需要手动下载安装虚拟麦克风驱动。

## 推荐方案：VB-Audio VoiceMeeter

VoiceMeeter 是 VB-Audio 开发的免费虚拟音频混音器，包含虚拟麦克风功能。

### 方案一：官方网站下载（推荐）

1. **访问官网**：
   - 打开浏览器访问：https://vb-audio.com/
   - 或访问：https://www.voicemeeter.com/

2. **下载 VoiceMeeter**：
   - 点击 "Download" 按钮
   - 选择 "Voicemeeter Standard"（标准版，免费）
   - 或 "Voicemeeter Banana"（增强版，功能更多）

3. **安装步骤**：
   - 解压下载的 ZIP 文件
   - 右键点击 `setup.exe` 或 `VoicemeeterSetup.exe`
   - 选择 "以管理员身份运行"
   - 按照安装向导完成安装
   - **重启电脑**（重要！）

4. **验证安装**：
   - 打开 Windows 声音设置
   - 在 "录音设备" 中应该能看到 "VoiceMeeter Output" 或 "VoiceMeeter Aux Output"
   - 这就是虚拟麦克风

### 方案二：国内下载源

如果官网下载慢，可以尝试以下国内软件园：

1. **华军软件园**：
   - https://www.onlinedown.net/soft/20145941.htm

2. **非凡软件站**：
   - 搜索 "VoiceMeeter" 或 "VB-Audio"

3. **百度网盘**（需要提取码）：
   - 搜索相关资源

### 方案三：使用 Windows 自带功能（临时方案）

如果无法安装第三方驱动，可以使用 Windows 自带的 "立体声混音"：

1. **启用立体声混音**：
   - 右键点击任务栏音量图标 → 选择 "声音"
   - 切换到 "录制" 选项卡
   - 右键空白处 → 勾选 "显示禁用的设备"
   - 找到 "立体声混音" → 右键 → "启用"
   - 设为默认设备

2. **配置电话业务员使用立体声混音**：
   - 修改 `vb_cable_output.py` 中的设备名称
   - 将 `VB_CABLE_DEVICE_NAME = "CABLE Input"` 改为
   - `VB_CABLE_DEVICE_NAME = "立体声混音"` 或 `VB_CABLE_DEVICE_NAME = "Stereo Mix"`

## 安装后测试

安装完成后，运行以下命令测试：

```bash
curl -s http://127.0.0.1:5000/api/mod/sz-qsm-pro/phone-agent/status | python -m json.tool
```

检查 `vb_cable_available` 是否变为 `true`。

## 注意事项

1. **管理员权限**：安装虚拟音频驱动必须使用管理员权限
2. **重启电脑**：安装后必须重启才能生效
3. **数字签名**：某些驱动可能没有微软数字签名，安装时需要确认
4. **杀毒软件**：安装时可能被杀毒软件拦截，需要暂时关闭或允许

## 替代方案说明

如果暂时无法安装虚拟麦克风，电话业务员的其他功能仍可正常使用：
- ✅ 窗口监控（检测微信电话）
- ✅ 音频采集（录音）
- ✅ ASR 语音识别（Whisper）
- ✅ 意图识别
- ✅ 回复生成
- ⚠️ TTS 播放（只能保存到文件，无法输出到虚拟麦克风）
