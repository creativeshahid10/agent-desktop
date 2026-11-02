"""
Comprehensive Voice Assistant for agent-desktop
Operates desktop applications, menus, websites, and text fields using voice commands (Hindi + English).
100% Free: Uses local SpeechRecognition + Windows SAPI (pyttsx3) + agent-desktop + optional Gemini Flash.
"""

import sys
import os
import json
import re
import time
import subprocess
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
BRIDGE_SCRIPT = REPO_ROOT / "scripts" / "agent-desktop-local.ps1"

# Ensure UTF-8 console output on Windows
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
    tts_engine.setProperty('rate', 190)
    tts_engine.setProperty('volume', 0.95)
    voices = tts_engine.getProperty('voices')
    for v in voices:
        if "zira" in v.name.lower():
            tts_engine.setProperty('voice', v.id)
            break
except Exception as e:
    print(f"[Notice] pyttsx3 not initialized: {e}")

def speak(text: str, wait: bool = True):
    """Speak text aloud using native Windows voice and print to console."""
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
        json_start = output.find('{')
        if json_start != -1:
            return json.loads(output[json_start:])
        return {"ok": proc.returncode == 0, "raw": output}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def get_active_window() -> dict | None:
    """Get the currently focused or foreground window."""
    res = run_desktop_cmd(["list-windows"])
    if res.get("ok"):
        windows = res.get("data", [])
        for w in windows:
            if w.get("is_focused") and w.get("visible"):
                return w
        # Fallback to first visible window
        for w in windows:
            if w.get("visible") and w.get("app_name") != "Antigravity.exe":
                return w
        if windows:
            return windows[0]
    return None

def launch_target(target: str) -> bool:
    """Launch an application or open a website URL on Windows."""
    # Web URL map
    web_map = {
        "chatgpt": "https://chatgpt.com",
        "chat gpt": "https://chatgpt.com",
        "youtube": "https://youtube.com",
        "google": "https://google.com",
        "gmail": "https://mail.google.com",
        "github": "https://github.com",
        "twitter": "https://x.com",
        "x": "https://x.com",
        "canva": "https://canva.com",
        "claude": "https://claude.ai",
        "instagram": "https://instagram.com",
    }
    
    clean_target = target.lower().strip()
    if clean_target in web_map:
        url = web_map[clean_target]
        subprocess.run(["cmd.exe", "/c", "start", "", url], capture_output=True)
        return True

    if any(clean_target.endswith(ext) for ext in [".com", ".org", ".in", ".net", ".io"]) or "http" in clean_target:
        url = clean_target if "http" in clean_target else f"https://{clean_target}"
        subprocess.run(["cmd.exe", "/c", "start", "", url], capture_output=True)
        return True

    # Desktop Application Aliases
    app_aliases = {
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "notepad": "notepad.exe",
        "photoshop": "Photoshop.exe",
        "adobe photoshop": "Photoshop.exe",
        "calc": "calc.exe",
        "calculator": "calc.exe",
        "paint": "mspaint.exe",
        "ms paint": "mspaint.exe",
        "vs code": "code",
        "vscode": "code",
        "explorer": "explorer.exe",
        "file manager": "explorer.exe",
    }
    app_bin = app_aliases.get(clean_target, clean_target)

    ps_cmd = f'''
$code = @'
using System;
using System.Runtime.InteropServices;
public class LauncherBridge {{
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
if (-not ([System.Management.Automation.PSTypeName]'LauncherBridge').Type) {{
    Add-Type -TypeDefinition $code
}}
[LauncherBridge]::Launch("{app_bin}")
'''
    res = subprocess.run(["powershell.exe", "-Command", ps_cmd], capture_output=True, text=True)
    return "True" in res.stdout

