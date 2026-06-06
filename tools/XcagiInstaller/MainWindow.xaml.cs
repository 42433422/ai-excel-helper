using System.Diagnostics;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using XcagiInstaller.Services;

namespace XcagiInstaller;

public partial class MainWindow : Window
{
    private enum WizardStep
    {
        Welcome,
        License,
        Directory,
        Installing,
        Complete,
        Error,
    }

    private WizardStep _step = WizardStep.Welcome;
    private string? _setupExePath;
    private bool _hasEmbeddedPayload;
    private string _installDir = NsisSilentInstaller.DefaultInstallDirectory();
    private string? _installedAppExe;
    private CancellationTokenSource? _installCts;

    private const double ExtractPhaseMax = 12;

    private double _displayProgress;
    private double _targetProgress;
    private DispatcherTimer? _progressSmoothTimer;

    public MainWindow()
    {
        InitializeComponent();
        Loaded += MainWindow_OnLoaded;
        WelcomeAgreeCheck.Checked += SyncAgreeFromWelcome;
        WelcomeAgreeCheck.Unchecked += SyncAgreeFromWelcome;
        AgreeLicenseCheck.Checked += SyncAgreeFromLicense;
        AgreeLicenseCheck.Unchecked += SyncAgreeFromLicense;
    }

    private void MainWindow_OnLoaded(object sender, RoutedEventArgs e)
    {
        LoadLogo();
        InstallDirBox.Text = _installDir;
        WelcomePathPreview.Text = _installDir;

        var license = LicenseTextProvider.Load();
        LicenseTextBlock.Text = string.IsNullOrWhiteSpace(license)
            ? "（协议全文未内嵌）"
            : license.Length > 10000
                ? license[..10000] + "\n\n…"
                : license;

        _hasEmbeddedPayload = EmbeddedPayloadExtractor.HasEmbeddedPayload();
        if (!_hasEmbeddedPayload)
        {
            _setupExePath = PayloadLocator.FindSetupExeOnDisk("8.0.0");
            if (_setupExePath == null)
            {
                ShowError(
                    "未找到安装包。\n\n" +
                    "请使用完整发行包（build-installer.ps1 生成），\n" +
                    "或将 XCAGI-Setup-8.0.0-x64.exe 置于本程序同目录。");
                return;
            }
        }

        ApplyStepUi();
    }

    private void SyncAgreeFromWelcome(object sender, RoutedEventArgs e)
    {
        AgreeLicenseCheck.IsChecked = WelcomeAgreeCheck.IsChecked;
        UpdateWelcomeButtonState();
    }

    private void SyncAgreeFromLicense(object sender, RoutedEventArgs e)
    {
        WelcomeAgreeCheck.IsChecked = AgreeLicenseCheck.IsChecked;
        UpdateWelcomeButtonState();
        if (_step == WizardStep.License)
            NextButton.IsEnabled = AgreeLicenseCheck.IsChecked == true;
    }

    private void UpdateWelcomeButtonState()
    {
        if (_step == WizardStep.Welcome)
            NextButton.IsEnabled = WelcomeAgreeCheck.IsChecked == true;
    }

    private void LoadLogo()
    {
        try
        {
            LogoImage.Source = new BitmapImage(new Uri("pack://application:,,,/Assets/logo.png", UriKind.Absolute));
        }
        catch
        {
            LogoImage.Visibility = Visibility.Collapsed;
        }
    }

    private void WindowDrag_OnMouseDown(object sender, MouseButtonEventArgs e)
    {
        if (e.LeftButton == MouseButtonState.Pressed)
            DragMove();
    }

    private void ViewLicense_OnClick(object sender, RoutedEventArgs e)
    {
        _step = WizardStep.License;
        ApplyStepUi();
    }

    private void CustomizePath_OnClick(object sender, RoutedEventArgs e)
    {
        _step = WizardStep.Directory;
        ApplyStepUi();
    }

