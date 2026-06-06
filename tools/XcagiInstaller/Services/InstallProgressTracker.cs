using System.Diagnostics;
using System.IO;

namespace XcagiInstaller.Services;

/// <summary>
/// 静默 NSIS 无进度回调时，通过安装目录体积与关键文件判断真实进度。
/// </summary>
public static class InstallProgressTracker
{
    private const long DefaultEstimatedBytes = 1_500L * 1024 * 1024;

    public static long EstimateInstalledBytes(string setupExePath, string installDirectory)
    {
        long compressed = 0;
        try
        {
            if (File.Exists(setupExePath))
                compressed = new FileInfo(setupExePath).Length;
        }
        catch
        {
            // ignore
        }

        var baseline = GetDirectorySize(installDirectory);
        var fromPayload = compressed > 0 ? (long)(compressed * 2.4) : 0;
        return Math.Max(DefaultEstimatedBytes, Math.Max(baseline + 50_000_000, fromPayload));
    }

    public static async Task MonitorInstallAsync(
        Process process,
        string installDirectory,
        long estimatedTotalBytes,
        IProgress<InstallProgressUpdate>? progress,
        CancellationToken cancellationToken = default)
    {
        var lastReported = 0;
        var started = Stopwatch.StartNew();
        var expectedMs = EstimateInstallDurationMs(estimatedTotalBytes);
        var targetBytes = Math.Max(estimatedTotalBytes, 1);

        while (!process.HasExited)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var current = GetDirectorySize(installDirectory);

            var sizePct = (int)Math.Min(99, current * 100 / targetBytes);
            var timePct = expectedMs > 0
                ? (int)Math.Min(98, started.ElapsedMilliseconds * 100 / expectedMs)
                : 0;

            // 覆盖安装时目录体积可能长期不变，用时间进度兜底，避免长时间停在 12%
            var blended = Math.Max(sizePct, timePct);
            var pct = Math.Max(lastReported, Math.Min(99, blended));
            if (pct > lastReported + 2)
                pct = lastReported + 2;

            if (pct != lastReported)
            {
                lastReported = pct;
                progress?.Report(new InstallProgressUpdate(pct, DescribeStage(installDirectory, current, pct)));
            }

            await Task.Delay(400, cancellationToken).ConfigureAwait(false);
        }

        progress?.Report(new InstallProgressUpdate(100, "安装完成"));
    }

    private static long EstimateInstallDurationMs(long estimatedTotalBytes)
    {
        // 按体积估算耗时（约 6MB/s）+ NSIS 固定开销；限制在 25s～4min
        var fromSize = (long)(estimatedTotalBytes / (6.0 * 1024 * 1024) * 1000);
        return Math.Clamp(fromSize + 15_000, 25_000, 240_000);
    }

    private static string DescribeStage(string installDirectory, long bytesWritten, int percent)
    {
        if (bytesWritten < 5_000_000)
            return "正在初始化安装…";

        var appExe = Path.Combine(installDirectory, "XCAGI.exe");
        if (!File.Exists(appExe))
            return $"正在释放文件… {percent}%";

        var asar = Path.Combine(installDirectory, "resources", "app.asar");
        if (!File.Exists(asar))
            return $"正在部署应用资源… {percent}%";

        if (percent < 85)
            return $"正在部署本地服务与前端… {percent}%";

        return "正在创建快捷方式并完成配置…";
    }

    public static long GetDirectorySize(string path)
    {
        if (!Directory.Exists(path))
            return 0;

        long total = 0;
        try
        {
            foreach (var file in Directory.EnumerateFiles(path, "*", SearchOption.AllDirectories))
            {
                try
                {
                    var info = new FileInfo(file);
                    if (info.Exists)
                        total += info.Length;
                }
                catch
                {
                    // 部分文件可能被 NSIS 占用
                }
            }
        }
        catch
        {
            // ignore
        }

        return total;
    }
}