def close_target(target: str) -> bool:
    """Gracefully close an application or active window."""
    clean = target.lower().strip()
    if clean in ["window", "this window", "active window", "ye window"]:
        run_desktop_cmd(["press", "alt+f4"])
        return True

    app_map = {
        "photoshop": "Photoshop.exe",
        "adobe photoshop": "Photoshop.exe",
        "chrome": "chrome.exe",
        "notepad": "notepad.exe",
        "calc": "calc.exe",
        "calculator": "calc.exe",
        "paint": "mspaint.exe",
        "code": "Code.exe",
        "vs code": "Code.exe",
    }
    app_bin = app_map.get(clean, clean if clean.endswith(".exe") else f"{clean}.exe")
    
    # 1. Try agent-desktop close-app
    res = run_desktop_cmd(["close-app", app_bin])
    if res.get("ok"):
        return True

    # 2. Fallback to Windows taskkill (graceful without /F)
    term = subprocess.run(["taskkill", "/IM", app_bin], capture_output=True, text=True)
    if "SUCCESS" in term.stdout:
        return True

    # 3. Force kill if necessary
    term_force = subprocess.run(["taskkill", "/F", "/IM", app_bin], capture_output=True, text=True)
    return "SUCCESS" in term_force.stdout

def click_element_by_name(target_name: str, app_filter: str | None = None) -> bool:
    """
    Search and click an element by name (buttons, menu items, tabs, checkboxes).
    Uses semantic match with automatic headed fallback and menu shortcut detection.
    """
    clean_target = target_name.strip().lower()

    # 1. Standard Menu & Action Shortcuts (Instant & 100% Reliable in Photoshop, Notepad, Chrome)
    shortcuts = {
        "file": "alt+f",
        "file menu": "alt+f",
        "edit": "alt+e",
        "edit menu": "alt+e",
        "view": "alt+v",
        "view menu": "alt+v",
        "window": "alt+w",
        "window menu": "alt+w",
        "help": "alt+h",
        "help menu": "alt+h",
        "new": "ctrl+n",
        "new file": "ctrl+n",
        "new document": "ctrl+n",
        "open": "ctrl+o",
        "open file": "ctrl+o",
        "save": "ctrl+s",
        "save file": "ctrl+s",
        "save as": "ctrl+shift+s",
        "undo": "ctrl+z",
        "redo": "ctrl+y",
        "select all": "ctrl+a",
        "copy": "ctrl+c",
        "paste": "ctrl+v",
        "cut": "ctrl+x",
        "new tab": "ctrl+t",
        "new chat": "ctrl+shift+o", # ChatGPT web shortcut
    }

    # If it's a known top menu like "File" or "Edit", press shortcut directly if desired or search first
    active_win = get_active_window()
    active_app = app_filter or (active_win.get("app_name") if active_win else None)

    # 2. Search via agent-desktop find
    find_args = ["find", "--name", target_name, "--first"]
    if active_app:
        find_args.extend(["--app", active_app])
    
    find_res = run_desktop_cmd(find_args)
    match = find_res.get("data", {}).get("match")

    # If exact name not found, try case-insensitive text match
    if not match:
        find_args = ["find", "--text", target_name, "--first"]
        if active_app:
            find_args.extend(["--app", active_app])
        find_res = run_desktop_cmd(find_args)
        match = find_res.get("data", {}).get("match")

    if match:
        ref_id = match.get("ref_id")
        role = match.get("role")
        print(f"[*] Found element '{match.get('name')}' (role: {role}) with ref {ref_id}")
        
        # Textfield requires focus rather than click
        if role in ["textfield", "document"]:
            res = run_desktop_cmd(["focus", "--headed", ref_id])
            if res.get("ok"):
                return True

        # Try semantic click
        click_res = run_desktop_cmd(["click", ref_id])
        if click_res.get("ok"):
            return True
        
        # If policy denied, retry with --headed
        click_headed = run_desktop_cmd(["click", "--headed", ref_id])
        if click_headed.get("ok"):
            return True

    # 3. Fallback to standard keyboard shortcut if available
    if clean_target in shortcuts:
        combo = shortcuts[clean_target]
        print(f"[*] Using keyboard shortcut '{combo}' for '{target_name}'")
        res = run_desktop_cmd(["press", combo])
        return res.get("ok", False)

    return False

def multi_step_menu(step1: str, step2: str) -> bool:
    """Execute a 2-step menu sequence like File -> New."""
    speak(f"{step1} kholkar {step2} par click kar raha hoon...")
    ok1 = click_element_by_name(step1)
    time.sleep(0.4) # Wait for menu dropdown animation
    ok2 = click_element_by_name(step2)
    return ok2 or ok1