    private void ApplyStepUi()
    {
        WelcomePanel.Visibility = _step == WizardStep.Welcome ? Visibility.Visible : Visibility.Collapsed;
        LicensePanel.Visibility = _step == WizardStep.License ? Visibility.Visible : Visibility.Collapsed;
        DirectoryPanel.Visibility = _step == WizardStep.Directory ? Visibility.Visible : Visibility.Collapsed;
        InstallingPanel.Visibility = _step == WizardStep.Installing ? Visibility.Visible : Visibility.Collapsed;
        CompletePanel.Visibility = _step == WizardStep.Complete ? Visibility.Visible : Visibility.Collapsed;
        ErrorPanel.Visibility = _step == WizardStep.Error ? Visibility.Visible : Visibility.Collapsed;

        BackButton.Visibility = _step is WizardStep.License or WizardStep.Directory
            ? Visibility.Visible
            : Visibility.Collapsed;

        CancelButton.Visibility = _step is WizardStep.Complete or WizardStep.Error
            ? Visibility.Collapsed
            : Visibility.Visible;
        CancelButton.IsEnabled = _step != WizardStep.Installing;

        NextButton.Style = (Style)FindResource(
            _step == WizardStep.Complete ? "SuccessButtonStyle" : "HeroButtonStyle");

        switch (_step)
        {
            case WizardStep.Welcome:
                NextButton.Content = "继续";
                UpdateWelcomeButtonState();
                break;
            case WizardStep.License:
                NextButton.Content = "继续";
                NextButton.IsEnabled = AgreeLicenseCheck.IsChecked == true;
                break;
            case WizardStep.Directory:
                NextButton.Content = "安装";
                NextButton.IsEnabled = !string.IsNullOrWhiteSpace(InstallDirBox.Text);
                break;
            case WizardStep.Installing:
                NextButton.IsEnabled = false;
                BackButton.Visibility = Visibility.Collapsed;
                break;
            case WizardStep.Complete:
                NextButton.Content = "好";
                NextButton.IsEnabled = true;
                break;
            case WizardStep.Error:
                NextButton.Content = "好";
                NextButton.IsEnabled = true;
                break;
        }

        UpdateStepRails();
    }

    private void UpdateStepRails()
    {
        var dots = new[] { Dot1, Dot2, Dot3, Dot4, Dot5 };
        var idx = _step switch
        {
            WizardStep.Welcome => 0,
            WizardStep.License => 1,
            WizardStep.Directory => 2,
            WizardStep.Installing => 3,
            WizardStep.Complete => 4,
            _ => 0,
        };

        var active = FindResource("DotActive") as System.Windows.Media.Brush;
        var inactive = FindResource("DotInactive") as System.Windows.Media.Brush;
        for (var i = 0; i < dots.Length; i++)
        {
            dots[i].Fill = i == idx && _step != WizardStep.Error ? active : inactive;
            dots[i].Width = i == idx && _step != WizardStep.Error ? 7 : 6;
            dots[i].Height = dots[i].Width;
        }
    }

    private void BrowseDir_OnClick(object sender, RoutedEventArgs e)
    {
        using var dialog = new System.Windows.Forms.FolderBrowserDialog
        {
            Description = "选择安装目录",
            SelectedPath = InstallDirBox.Text,
            ShowNewFolderButton = true,
        };
        if (dialog.ShowDialog() == System.Windows.Forms.DialogResult.OK)
        {
            InstallDirBox.Text = dialog.SelectedPath;
            WelcomePathPreview.Text = dialog.SelectedPath;
        }
    }

    private async void Next_OnClick(object sender, RoutedEventArgs e)
    {
        switch (_step)
        {
            case WizardStep.Welcome:
                if (WelcomeAgreeCheck.IsChecked != true)
                    return;
                _step = WizardStep.Directory;
                ApplyStepUi();
                break;
            case WizardStep.License:
                if (AgreeLicenseCheck.IsChecked != true)
                    return;
                _step = WizardStep.Directory;
                ApplyStepUi();
                break;
            case WizardStep.Directory:
                _installDir = InstallDirBox.Text.Trim();
                WelcomePathPreview.Text = _installDir;
                await RunInstallAsync();
                break;
            case WizardStep.Complete:
                Close();
                break;
            case WizardStep.Error:
                Close();
                break;
        }
    }

    private void Back_OnClick(object sender, RoutedEventArgs e)
    {
        _step = _step switch
        {
            WizardStep.License => WizardStep.Welcome,
            WizardStep.Directory => WizardStep.Welcome,
            _ => _step,
        };
        ApplyStepUi();
    }

    private void Cancel_OnClick(object sender, RoutedEventArgs e)
    {
        if (_step == WizardStep.Installing)
            return;
        Close();
    }

    private void Close_OnClick(object sender, RoutedEventArgs e) => Close();

