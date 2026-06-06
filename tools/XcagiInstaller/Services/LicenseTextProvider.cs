using System.IO;
using System.Reflection;
using System.Windows;

namespace XcagiInstaller.Services;

public static class LicenseTextProvider
{
    private const string PackUri = "pack://application:,,,/Assets/LICENSE.zh-CN.txt";

    public static string? Load()
    {
        var fromEmbed = EmbeddedPayloadExtractor.ReadEmbeddedLicense();
        if (!string.IsNullOrWhiteSpace(fromEmbed))
            return fromEmbed;

        var fromPack = ReadFromWpfResource();
        if (!string.IsNullOrWhiteSpace(fromPack))
            return fromPack;

        return PayloadLocator.FindLicenseTextOnDisk();
    }

    private static string? ReadFromWpfResource()
    {
        try
        {
            var streamInfo = System.Windows.Application.GetResourceStream(new Uri(PackUri, UriKind.Absolute));
            if (streamInfo?.Stream == null)
                return null;
            using var reader = new StreamReader(streamInfo.Stream);
            return reader.ReadToEnd();
        }
        catch
        {
            return null;
        }
    }
}
