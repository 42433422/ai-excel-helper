using System.Diagnostics;

namespace XcagiInstaller.Services;

public sealed class NsisSilentInstaller
{
    public static string DefaultInstallDirectory()
    {
        var local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        return Path.Combine(local, "Programs", "XCAGI");
    }

    /// <summary>
    /// 静默运行 NSIS：/S 静默，/D= 必须为最后一个参数且路径勿加引号。
    /// </summary>
    public static async Task<InstallResult> RunAsync(
        string setupExePath,
        string installDirectory,
        IProgress<InstallProgressUpdate>? progress = null,
        CancellationToken cancellationToken = default)
    {
        if (!File.Exists(setupExePath))
            return InstallResult.Fail($"未找到安装包：{setupExePath}");

        var dir = installDirectory.Trim().TrimEnd('\\', '/');
        if (string.IsNullOrWhiteSpace(dir))
            return InstallResult.Fail("安装目录无效。");

        try
        {
            Directory.CreateDirectory(dir);
        }
        catch (Exception ex)
        {
            return InstallResult.Fail($"无法创建目录：{ex.Message}");
        }

        var args = $"/S /D={dir}";
        var psi = new ProcessStartInfo
        {
            FileName = setupExePath,
            Arguments = args,
            UseShellExecute = false,
            CreateNoWindow = true,
            WindowStyle = ProcessWindowStyle.Hidden,
        };

        using var process = new Process { StartInfo = psi, EnableRaisingEvents = true };
        try
        {
            if (!process.Start())
                return InstallResult.Fail("无法启动安装进程。");
        }
        catch (Exception ex)
        {
            return InstallResult.Fail($"启动失败：{ex.Message}");
        }

        var estimated = InstallProgressTracker.EstimateInstalledBytes(setupExePath, dir);

        try
        {
            var monitor = InstallProgressTracker.MonitorInstallAsync(
                process,
                dir,
                estimated,
                progress,
                cancellationToken);
            await process.WaitForExitAsync(cancellationToken).ConfigureAwait(false);
            await monitor.ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            try
            {
                if (!process.HasExited)
                    process.Kill(entireProcessTree: true);
            }
            catch
            {
                // ignore
            }

            return InstallResult.Fail("安装已取消。");
        }

        if (process.ExitCode != 0)
            return InstallResult.Fail($"安装程序退出码 {process.ExitCode}。");

        var appExe = Path.Combine(dir, "XCAGI.exe");
        if (!File.Exists(appExe))
        {
            var found = Directory.EnumerateFiles(dir, "XCAGI.exe", SearchOption.AllDirectories).FirstOrDefault();
            if (found != null)
                appExe = found;
        }

        return InstallResult.Ok(dir, File.Exists(appExe) ? appExe : null);
    }
}

public readonly record struct InstallResult(bool Success, string? InstallDir, string? AppExePath, string? Error)
{
    public static InstallResult Ok(string dir, string? appExe) => new(true, dir, appExe, null);
    public static InstallResult Fail(string error) => new(false, null, null, error);
}
