using Org.BouncyCastle.Crypto.Parameters;
using Org.BouncyCastle.Crypto.Signers;
using Org.BouncyCastle.OpenSsl;
using Org.BouncyCastle.Security;
using Org.BouncyCastle.Asn1.X509;

namespace XcagiDownloader.Services;

/// <summary>
/// 对齐 desktop/updater.ts 中 verifyLatestMetadataSignature：去掉 signature: ed25519: 行后对正文验签。
/// </summary>
public static class MetadataSignatureVerifier
{
    public static void VerifyIfConfigured(string rawYaml, string? pemPublicKey)
    {
        if (string.IsNullOrWhiteSpace(pemPublicKey))
            return;

        var lines = rawYaml.Replace("\r\n", "\n").Replace('\r', '\n').Split('\n');
        var sigLine = lines.FirstOrDefault(l => l.StartsWith("signature: ed25519:", StringComparison.Ordinal));
        if (sigLine == null)
            throw new InvalidOperationException("更新元数据缺少 Ed25519 二次签名（signature: ed25519:）");

        var body = string.Join(
            "\n",
            lines.Where(l => !l.StartsWith("signature: ed25519:", StringComparison.Ordinal))).TrimEnd();

        var sigB64 = sigLine["signature: ed25519:".Length..].Trim();
        var signature = Convert.FromBase64String(sigB64);

        var pem = pemPublicKey.Trim().Replace("\\n", "\n", StringComparison.Ordinal);
        using var reader = new StringReader(pem);
        var pemReader = new PemReader(reader);
        var obj = pemReader.ReadObject() ?? throw new InvalidOperationException("公钥 PEM 无法解析");

        Ed25519PublicKeyParameters pubKey = obj switch
        {
            Ed25519PublicKeyParameters ek => ek,
            SubjectPublicKeyInfo spi => (Ed25519PublicKeyParameters)PublicKeyFactory.CreateKey(spi),
            _ => throw new NotSupportedException($"不支持的 PEM 类型: {obj.GetType().Name}")
        };

        var verifier = new Ed25519Signer();
        verifier.Init(false, pubKey);
        var msg = System.Text.Encoding.UTF8.GetBytes(body);
        verifier.BlockUpdate(msg, 0, msg.Length);
        if (!verifier.VerifySignature(signature))
            throw new InvalidOperationException("更新元数据 Ed25519 二次签名校验失败");
    }
}
