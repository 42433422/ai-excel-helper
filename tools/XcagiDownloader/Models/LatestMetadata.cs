namespace XcagiDownloader.Models;

/// <summary>electron-builder generic 发布的 latest.yml 子集。</summary>
public sealed class LatestMetadata
{
    public string Version { get; set; } = "";
    public List<LatestFileEntry> Files { get; set; } = [];
    public string Path { get; set; } = "";
    public string Sha512 { get; set; } = "";
}

public sealed class LatestFileEntry
{
    public string Url { get; set; } = "";
    public string Sha512 { get; set; } = "";
    public long Size { get; set; }
}