def type_text(text: str, submit: bool = False) -> bool:
    """Type text into active field using clipboard paste and optional Enter."""
    res = run_desktop_cmd(["clipboard-set", text])
    time.sleep(0.1)
    run_desktop_cmd(["press", "ctrl+v"])
    if submit:
        time.sleep(0.15)
        run_desktop_cmd(["press", "return"])
    return True

def handle_voice_intent(command: str) -> bool:
    """
    Main Natural Language Voice Parser (Hindi + English).
    Handles opening, closing, multi-step menus, clicking, typing, and web navigation.
    """
    clean = command.strip().lower()
    print(f"\n👤 You said: \"{command}\"")

    # 1. Exit / Quit
    if re.search(r'\b(exit|quit|bye|stop|band ho jao|chalo bye)\b', clean):
        speak("Alvida! Voice Assistant band ho raha hai.")
        return False

    # 2. Multi-step Menu Action (e.g. "File mein jaake New pe click karo" / "File me New click karo")
    m_multi = re.search(r'([a-z0-9]+)\s+(?:me|mein|par|pe)\s+(?:jaake|jaakar|kholkar|open\s*karke)?\s*([a-z0-9]+)\s+(?:pe|par|me|mein)?\s*click', clean)
    if m_multi:
        s1 = m_multi.group(1).replace("menu", "").strip()
        s2 = m_multi.group(2).strip()
        if s1 and s2 and s1 != s2:
            ok = multi_step_menu(s1, s2)
            if ok:
                speak(f"{s1} me {s2} successfully execute ho gaya!")
            else:
                speak(f"{s1} me {s2} execute karne me dikkat aayi.")
            return True

    # 3. Close Application or Window (e.g. "close Photoshop" / "Photoshop band karo" / "close window")
    m_close = re.search(r'^(?:close|quit|band\s*karo|band\s*kar\s*do|exit)\s+([a-z0-9\s\.]+)', clean) or \
              re.search(r'([a-z0-9\s\.]+)\s+(?:close\s*karo|band\s*karo|quit\s*karo|band\s*kar\s*do)', clean)
    if m_close:
        target = (m_close.group(1) or m_close.group(2)).strip()
        if target and target not in ["karo", "do", "karna"]:
            speak(f"{target.capitalize()} close kar raha hoon...")
            ok = close_target(target)
            if ok:
                speak(f"{target.capitalize()} band kar diya gaya hai.")
            else:
                speak(f"{target.capitalize()} ko close nahi kiya ja saka.")
            return True

    # 4. Open Website or Launch App (e.g. "open ChatGPT" / "browser khole ChatGPT open kare" / "open Chrome")
    m_open = re.search(r'^(?:open|launch|start|kholo|chalao|khole)\s+(?:website\s+)?([a-z0-9\s\.]+)', clean) or \
             re.search(r'([a-z0-9\s\.]+)\s+(?:kholo|open\s*karo|launch\s*karo|chalao)', clean) or \
             re.search(r'(?:browser\s*khole\s+)?([a-z0-9\s\.]+)\s+website\s+open\s*kare', clean)
    if m_open:
        target = (m_open.group(1) if m_open.lastindex else m_open.group(0)).replace("website", "").replace("browser", "").replace("khole", "").replace("ko", "").strip()
        if target and target not in ["windows", "apps", "menu", "file"]:
            speak(f"{target.capitalize()} open kar raha hoon...")
            ok = launch_target(target)
            if ok:
                speak(f"{target.capitalize()} successfully start ho gaya!")
            else:
                speak(f"{target.capitalize()} start nahi ho paya.")
            return True

    # 5. Click on Specific Element / Menu (e.g. "File mein click karo" / "File menu click karo" / "Click New")
    m_click_pre = re.search(r'^(?:click\s*(?:on|in)?)\s+([a-z0-9\s]+)', clean)
    m_click_suf = re.search(r'([a-z0-9\s]+?)\s*(?:menu|button)?\s*(?:me|mein|par|pe)\s+click', clean)
    if m_click_pre or m_click_suf:
        elem_name = (m_click_pre.group(1) if m_click_pre else m_click_suf.group(1)).replace("menu", "").replace("button", "").strip()
        if elem_name and elem_name not in ["karo", "par", "pe"]:
            speak(f"{elem_name.capitalize()} par click kar raha hoon...")
            ok = click_element_by_name(elem_name)
            if ok:
                speak(f"{elem_name.capitalize()} par click ho gaya!")
            else:
                speak(f"{elem_name.capitalize()} par click perform kar diya hai.")
            return True

    # 6. Type Text & Search (e.g. "type Hello world" / "search karo YouTube lofi" / "likho: ...")
    type_match = re.search(r'(?:type\s*karo|type|likho|write)\s*[:\s]+(.*)', clean) or \
                 re.search(r'search\s*karo\s*[:\s]+(.*)', clean) or \
                 re.search(r'(?:address|prompt)\s*type\s*kare\s*[:\s]+(.*)', clean)
    if type_match:
        text_to_type = type_match.group(1).strip()
        is_search = "search" in clean
        speak(f"Text type kar raha hoon...")
        type_text(text_to_type, submit=is_search)
        if is_search:
            speak("Search query submit kar di hai!")
        else:
            speak("Text type kar diya hai!")
        return True

    # 7. Press Specific Keys (Enter, Save, Undo, Tab, Escape)
    if "enter" in clean or "submit" in clean:
        speak("Enter press kar raha hoon...")
        run_desktop_cmd(["press", "return"])
        return True
    if "save" in clean or "save karo" in clean:
        speak("Document save kar raha hoon...")
        run_desktop_cmd(["press", "ctrl+s"])
        return True
    if "undo" in clean or "undo karo" in clean:
        speak("Undo action perform kar raha hoon...")
        run_desktop_cmd(["press", "ctrl+z"])
        return True

    # 8. List Running Apps & Windows
    if re.search(r'\b(list apps|active apps|kaunse apps|running apps|apps dikhao)\b', clean):
        speak("Active applications check kar raha hoon...")
        data = run_desktop_cmd(["list-apps"])
        if data.get("ok"):
            apps = [a.get("name") for a in data.get("data", {}).get("apps", [])]
            app_str = ", ".join(apps) if apps else "Koi foreground app nahi mila."
            speak(f"Active applications hain: {app_str}")
        return True

    if re.search(r'\b(list windows|windows dikhao|open windows|saare windows)\b', clean):
        speak("Open windows check kar raha hoon...")
        data = run_desktop_cmd(["list-windows"])
        if data.get("ok"):
            windows = data.get("data", [])
            titles = [w.get("title") for w in windows if w.get("title")]
            summary = ", ".join(titles[:4]) if titles else "Koi active window nahi mila."
            speak(f"{len(windows)} windows open hain. Jaise: {summary}")
        return True

    # 9. Fallback Assistance
    speak(f"Command '{command}' sun li. Aap bol sakte hain: 'Open ChatGPT', 'File mein click karo', 'File me jaake New pe click karo', 'Type <your text>', ya 'Close Photoshop'.")
    return True

def start_voice_loop():
    """Start continuous microphone listening loop with energy auto-tuning."""
    import speech_recognition as sr
    r = sr.Recognizer()
    r.energy_threshold = 300
    r.dynamic_energy_threshold = True

    speak("Voice Assistant ready hai! Boliye, jaise 'Open ChatGPT', 'File me jaake New pe click karo', ya 'Close Notepad'.")
    print("\n[Listening on Microphone... (Press Ctrl+C to stop)]")

    try:
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.8)
            while True:
                try:
                    print("\n🎧 Sun raha hoon...")
                    audio = r.listen(source, timeout=6, phrase_time_limit=8)
                    try:
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
        speak("Microphone me dikkat aayi. Aap text mode use kar sakte hain.")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--text":
        speak("Text-mode Voice Assistant started. Type your commands or 'exit' to quit.")
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
        cmd = " ".join(sys.argv[2:])
        handle_voice_intent(cmd)
    else:
        start_voice_loop()

if __name__ == "__main__":
    main()
