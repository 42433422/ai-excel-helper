using System.Diagnostics;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Security.Cryptography;

namespace XcagiDownloader.Services;

public sealed class ResumableSetupDownloader
{
    public async Task DownloadAsync(
        string artifactUrl,
        string destinationPath,
        long? expectedSize,
        string expectedSha512Base64,
        bool useSystemProxy,
        string? manualProxyUrl,
        IProgress<(long BytesReceived, long? Total)>? progress,
        CancellationToken ct)
    {
        using var handler = LatestYmlClient.CreateHandler(useSystemProxy, manualProxyUrl);
        using var client = new HttpClient(handler, disposeHandler: true)
        {
            Timeout = TimeSpan.FromHours(24)
        };

        var tempPath = destinationPath + ".partial";

        await ResumeDownloadAsync(client, artifactUrl, tempPath, expectedSize, progress, ct)
            .ConfigureAwait(false);

        await VerifySha512Async(tempPath, expectedSha512Base64).ConfigureAwait(false);

        if (File.Exists(destinationPath))
            File.Delete(destinationPath);
        File.Move(tempPath, destinationPath);
        FileLogger.Log($"校验通过，已保存 {destinationPath}");
    }

    private static async Task ResumeDownloadAsync(
        HttpClient client,
        string artifactUrl,
        string tempPath,
        long? expectedTotal,
        IProgress<(long BytesReceived, long? Total)>? progress,
        CancellationToken ct)
    {
        while (true)
        {
            long resumeFrom = File.Exists(tempPath) ? new FileInfo(tempPath).Length : 0;

            using var request = new HttpRequestMessage(HttpMethod.Get, artifactUrl);
            if (resumeFrom > 0)
                request.Headers.Range = new RangeHeaderValue(resumeFrom, null);

            using var response = await client
                .SendAsync(request, HttpCompletionOption.ResponseHeadersRead, ct)
                .ConfigureAwait(false);

            if (response.StatusCode == HttpStatusCode.OK && resumeFrom > 0)
            {
                File.Delete(tempPath);
                continue;
            }

            if (response.StatusCode == HttpStatusCode.RequestedRangeNotSatisfiable)
            {
                if (File.Exists(tempPath) && expectedTotal.HasValue)
                {
                    var len = new FileInfo(tempPath).Length;
                    if (len == expectedTotal.Value)
                    {
                        progress?.Report((BytesReceived: len, Total: (long?)expectedTotal.Value));
                        return;
                    }
                }

                throw new HttpRequestException(
                    $"服务器拒绝 Range 请求 (416)，请删除临时文件后重试: {tempPath}");
            }

            response.EnsureSuccessStatusCode();

            long? total = response.Content.Headers.ContentRange?.Length
                          ?? response.Content.Headers.ContentLength
                          ?? expectedTotal;

            await StreamToFileAsync(response, tempPath, resumeFrom, total, progress, ct)
                .ConfigureAwait(false);

            return;
        }
    }

    private static async Task StreamToFileAsync(
        HttpResponseMessage response,
        string tempPath,
        long resumeFrom,
        long? total,
        IProgress<(long BytesReceived, long? Total)>? progress,
        CancellationToken ct)
    {
        var mode = resumeFrom > 0 ? FileMode.OpenOrCreate : FileMode.Create;
        await using var fs = new FileStream(tempPath, mode, FileAccess.Write, FileShare.Read);
        if (resumeFrom > 0)
            fs.Seek(0, SeekOrigin.End);

        await using var network = await response.Content.ReadAsStreamAsync(ct).ConfigureAwait(false);
        var buffer = new byte[1024 * 128];
        long transferred = fs.Length;
        progress?.Report((transferred, total));
        int read;
        while ((read = await network.ReadAsync(buffer.AsMemory(0, buffer.Length), ct).ConfigureAwait(false)) > 0)
        {
            await fs.WriteAsync(buffer.AsMemory(0, read), ct).ConfigureAwait(false);
            transferred += read;
            progress?.Report((transferred, total));
        }
    }

    private static async Task VerifySha512Async(string path, string expectedSha512Base64)
    {
        await using var fs = File.OpenRead(path);
        var hash = await SHA512.HashDataAsync(fs).ConfigureAwait(false);
        var actual = Convert.ToBase64String(hash);
        if (!string.Equals(actual, expectedSha512Base64.Trim(), StringComparison.Ordinal))
        {
            FileLogger.Log($"SHA512 不匹配: 期望 {expectedSha512Base64} 实际 {actual}");
            throw new InvalidOperationException(
                "SHA512 校验失败，文件可能损坏或被替换。临时文件保留为 .partial 便于排查。");
        }
    }

    public static void StartInstaller(string setupPath)
    {
        FileLogger.Log($"启动安装包: {setupPath}");
        Process.Start(new ProcessStartInfo
        {
            FileName = setupPath,
            UseShellExecute = true
        });
    }
}
