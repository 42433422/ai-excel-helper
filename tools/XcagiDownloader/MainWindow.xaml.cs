using System.Windows;
using System.Windows.Controls;
using XcagiDownloader.Models;
using XcagiDownloader.Services;

namespace XcagiDownloader;

public partial class MainWindow : Window
{
    private AppSettings _settings = new();
    private LatestMetadata? _cachedMeta;
    private LatestFileEntry? _cachedFile;
    private CancellationTokenSource? _cts;
    private readonly ResumableSetupDownloader _downloader = new();

    public MainWindow()
    {
        InitializeComponent();
        Loaded += MainWindow_OnLoaded;
        Closing += (_, _) => SaveUiToSettings();
    }

    private void MainWindow_OnLoaded(object sender, RoutedEventArgs e)
    {
        _settings = SettingsStore.Load();
        LoadUiFromSettings();
        AppendLog($"日志文件: {FileLogger.LogFilePath}");
    }

    private void LoadUiFromSettings()
    {
        PresetCombo.Items.Clear();
        foreach (var p in _settings.UrlPresets)
            PresetCombo.Items.Add(p.Name);

        var idx = Math.Clamp(_settings.SelectedPresetIndex, 0, Math.Max(0, PresetCombo.Items.Count - 1));
        PresetCombo.SelectedIndex = idx;

        BaseUrlBox.Text = _settings.CurrentBaseUrl;
        UseSystemProxyCheck.IsChecked = _settings.UseSystemProxy;
        ProxyBox.Text = _settings.ManualProxyUrl ?? "";
        PublicKeyBox.Text = _settings.Ed25519PublicKeyPem ?? "";
        DownloadDirBox.Text = _settings.DownloadDirectory;

        LaunchButton.IsEnabled =
            !string.IsNullOrEmpty(_settings.LastSetupPath) && File.Exists(_settings.LastSetupPath);
    }

    private void SaveUiToSettings()
    {
        _settings.SelectedPresetIndex = Math.Max(0, PresetCombo.SelectedIndex);
        _settings.CurrentBaseUrl = BaseUrlBox.Text.Trim();
        _settings.UseSystemProxy = UseSystemProxyCheck.IsChecked == true;
        _settings.ManualProxyUrl = string.IsNullOrWhiteSpace(ProxyBox.Text) ? null : ProxyBox.Text.Trim();
        _settings.Ed25519PublicKeyPem = string.IsNullOrWhiteSpace(PublicKeyBox.Text)
            ? null
            : PublicKeyBox.Text.Trim();
        _settings.DownloadDirectory = DownloadDirBox.Text.Trim();
        SettingsStore.Save(_settings);
    }

