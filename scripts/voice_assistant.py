"""
Free Voice Assistant for agent-desktop
Operates desktop applications using voice commands (Hindi + English).
100% Free: Uses local SpeechRecognition + Windows SAPI (pyttsx3) + agent-desktop + optional Gemini Flash.
"""

import sys
import os
import json
import re
import subprocess
import threading
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
BRIDGE_SCRIPT = REPO_ROOT / "scripts" / "agent-desktop-local.ps1"

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Initialize TTS Engine (Windows Native SAPI - 100% Free, Offline, 0ms Lag)
tts_engine = None
try:
    import pyttsx3
    tts_engine = pyttsx3.init()
    # Configure speed and volume
    tts_engine.setProperty('rate', 185)
    tts_engine.setProperty('volume', 0.95)
    # Prefer female voice (Zira) if available, else default
    voices = tts_engine.getProperty('voices')
    for v in voices:
        if "zira" in v.name.lower():
            tts_engine.setProperty('voice', v.id)
            break
except Exception as e:
    print(f"[Notice] pyttsx3 not initialized: {e}")

def speak(text: str, wait: bool = True):
    """Speak text aloud using native Windows SAPI voice and print to console."""
    print(f"\n🎙️  Agent: {text}")
    if tts_engine:
        try:
            tts_engine.say(text)
            if wait:
                tts_engine.runAndWait()
        except Exception:
            pass

def run_desktop_cmd(args: list[str]) -> dict:
    """Run agent-desktop command via local bridge script and return parsed JSON."""
    cmd = [
        "powershell.exe",
        "-ExecutionPolicy", "Bypass",
        "-File", str(BRIDGE_SCRIPT)
    ] + args
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = proc.stdout.strip()
        # Find json in output if any
        json_start = output.find('{')
        if json_start != -1:
            return json.loads(output[json_start:])
        return {"ok": proc.returncode == 0, "raw": output}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def launch_application(app_name: str) -> bool:
    """Launch or bring forward a Windows desktop application."""
    # Common app aliases
    aliases = {
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "notepad": "notepad.exe",
        "calc": "calc.exe",
        "calculator": "calc.exe",
        "paint": "mspaint.exe",
        "vs code": "code",
        "vscode": "code",
        "explorer": "explorer.exe",
        "files": "explorer.exe",
    }
    target = aliases.get(app_name.lower().strip(), app_name.strip())
    
    ps_cmd = f'''
$code = @'
using System;
using System.Runtime.InteropServices;
public class LauncherDirect {{
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct STARTUPINFO {{
        public Int32 cb;
        public string lpReserved, lpDesktop, lpTitle;
        public Int32 dwX, dwY, dwXSize, dwYSize, dwXCountChars, dwYCountChars, dwFillAttribute, dwFlags;
        public Int16 wShowWindow, cbReserved2;
        public IntPtr lpReserved2, hStdInput, hStdOutput, hStdError;
    }}
    [StructLayout(LayoutKind.Sequential)]
    public struct PROCESS_INFORMATION {{ public IntPtr hProcess, hThread; public int dwProcessId, dwThreadId; }}
    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    public static extern bool CreateProcess(string app, string cmd, IntPtr pa, IntPtr ta, bool inh, uint flags, IntPtr env, string dir, ref STARTUPINFO si, out PROCESS_INFORMATION pi);

    public static bool Launch(string target) {{
        STARTUPINFO si = new STARTUPINFO();
        si.cb = Marshal.SizeOf(si);
        si.lpDesktop = @"WinSta0\\Default";
        PROCESS_INFORMATION pi = new PROCESS_INFORMATION();
        string fullCmd = "cmd.exe /c start \\"\\" \\"" + target + "\\"";
        return CreateProcess(null, fullCmd, IntPtr.Zero, IntPtr.Zero, false, 0x08000000, IntPtr.Zero, null, ref si, out pi);
    }}
}}
'@
if (-not ([System.Management.Automation.PSTypeName]'LauncherDirect').Type) {{
    Add-Type -TypeDefinition $code
}}
[LauncherDirect]::Launch("{target}")
'''
    res = subprocess.run(["powershell.exe", "-Command", ps_cmd], capture_output=True, text=True)
    return "True" in res.stdout

