namespace XcagiInstaller.Services;

public static class PayloadLocator
{
    private static readonly string[] PayloadNames =
    [
        "XCAGI-Setup-*-x64.exe",
        "XCAGI-Setup-*.exe",
    ];

    public static async Task<string?> ResolveSetupExeAsync(
        IProgress<double>? extractProgress = null,
        CancellationToken cancellationToken = default)
    {
        if (EmbeddedPayloadExtractor.HasEmbeddedPayload())
        {
            return await EmbeddedPayloadExtractor
                .EnsureSetupExeAsync(extractProgress, cancellationToken)
                .ConfigureAwait(false);
        }

        return FindSetupExeOnDisk();
    }

    public static string? FindSetupExeOnDisk(string? versionHint = null)
    {
        foreach (var root in GetSearchRoots())
        {
            var found = FindInDirectory(root, versionHint);
            if (found != null)
                return found;
        }

        return null;
    }

    private static IEnumerable<string> GetSearchRoots()
    {
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var list = new List<string>();
        var baseDir = AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);

        void TryAdd(string? path)
        {
            if (string.IsNullOrWhiteSpace(path))
                return;
            var full = Path.GetFullPath(path);
            if (Directory.Exists(full) && seen.Add(full))
                list.Add(full);
        }

        TryAdd(baseDir);
        TryAdd(Path.Combine(baseDir, "_payload"));
        TryAdd(Path.Combine(baseDir, "dev-payload"));

        var dir = baseDir;
        for (var i = 0; i < 10 && !string.IsNullOrEmpty(dir); i++)
        {
            TryAdd(dir);
            var releaseDir = Path.Combine(dir, "release");
            if (Directory.Exists(releaseDir))
            {
                foreach (var sub in Directory.GetDirectories(releaseDir))
                    TryAdd(sub);
            }

            dir = Directory.GetParent(dir)?.FullName;
        }

        return list;
    }

    private static string? FindInDirectory(string root, string? versionHint)
    {
        foreach (var pattern in PayloadNames)
        {
            IEnumerable<string> matches;
            try
            {
                matches = Directory.GetFiles(root, pattern, SearchOption.TopDirectoryOnly);
            }
            catch
            {
                continue;
            }

            var list = matches
                .Where(IsNsisPayloadCandidate)
                .OrderByDescending(File.GetLastWriteTimeUtc)
                .ToList();

            if (!string.IsNullOrWhiteSpace(versionHint))
            {
                var vMatch = list.Where(f => f.Contains(versionHint, StringComparison.OrdinalIgnoreCase)).ToList();
                if (vMatch.Count > 0)
                    return vMatch[0];
            }

            if (list.Count > 0)
                return list[0];
        }

        return null;
    }

    /// <summary>
    /// 静默引擎须为裸 NSIS 包，排除 WPF 外壳（preview / XcagiInstaller）及旧命名。
    /// </summary>
    private static bool IsNsisPayloadCandidate(string path)
    {
        var name = Path.GetFileName(path);
        if (string.IsNullOrEmpty(name))
            return false;

        ReadOnlySpan<string> exclude =
        [
            "安装程序",
            "Installer",
            "preview",
            "XcagiInstaller",
            ".tmp",
        ];

        foreach (var token in exclude)
        {
            if (name.Contains(token, StringComparison.OrdinalIgnoreCase))
                return false;
        }

        return true;
    }

    public static string? FindLicenseTextOnDisk()
    {
        foreach (var root in GetSearchRoots())
        {
            foreach (var rel in new[]
                     {
                         Path.Combine("Assets", "LICENSE.zh-CN.txt"),
                         "LICENSE.zh-CN.txt",
                         Path.Combine("tools", "XcagiInstaller", "Assets", "LICENSE.zh-CN.txt"),
                         Path.Combine("..", "tools", "XcagiInstaller", "Assets", "LICENSE.zh-CN.txt"),
                         Path.Combine("..", "..", "tools", "XcagiInstaller", "Assets", "LICENSE.zh-CN.txt"),
                     })
            {
                var full = Path.GetFullPath(Path.Combine(root, rel));
                if (File.Exists(full))
                    return File.ReadAllText(full);
            }
        }

        return null;
    }
}
