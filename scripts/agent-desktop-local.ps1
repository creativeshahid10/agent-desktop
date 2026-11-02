# agent-desktop Windows Runner Bridge
# Allows running agent-desktop on Windows both from interactive terminals and sandboxed runner environments.
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

$bin = "$env:APPDATA\npm\node_modules\agent-desktop\bin\agent-desktop-win32-x64.exe"
if (-not (Test-Path $bin)) {
    Write-Error "agent-desktop binary not found at $bin. Please run: npm.cmd install -g agent-desktop"
    exit 1
}

$arguments = ($CliArgs -join ' ')

$bridgeCode = @'
using System;
using System.IO;
using System.Runtime.InteropServices;

public class DesktopBridge {
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct STARTUPINFO {
        public Int32 cb;
        public string lpReserved, lpDesktop, lpTitle;
        public Int32 dwX, dwY, dwXSize, dwYSize, dwXCountChars, dwYCountChars, dwFillAttribute, dwFlags;
        public Int16 wShowWindow, cbReserved2;
        public IntPtr lpReserved2, hStdInput, hStdOutput, hStdError;
    }
    [StructLayout(LayoutKind.Sequential)]
    public struct PROCESS_INFORMATION {
        public IntPtr hProcess, hThread;
        public int dwProcessId, dwThreadId;
    }
    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    public static extern bool CreateProcess(
        string app, string cmd, IntPtr pa, IntPtr ta, bool inh, uint flags, IntPtr env, string dir,
        ref STARTUPINFO si, out PROCESS_INFORMATION pi);

    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern uint WaitForSingleObject(IntPtr hHandle, uint dwMilliseconds);

    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern bool CloseHandle(IntPtr hObject);

    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern bool GetExitCodeProcess(IntPtr hProcess, out uint lpExitCode);

    public static int Execute(string exePath, string args) {
        string tmpOut = Path.GetTempFileName();
        STARTUPINFO si = new STARTUPINFO();
        si.cb = Marshal.SizeOf(si);
        si.lpDesktop = @"WinSta0\Default";
        PROCESS_INFORMATION pi = new PROCESS_INFORMATION();
        string cmd = "cmd.exe /c \"\"" + exePath + "\" " + args + " > \"" + tmpOut + "\" 2>&1\"";
        bool ok = CreateProcess(null, cmd, IntPtr.Zero, IntPtr.Zero, false, 0x08000000, IntPtr.Zero, null, ref si, out pi);
        if (!ok) {
            Console.Error.WriteLine("Failed to launch on WinSta0\\Default: " + Marshal.GetLastWin32Error());
            return 1;
        }
        WaitForSingleObject(pi.hProcess, 60000);
        uint code;
        GetExitCodeProcess(pi.hProcess, out code);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
        try {
            string result = File.ReadAllText(tmpOut);
            Console.Write(result);
            File.Delete(tmpOut);
        } catch {}
        return (int)code;
    }
}
'@

if (-not ([System.Management.Automation.PSTypeName]'DesktopBridge').Type) {
    Add-Type -TypeDefinition $bridgeCode
}

$exitCode = [DesktopBridge]::Execute($bin, $arguments)
exit $exitCode
