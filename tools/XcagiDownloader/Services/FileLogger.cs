namespace XcagiDownloader.Services;

public static class FileLogger
{
    private static readonly object Gate = new();

    public static string LogDirectory =>
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "XCAGI", "downloader");

    public static string LogFilePath => Path.Combine(LogDirectory, "downloader.log");

    public static void Log(string message)
    {
        try
        {
            Directory.CreateDirectory(LogDirectory);
            lock (Gate)
            {
                File.AppendAllText(LogFilePath, $"[{DateTime.Now:O}] {message}{Environment.NewLine}");
            }
        }
        catch
        {
            /* best effort */
        }
    }
}