    private async Task RunInstallAsync()
    {
        _step = WizardStep.Installing;
        ApplyStepUi();
        _installCts = new CancellationTokenSource();

        BeginInstallProgressUi();

        if (string.IsNullOrEmpty(_setupExePath))
        {
            var extractProgress = new Progress<double>(p =>
            {
                var overall = p * ExtractPhaseMax / 100.0;
                UpdateInstallProgress(overall, DescribeExtractStatus(p));
            });

            try
            {
                _setupExePath = await PayloadLocator.ResolveSetupExeAsync(extractProgress, _installCts.Token);
            }
            catch (OperationCanceledException)
            {
                ShowError("已取消");
                return;
            }
            catch (Exception ex)
            {
                ShowError(ex.Message);
                return;
            }

            if (string.IsNullOrEmpty(_setupExePath))
            {
                ShowError("无法准备安装包");
                return;
            }
        }
        else
        {
            UpdateInstallProgress(ExtractPhaseMax, "准备开始安装…");
        }

        var installProgress = new Progress<InstallProgressUpdate>(u =>
        {
            var overall = ExtractPhaseMax + u.Percent * (100 - ExtractPhaseMax) / 100.0;
            UpdateInstallProgress(overall, u.Status);
        });

        var result = await NsisSilentInstaller.RunAsync(
            _setupExePath,
            _installDir,
            installProgress,
            _installCts.Token);

        if (!result.Success)
        {
            ShowError(result.Error ?? "安装失败");
            return;
        }

        UpdateInstallProgress(100, "安装完成");
        await Task.Delay(450).ConfigureAwait(true);

        _installedAppExe = result.AppExePath;
        var extras = ApplyPostInstallTasks();
        StopProgressSmoothTimer();
        CompletePathText.Text = result.InstallDir ?? "";
        CompleteExtrasText.Text = extras;
        _step = WizardStep.Complete;
        ApplyStepUi();
    }

    private string ApplyPostInstallTasks()
    {
        if (string.IsNullOrEmpty(_installedAppExe))
            return "";

        var notes = new List<string>();

        if (DesktopShortcutCheck.IsChecked == true)
        {
            if (PostInstallTasks.TryCreateDesktopShortcut(_installedAppExe))
                notes.Add("已创建桌面快捷方式");
            else
                notes.Add("桌面快捷方式创建失败");
        }

        PostInstallTasks.TryCreateStartMenuShortcut(_installedAppExe);

        if (RunAfterInstallCheck.IsChecked == true)
        {
            try
            {
                PostInstallTasks.TryLaunchApp(_installedAppExe);
                notes.Add("已启动 XCAGI");
            }
            catch (Exception ex)
            {
                notes.Add($"启动失败：{ex.Message}");
            }
        }

        return string.Join(" · ", notes);
    }

    private void BeginInstallProgressUi()
    {
        InstallProgress.IsIndeterminate = false;
        _displayProgress = 0;
        _targetProgress = 0;
        InstallProgress.Value = 0;
        InstallPercentText.Visibility = Visibility.Visible;
        InstallPercentText.Text = "0%";
        InstallStatusText.Text = "准备中…";
        StartProgressSmoothTimer();
    }

    private void StartProgressSmoothTimer()
    {
        _progressSmoothTimer?.Stop();
        _progressSmoothTimer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(45) };
        _progressSmoothTimer.Tick += (_, _) =>
        {
            if (_displayProgress < _targetProgress)
            {
                var gap = _targetProgress - _displayProgress;
                var step = Math.Max(0.35, gap * 0.14);
                _displayProgress = Math.Min(_targetProgress, _displayProgress + step);
            }
            else
            {
                _displayProgress = _targetProgress;
            }

            InstallProgress.Value = _displayProgress;
            InstallPercentText.Text = $"{_displayProgress:0}%";

            if (_step != WizardStep.Installing)
                StopProgressSmoothTimer();
        };
        _progressSmoothTimer.Start();
    }

    private void StopProgressSmoothTimer()
    {
        _progressSmoothTimer?.Stop();
        _progressSmoothTimer = null;
    }

    private void UpdateInstallProgress(double percent, string status)
    {
        if (!Dispatcher.CheckAccess())
        {
            Dispatcher.Invoke(() => UpdateInstallProgress(percent, status));
            return;
        }

        var clamped = Math.Clamp(percent, 0, 100);
        _targetProgress = Math.Max(_targetProgress, clamped);
        InstallStatusText.Text = status;

        if (_progressSmoothTimer == null)
            StartProgressSmoothTimer();
    }

    private static string DescribeExtractStatus(double extractPercent) =>
        extractPercent switch
        {
            < 25 => "正在解压安装包…",
            < 70 => "正在校验安装文件…",
            < 99 => "即将开始安装…",
            _ => "准备开始安装…",
        };

    private void ShowError(string message)
    {
        StopProgressSmoothTimer();
        ErrorMessageText.Text = message;
        _step = WizardStep.Error;
        ApplyStepUi();
    }

    protected override void OnClosed(EventArgs e)
    {
        StopProgressSmoothTimer();
        _installCts?.Cancel();
        base.OnClosed(e);
    }
}
