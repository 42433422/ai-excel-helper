using System.Text.Json;
using XcagiDownloader.Models;

namespace XcagiDownloader.Services;

public static class SettingsStore
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase
    };

    public static string SettingsPath =>
        Path.Combine(FileLogger.LogDirectory, "settings.json");

    public static AppSettings Load()
    {
        try
        {
            if (!File.Exists(SettingsPath))
                return new AppSettings();
            var json = File.ReadAllText(SettingsPath);
            var s = JsonSerializer.Deserialize<AppSettings>(json, JsonOptions);
            return s ?? new AppSettings();
        }
        catch (Exception ex)
        {
            FileLogger.Log($"加载设置失败: {ex.Message}");
            return new AppSettings();
        }
    }

    public static void Save(AppSettings settings)
    {
        Directory.CreateDirectory(FileLogger.LogDirectory);
        var json = JsonSerializer.Serialize(settings, JsonOptions);
        File.WriteAllText(SettingsPath, json);
    }
}