    private void PresetCombo_OnSelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (PresetCombo.SelectedIndex < 0)
            return;
        var preset = _settings.UrlPresets[PresetCombo.SelectedIndex];
        if (!string.IsNullOrWhiteSpace(preset.BaseUrl))
            BaseUrlBox.Text = preset.BaseUrl.Trim();
    }

    private void BrowseDir_OnClick(object sender, RoutedEventArgs e)
    {
        using var dlg = new System.Windows.Forms.FolderBrowserDialog
        {
            SelectedPath = Directory.Exists(DownloadDirBox.Text) ? DownloadDirBox.Text : "",
            Description = "选择安装包保存目录"
        };
        if (dlg.ShowDialog() == System.Windows.Forms.DialogResult.OK)
            DownloadDirBox.Text = dlg.SelectedPath;
    }

    private static void OpenInExplorer(string dir)
    {
        System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
        {
            FileName = dir,
            UseShellExecute = true
        });
    }

    private void OpenLogDir_OnClick(object sender, RoutedEventArgs e)
    {
        Directory.CreateDirectory(FileLogger.LogDirectory);
        OpenInExplorer(FileLogger.LogDirectory);
    }

    private void AppendLog(string line)
    {
        FileLogger.Log(line);
        LogBox.AppendText(line + Environment.NewLine);
        LogBox.ScrollToEnd();
    }

    private async void Fetch_OnClick(object sender, RoutedEventArgs e)
    {
        SaveUiToSettings();
        _cts = new CancellationTokenSource();
        SetBusy(true);
        MetaLabel.Text = "";
        DownloadProgress.IsIndeterminate = true;
        ProgressLabel.Text = "";

        try
        {
            var pem = string.IsNullOrWhiteSpace(PublicKeyBox.Text) ? null : PublicKeyBox.Text.Trim();
            var (_, meta) = await LatestYmlClient.FetchLatestAsync(
                    BaseUrlBox.Text.Trim(),
                    useMac: false,
                    UseSystemProxyCheck.IsChecked == true,
                    string.IsNullOrWhiteSpace(ProxyBox.Text) ? null : ProxyBox.Text.Trim(),
                    pem,
                    _cts.Token)
                .ConfigureAwait(true);

            _cachedMeta = meta;
            _cachedFile = LatestYmlClient.ResolvePrimaryFile(meta);
            var url = LatestYmlClient.BuildArtifactUrl(BaseUrlBox.Text.Trim(), _cachedFile.Url);

            MetaLabel.Text =
                $"就绪：版本 {meta.Version}，安装包 {_cachedFile.Url}（期望大小 {_cachedFile.Size} 字节）";
            AppendLog($"解析成功，artifact URL: {url}");
            DownloadButton.IsEnabled = true;
        }
        catch (Exception ex)
        {
            _cachedMeta = null;
            _cachedFile = null;
            DownloadButton.IsEnabled = false;
            AppendLog($"获取失败: {ex.Message}");
            System.Windows.MessageBox.Show(this, ex.Message, "获取版本信息失败", MessageBoxButton.OK,
                MessageBoxImage.Warning);
        }
        finally
        {
            DownloadProgress.IsIndeterminate = false;
            SetBusy(false);
        }
    }

    private async void Download_OnClick(object sender, RoutedEventArgs e)
    {
        if (_cachedFile == null)
        {
            System.Windows.MessageBox.Show(this, "请先获取版本信息。", "提示", MessageBoxButton.OK,
                MessageBoxImage.Information);
            return;
        }

        var dir = DownloadDirBox.Text.Trim();
        if (!Directory.Exists(dir))
        {
            System.Windows.MessageBox.Show(this, "保存目录不存在。", "提示", MessageBoxButton.OK,
                MessageBoxImage.Warning);
            return;
        }

        SaveUiToSettings();
        _cts = new CancellationTokenSource();
        SetBusy(true);

        var artifactUrl = LatestYmlClient.BuildArtifactUrl(BaseUrlBox.Text.Trim(), _cachedFile.Url);
        var fileName = Path.GetFileName(_cachedFile.Url.Split('?', StringSplitOptions.None)[0]);
        if (string.IsNullOrEmpty(fileName))
            fileName = $"XCAGI-Setup-{_cachedMeta?.Version ?? "unknown"}-x64.exe";

        var dest = Path.Combine(dir, fileName);

        var progress = new Progress<(long BytesReceived, long? Total)>(p =>
        {
            if (p.Total is > 0)
            {
                DownloadProgress.IsIndeterminate = false;
                DownloadProgress.Maximum = 100;
                DownloadProgress.Value = 100.0 * p.BytesReceived / p.Total.Value;
                ProgressLabel.Text = $"{p.BytesReceived:N0} / {p.Total:N0} 字节";
            }
            else
            {
                DownloadProgress.IsIndeterminate = true;
                ProgressLabel.Text = $"{p.BytesReceived:N0} 字节";
            }
        });

        try
        {
            AppendLog($"开始下载到 {dest}");
            await _downloader.DownloadAsync(
                    artifactUrl,
                    dest,
                    _cachedFile.Size > 0 ? _cachedFile.Size : null,
                    _cachedFile.Sha512,
                    UseSystemProxyCheck.IsChecked == true,
                    string.IsNullOrWhiteSpace(ProxyBox.Text) ? null : ProxyBox.Text.Trim(),
                    progress,
                    _cts.Token)
                .ConfigureAwait(true);

            _settings.LastSetupPath = dest;
            SettingsStore.Save(_settings);
            LaunchButton.IsEnabled = true;
            DownloadProgress.IsIndeterminate = false;
            DownloadProgress.Value = 100;
            ProgressLabel.Text = "完成";
            AppendLog("下载并校验完成。");
            System.Windows.MessageBox.Show(this, $"已保存:\n{dest}", "完成", MessageBoxButton.OK,
                MessageBoxImage.Information);
        }
        catch (OperationCanceledException)
        {
            AppendLog("已取消下载。");
            ProgressLabel.Text = "已取消";
        }
        catch (Exception ex)
        {
            AppendLog($"下载失败: {ex.Message}");
            System.Windows.MessageBox.Show(this, ex.Message, "下载失败", MessageBoxButton.OK,
                MessageBoxImage.Error);
        }
        finally
        {
            DownloadProgress.IsIndeterminate = false;
            SetBusy(false);
        }
    }

    private void Cancel_OnClick(object sender, RoutedEventArgs e)
    {
        _cts?.Cancel();
        AppendLog("正在取消…");
    }

    private void Launch_OnClick(object sender, RoutedEventArgs e)
    {
        var path = _settings.LastSetupPath;
        if (string.IsNullOrEmpty(path) || !File.Exists(path))
        {
            System.Windows.MessageBox.Show(this, "未找到已下载的安装包。", "提示", MessageBoxButton.OK,
                MessageBoxImage.Warning);
            return;
        }

        try
        {
            ResumableSetupDownloader.StartInstaller(path);
        }
        catch (Exception ex)
        {
            System.Windows.MessageBox.Show(this, ex.Message, "无法启动安装包", MessageBoxButton.OK,
                MessageBoxImage.Error);
        }
    }

    private void SetBusy(bool busy)
    {
        FetchButton.IsEnabled = !busy;
        DownloadButton.IsEnabled = !busy && _cachedFile != null;
        CancelButton.IsEnabled = busy;
        PresetCombo.IsEnabled = !busy;
        BaseUrlBox.IsEnabled = !busy;
        UseSystemProxyCheck.IsEnabled = !busy;
        ProxyBox.IsEnabled = !busy;
        PublicKeyBox.IsEnabled = !busy;
        DownloadDirBox.IsEnabled = !busy;
    }
}