def handle_voice_intent(command: str) -> bool:
    """
    Parse natural voice command (Hindi/English) and execute desktop action.
    Returns False when user wants to exit.
    """
    clean = command.strip().lower()
    print(f"\n👤 You said: \"{command}\"")

    # 1. Exit / Quit
    if re.search(r'\b(exit|quit|bye|stop|band ho jao|chalo bye)\b', clean):
        speak("Alvida! Voice Assistant band ho raha hai.")
        return False

    # 2. List Running Apps
    if re.search(r'\b(list apps|active apps|kaunse apps|running apps|apps dikhao)\b', clean):
        speak("Active applications check kar raha hoon...")
        data = run_desktop_cmd(["list-apps"])
        if data.get("ok"):
            apps = [a.get("name") for a in data.get("data", {}).get("apps", [])]
            app_str = ", ".join(apps) if apps else "Koi foreground app nahi mila."
            speak(f"Active applications hain: {app_str}")
        else:
            speak("Applications list karne me error aaya.")
        return True

    # 3. List Windows
    if re.search(r'\b(list windows|windows dikhao|open windows|saare windows)\b', clean):
        speak("Open windows check kar raha hoon...")
        data = run_desktop_cmd(["list-windows"])
        if data.get("ok"):
            windows = data.get("data", [])
            titles = [w.get("title") for w in windows if w.get("title")]
            summary = ", ".join(titles[:4]) if titles else "Koi active window nahi mila."
            speak(f"{len(windows)} windows open hain. Kuch pramukh hain: {summary}")
        else:
            speak("Windows list karne me error aaya.")
        return True

    # 4. Launch / Open Application
    open_match = re.search(r'(?:open|launch|start|kholo|chalao)\s+([a-zA-Z0-9\s]+)', clean) or \
                 re.search(r'([a-zA-Z0-9\s]+)\s+(?:kholo|open karo|launch karo)', clean)
    if open_match:
        app_name = open_match.group(1).replace("karo", "").replace("ko", "").strip()
        if app_name and app_name not in ["windows", "apps"]:
            speak(f"{app_name.capitalize()} open kar raha hoon...")
            ok = launch_application(app_name)
            if ok:
                speak(f"{app_name.capitalize()} successfully start ho gaya hai!")
            else:
                speak(f"Koshish ki par {app_name} start nahi ho paya.")
            return True

    # 5. Snapshot UI of an App
    snap_match = re.search(r'(?:snapshot|screen dekho|ui dekho|inspect)\s+([a-zA-Z0-9\s\.]+)', clean)
    if snap_match:
        target_app = snap_match.group(1).strip()
        speak(f"{target_app} ka accessibility snapshot le raha hoon...")
        res = run_desktop_cmd(["snapshot", "--app", target_app, "-i", "--compact"])
        if res.get("ok"):
            ref_count = res.get("data", {}).get("ref_count", 0)
            speak(f"{target_app} ka snapshot ready hai! Isme {ref_count} interactive buttons aur fields mile hain.")
        else:
            speak(f"{target_app} ka snapshot lene me dikkat aayi.")
        return True

    # 6. Click Element
    click_match = re.search(r'click\s+(@[a-zA-Z0-9:]+)', clean)
    if click_match:
        ref_id = click_match.group(1)
        speak(f"Ref {ref_id} par click kar raha hoon...")
        res = run_desktop_cmd(["click", ref_id])
        if res.get("ok"):
            speak("Click successful!")
        else:
            speak("Click fail ho gaya.")
        return True

    # 7. Press Key (Enter, Escape, Tab)
    if "press enter" in clean or "enter dabao" in clean:
        speak("Enter key press kar raha hoon...")
        run_desktop_cmd(["press", "Enter"])
        return True

    # 8. Fallback AI / Smart Assistant
    speak(f"Command sun li: {command}. Iska specific rule set nahi hai, par aap 'open chrome', 'list windows', ya 'list apps' bol sakte hain.")
    return True

def start_voice_loop():
    """Start the continuous microphone listening loop."""
    import speech_recognition as sr
    r = sr.Recognizer()
    r.energy_threshold = 300
    r.dynamic_energy_threshold = True

    speak("Voice Assistant active hai! Kuch bhi boliye, jaise 'Open Notepad' ya 'List Windows'.")
    print("\n[Listening on Microphone... (Press Ctrl+C to stop)]")

    try:
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.8)
            while True:
                try:
                    print("\n🎧 Sun raha hoon...")
                    audio = r.listen(source, timeout=6, phrase_time_limit=8)
                    try:
                        # Free Google Web Speech API (supports English and Hinglish)
                        text = r.recognize_google(audio, language="en-IN")
                        should_continue = handle_voice_intent(text)
                        if not should_continue:
                            break
                    except sr.UnknownValueError:
                        pass
                    except sr.RequestError as e:
                        print(f"[Error connecting to speech service: {e}]")
                except sr.WaitTimeoutError:
                    continue
    except KeyboardInterrupt:
        speak("Voice Assistant stopped. Have a good day!")
    except Exception as e:
        print(f"\n[Microphone Error: {e}]")
        speak("Microphone me error aaya. Aap text mode me command chala sakte hain.")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--text":
        # Interactive text-testing mode
        speak("Text-mode Voice Assistant started. Type 'exit' to quit.")
        while True:
            try:
                line = input("\n📝 Enter command: ").strip()
                if not line:
                    continue
                cont = handle_voice_intent(line)
                if not cont:
                    break
            except (KeyboardInterrupt, EOFError):
                break
    elif len(sys.argv) > 2 and sys.argv[1] == "--run":
        # Run one-off command
        cmd = " ".join(sys.argv[2:])
        handle_voice_intent(cmd)
    else:
        # Default microphone mode
        start_voice_loop()

if __name__ == "__main__":
    main()
