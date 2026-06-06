using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using YamlDotNet.Serialization;
using YamlDotNet.Serialization.NamingConventions;
using XcagiDownloader.Models;

namespace XcagiDownloader.Services;

public sealed class LatestYmlClient
{
    public static HttpClientHandler CreateHandler(bool useSystemProxy, string? manualProxyUrl)
    {
        var handler = new HttpClientHandler();

        if (!string.IsNullOrWhiteSpace(manualProxyUrl))
        {
            handler.Proxy = new WebProxy(manualProxyUrl.Trim());
            handler.UseProxy = true;
        }
        else if (useSystemProxy)
        {
            handler.UseProxy = true;
            handler.DefaultProxyCredentials = CredentialCache.DefaultCredentials;
        }
        else
        {
            handler.UseProxy = false;
        }

        return handler;
    }

    public static async Task<(string RawYaml, LatestMetadata Meta)> FetchLatestAsync(
        string baseUrl,
        bool useMac,
        bool useSystemProxy,
        string? manualProxyUrl,
        string? ed25519Pem,
        CancellationToken ct)
    {
        var normalized = baseUrl.Trim().TrimEnd('/');
        var fileName = useMac ? "latest-mac.yml" : "latest.yml";
        var url = $"{normalized}/{fileName}";

        using var handler = CreateHandler(useSystemProxy, manualProxyUrl);
        using var client = new HttpClient(handler, disposeHandler: true)
        {
            Timeout = TimeSpan.FromMinutes(10)
        };

        FileLogger.Log($"GET {url}");
        var raw = await client.GetStringAsync(url, ct).ConfigureAwait(false);

        MetadataSignatureVerifier.VerifyIfConfigured(raw, ed25519Pem);

        var deserializer = new DeserializerBuilder()
            .WithNamingConvention(CamelCaseNamingConvention.Instance)
            .IgnoreUnmatchedProperties()
            .Build();

        var meta = deserializer.Deserialize<LatestMetadata>(raw)
                   ?? throw new InvalidOperationException("latest.yml 解析失败");

        if (meta.Files.Count == 0 && string.IsNullOrEmpty(meta.Path))
            throw new InvalidOperationException("latest.yml 缺少 files 或 path");

        return (raw, meta);
    }

    public static LatestFileEntry ResolvePrimaryFile(LatestMetadata meta)
    {
        if (meta.Files.Count > 0)
            return meta.Files[0];

        return new LatestFileEntry
        {
            Url = meta.Path,
            Sha512 = meta.Sha512,
            Size = 0
        };
    }

    public static string BuildArtifactUrl(string baseUrl, string relativeOrAbsolute)
    {
        if (relativeOrAbsolute.StartsWith("http://", StringComparison.OrdinalIgnoreCase)
            || relativeOrAbsolute.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
            return relativeOrAbsolute;

        var normalized = baseUrl.Trim().TrimEnd('/');
        var rel = relativeOrAbsolute.TrimStart('/');
        return $"{normalized}/{rel}";
    }
}
