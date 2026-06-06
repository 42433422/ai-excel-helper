namespace XcagiDownloader.Models;

public sealed class UrlPreset
{
    public string Name { get; set; } = "";
    public string BaseUrl { get; set; } = "";
}

public sealed class AppSettings
{
    public List<UrlPreset> UrlPresets { get; set; } =
    [
        new UrlPreset { Name = "官方 stable", BaseUrl = "https://update.xcagi.com/releases/stable/" },
        new UrlPreset { Name = "自定义", BaseUrl = "" }
    ];

    /// <summary>当前选中的预设索引（ComboBox）。</summary>
    public int SelectedPresetIndex { get; set; }

    /// <summary>实际用于请求的基址（可与预设叠加编辑）。</summary>
    public string CurrentBaseUrl { get; set; } = "https://update.xcagi.com/releases/stable/";

    public bool UseSystemProxy { get; set; } = true;

    /// <summary>手动代理，例如 http://127.0.0.1:7890；为空则仅用系统代理。</summary>
    public string? ManualProxyUrl { get; set; }

    /// <summary>与桌面 XCAGI_UPDATE_ED25519_PUBLIC_KEY 相同的 PEM；为空则跳过验签。</summary>
    public string? Ed25519PublicKeyPem { get; set; }

    public string DownloadDirectory { get; set; } =
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads");

    public string? LastSetupPath { get; set; }
}
