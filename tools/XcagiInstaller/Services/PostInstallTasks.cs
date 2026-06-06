using System.Diagnostics;

namespace XcagiInstaller.Services;

public static class PostInstallTasks
{
    public static bool TryCreateDesktopShortcut(string targetExe, string shortcutName = "XCAGI")
    {
        var desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
        var linkPath = Path.Combine(desktop, $"{shortcutName}.lnk");
        return TryCreateShellLink(linkPath, targetExe, shortcutName);
    }

    public static bool TryCreateStartMenuShortcut(string targetExe, string shortcutName = "XCAGI")
    {
        var programs = Environment.GetFolderPath(Environment.SpecialFolder.Programs);
        var folder = Path.Combine(programs, shortcutName);
        Directory.CreateDirectory(folder);
        var linkPath = Path.Combine(folder, $"{shortcutName}.lnk");
        return TryCreateShellLink(linkPath, targetExe, shortcutName);
    }

    public static void TryLaunchApp(string targetExe, string arguments = "--fresh-install")
    {
        Process.Start(new ProcessStartInfo(targetExe, arguments)
        {
            UseShellExecute = true,
            WorkingDirectory = Path.GetDirectoryName(targetExe) ?? "",
        });
    }

    private static bool TryCreateShellLink(string linkPath, string targetExe, string description)
    {
        if (!File.Exists(targetExe))
            return false;

        try
        {
            var shellType = Type.GetTypeFromProgID("WScript.Shell");
            if (shellType == null)
                return false;

            dynamic shell = Activator.CreateInstance(shellType)!;
            dynamic shortcut = shell.CreateShortcut(linkPath);
            shortcut.TargetPath = targetExe;
            shortcut.WorkingDirectory = Path.GetDirectoryName(targetExe) ?? "";
            shortcut.Description = description;
            shortcut.IconLocation = $"{targetExe},0";
            shortcut.Save();
            return File.Exists(linkPath);
        }
        catch
        {
            return false;
        }
    }
}
