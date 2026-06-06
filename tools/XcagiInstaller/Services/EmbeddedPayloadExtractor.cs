using System.Reflection;

namespace XcagiInstaller.Services;

/// <summary>
/// 从单文件安装程序内嵌资源解压 NSIS 静默包到本地缓存。
/// </summary>
public static class EmbeddedPayloadExtractor
{
    public const string PayloadResourceName = "XCAGI.SetupPayload";
    public const string LicenseResourceName = "XCAGI.LicenseText";

    private static string CacheDirectory =>
        Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "XCAGI",
            "installer-cache");

    public static bool HasEmbeddedPayload()
    {
        return HostAssembly
            .GetManifestResourceNames()
            .Any(n => n.Equals(PayloadResourceName, StringComparison.Ordinal));
    }

    public static bool HasEmbeddedLicense() =>
        HostAssembly
            .GetManifestResourceNames()
            .Any(n => n.Equals(LicenseResourceName, StringComparison.Ordinal));

    public static async Task<string?> EnsureSetupExeAsync(
        IProgress<double>? progress = null,
        CancellationToken cancellationToken = default)
    {
        if (!HasEmbeddedPayload())
            return null;

        await using var stream = HostAssembly.GetManifestResourceStream(PayloadResourceName);
        if (stream == null)
            return null;

        Directory.CreateDirectory(CacheDirectory);
        var cacheExe = Path.Combine(CacheDirectory, "XCAGI-Setup-payload.exe");
        var stampFile = cacheExe + ".stamp";
        var expectedSize = stream.Length;

        if (File.Exists(cacheExe) && File.Exists(stampFile))
        {
            var stamp = await File.ReadAllTextAsync(stampFile, cancellationToken).ConfigureAwait(false);
            if (long.TryParse(stamp, out var cachedSize) && cachedSize == expectedSize &&
                new FileInfo(cacheExe).Length == expectedSize)
            {
                if (progress != null)
                {
                    for (var p = 20.0; p <= 100.0; p += 20.0)
                    {
                        progress.Report(p);
                        await Task.Delay(40, cancellationToken).ConfigureAwait(false);
                    }
                }

                return cacheExe;
            }
        }

        var tempPath = cacheExe + ".tmp";
        try
        {
            if (File.Exists(tempPath))
                File.Delete(tempPath);

            await using (var outStream = new FileStream(
                             tempPath,
                             FileMode.CreateNew,
                             FileAccess.Write,
                             FileShare.None,
                             bufferSize: 1024 * 1024,
                             useAsync: true))
            {
                var buffer = new byte[1024 * 1024];
                long total = expectedSize > 0 ? expectedSize : 1;
                long written = 0;
                int read;
                while ((read = await stream.ReadAsync(buffer, cancellationToken).ConfigureAwait(false)) > 0)
                {
                    await outStream.WriteAsync(buffer.AsMemory(0, read), cancellationToken)
                        .ConfigureAwait(false);
                    written += read;
                    if (expectedSize > 0)
                        progress?.Report(Math.Min(99, written * 100.0 / total));
                }
            }

            if (File.Exists(cacheExe))
                File.Delete(cacheExe);
            File.Move(tempPath, cacheExe);
            await File.WriteAllTextAsync(stampFile, expectedSize.ToString(), cancellationToken)
                .ConfigureAwait(false);
            progress?.Report(100);
            return cacheExe;
        }
        catch
        {
            if (File.Exists(tempPath))
            {
                try
                {
                    File.Delete(tempPath);
                }
                catch
                {
                    // ignore
                }
            }

            throw;
        }
    }

    public static string? ReadEmbeddedLicense()
    {
        if (!HasEmbeddedLicense())
            return null;

        using var stream = HostAssembly.GetManifestResourceStream(LicenseResourceName);
        if (stream == null)
            return null;
        using var reader = new StreamReader(stream);
        return reader.ReadToEnd();
    }

    /// <summary>
    /// 单文件发布时 GetExecutingAssembly() 指向宿主桩程序，内嵌资源在业务程序集内。
    /// </summary>
    private static Assembly HostAssembly => typeof(EmbeddedPayloadExtractor).Assembly;
}
