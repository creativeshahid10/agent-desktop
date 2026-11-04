"""
Jam - Free Voice AI Agent for agent-desktop (v2.0)
Named 'Jam': High-sensitivity wake-word in background noise, Delhi Indian Accent (Sweet Female / Male),
persisted voice switching, crystal-clear 'Shahid Sir' pronunciation, and full desktop automation.
100% Free: Uses SpeechRecognition + gTTS (Indian Neural Voice) + agent-desktop + Pyttsx3.
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

# Import Jam TTS Engine
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from jam_tts import (
    speak,
    play_wake_chime,
    set_voice_gender,
    get_voice_gender,
    load_config
)

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
        for w in windows:
            if w.get("visible") and w.get("app_name") != "Antigravity.exe":
                return w
        if windows:
            return windows[0]
    return None

def launch_target(target: str) -> bool:
    """Launch an application or open a website URL on Windows."""
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
    
    # Try agent-desktop close-app
    res = run_desktop_cmd(["close-app", app_bin])
    if res.get("ok"):
        return True

    # Windows graceful taskkill
    term = subprocess.run(["taskkill", "/IM", app_bin], capture_output=True, text=True)
    if "SUCCESS" in term.stdout:
        return True

    # Force kill if needed
    term_force = subprocess.run(["taskkill", "/F", "/IM", app_bin], capture_output=True, text=True)
    return "SUCCESS" in term_force.stdout

def click_element_by_name(target_name: str, app_filter: str | None = None) -> bool:
    """Search and click element by name with keyboard shortcut fallback."""
    clean_target = target_name.strip().lower()

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
        "new tab": "ctrl+t",
        "new chat": "ctrl+shift+o",
    }

    active_win = get_active_window()
    active_app = app_filter or (active_win.get("app_name") if active_win else None)

    find_args = ["find", "--name", target_name, "--first"]
    if active_app:
        find_args.extend(["--app", active_app])
    
    find_res = run_desktop_cmd(find_args)
    match = find_res.get("data", {}).get("match")

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
        
        if role in ["textfield", "document"]:
            res = run_desktop_cmd(["focus", "--headed", ref_id])
            if res.get("ok"):
                return True

        click_res = run_desktop_cmd(["click", ref_id])
        if click_res.get("ok"):
            return True
        
        click_headed = run_desktop_cmd(["click", "--headed", ref_id])
        if click_headed.get("ok"):
            return True

    if clean_target in shortcuts:
        combo = shortcuts[clean_target]
        print(f"[*] Using keyboard shortcut '{combo}' for '{target_name}'")
        res = run_desktop_cmd(["press", combo])
        return res.get("ok", False)

    return False

def multi_step_menu(step1: str, step2: str) -> bool:
    """Execute a 2-step menu sequence like File -> New."""
    speak(f"Ji Shahid Sir, {step1} kholkar {step2} par click kar rahi hoon...")
    ok1 = click_element_by_name(step1)
    time.sleep(0.4)
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

# Jam Agent State Manager
class JamAgent:
    def __init__(self):
        self.name = "Jam"
        self.is_active = False
        self.last_active_time = 0.0
        self.ACTIVE_WINDOW_SEC = 14.0  # Retains conversation focus for 14 seconds

    def is_in_active_window(self) -> bool:
        if self.is_active and (time.time() - self.last_active_time < self.ACTIVE_WINDOW_SEC):
            return True
        self.is_active = False
        return False

    def activate(self):
        self.is_active = True
        self.last_active_time = time.time()

    def deactivate(self):
        self.is_active = False
        self.last_active_time = 0.0

jam = JamAgent()

# Ultra-resilient wake-word pattern (catches "Hey Jam", "Jam", and all noisy acoustic variations)
WAKE_PATTERN = r'\b(?:hey|suno|ok|oye|hello|ay|a)?\s*(?:jam|gem|gym|jan|jaam|jham|cham|exam|chem|john)\b'

def execute_desktop_action(command: str) -> bool:
    """Execute parsed action after wake word or in active conversational window."""
    clean = command.strip().lower()

    # Voice Switch Commands (Male / Female)
    if re.search(r'\b(ladki\s*ki\s*voice|female\s*voice|ladki\s*ki\s*awaaz|female\s*awaaz)\b', clean):
        set_voice_gender("female")
        jam.activate()
        return True

    if re.search(r'\b(ladke\s*ki\s*voice|male\s*voice|ladke\s*ki\s*awaaz|male\s*awaaz)\b', clean):
        set_voice_gender("male")
        jam.activate()
        return True

    if re.search(r'\b(voice\s*change|change\s*voice|awaaz\s*badlo|awaaz\s*change)\b', clean):
        new_g = "male" if get_voice_gender() == "female" else "female"
        set_voice_gender(new_g)
        jam.activate()
        return True

    # Standby / Dismissal
    if re.search(r'\b(standby|chup\s*ho\s*jao|chup|baad\s*me|theek\s*hai\s*thanks|bas\s*ho\s*gaya|bas)\b', clean):
        speak("Ji Shahid Sir, Jam standby par jaa rahi hai.", cache_key="standby_female")
        jam.deactivate()
        return True

    if re.search(r'\b(exit|quit|bye|band\s*ho\s*jao)\b', clean):
        speak("Alvida Shahid Sir! Jam shut down ho rahi hai.")
        return False

    # Multi-step Menu Action (e.g. "File mein jaake New pe click karo")
    m_multi = re.search(r'([a-z0-9]+)\s+(?:me|mein|par|pe)\s+(?:jaake|jaakar|kholkar|open\s*karke)?\s*([a-z0-9]+)\s+(?:pe|par|me|mein)?\s*click', clean)
    if m_multi:
        s1 = m_multi.group(1).replace("menu", "").strip()
        s2 = m_multi.group(2).strip()
        if s1 and s2 and s1 != s2:
            ok = multi_step_menu(s1, s2)
            if ok:
                speak(f"Ji Shahid Sir, {s1} me {s2} successfully execute ho gaya!")
            else:
                speak(f"Shahid Sir, {s1} me {s2} execute karne me dikkat aayi.")
            jam.activate()
            return True

    # Close Application or Window (e.g. "close Photoshop" / "Photoshop band karo")
    m_close = re.search(r'^(?:close|quit|band\s*karo|band\s*kar\s*do|exit)\s+([a-z0-9\s\.]+)', clean) or \
              re.search(r'([a-z0-9\s\.]+)\s+(?:close\s*karo|band\s*karo|quit\s*karo|band\s*kar\s*do)', clean)
    if m_close:
        target = (m_close.group(1) or m_close.group(2)).strip()
        if target and target not in ["karo", "do", "karna"]:
            speak(f"Ji Shahid Sir, {target.capitalize()} close kar rahi hoon...")
            ok = close_target(target)
            if ok:
                speak(f"Shahid Sir, {target.capitalize()} band kar diya gaya hai.")
            else:
                speak(f"Shahid Sir, {target.capitalize()} ko close nahi kiya ja saka.")
            jam.activate()
            return True

    # Open Website or Launch App (e.g. "open ChatGPT" / "browser khole ChatGPT open kare")
    m_open = re.search(r'^(?:open|launch|start|kholo|chalao|khole)\s+(?:website\s+)?([a-z0-9\s\.]+)', clean) or \
             re.search(r'([a-z0-9\s\.]+)\s+(?:kholo|open\s*karo|launch\s*karo|chalao)', clean) or \
             re.search(r'(?:browser\s*khole\s+)?([a-z0-9\s\.]+)\s+website\s+open\s*kare', clean)
    if m_open:
        target = (m_open.group(1) if m_open.lastindex else m_open.group(0)).replace("website", "").replace("browser", "").replace("khole", "").replace("ko", "").strip()
        if target and target not in ["windows", "apps", "menu", "file"]:
            speak(f"Ji Shahid Sir, {target.capitalize()} open kar rahi hoon...")
            ok = launch_target(target)
            if ok:
                speak(f"Shahid Sir, {target.capitalize()} successfully start ho gaya hai!")
            else:
                speak(f"Shahid Sir, {target.capitalize()} start nahi ho paya.")
            jam.activate()
            return True

    # Click on Specific Element / Menu (e.g. "File mein click karo" / "Click New")
    m_click_pre = re.search(r'^(?:click\s*(?:on|in)?)\s+([a-z0-9\s]+)', clean)
    m_click_suf = re.search(r'([a-z0-9\s]+?)\s*(?:menu|button)?\s*(?:me|mein|par|pe)\s+click', clean)
    if m_click_pre or m_click_suf:
        elem_name = (m_click_pre.group(1) if m_click_pre else m_click_suf.group(1)).replace("menu", "").replace("button", "").strip()
        if elem_name and elem_name not in ["karo", "par", "pe"]:
            speak(f"Ji Shahid Sir, {elem_name.capitalize()} par click kar rahi hoon...")
            ok = click_element_by_name(elem_name)
            if ok:
                speak(f"Shahid Sir, {elem_name.capitalize()} par click ho gaya!")
            else:
                speak(f"Shahid Sir, {elem_name.capitalize()} par click perform kar diya hai.")
            jam.activate()
            return True

    # Type Text & Search (e.g. "type Hello world" / "search karo YouTube lofi")
    type_match = re.search(r'(?:type\s*karo|type|likho|write)\s*[:\s]+(.*)', clean) or \
                 re.search(r'search\s*karo\s*[:\s]+(.*)', clean) or \
                 re.search(r'(?:address|prompt)\s*type\s*kare\s*[:\s]+(.*)', clean)
    if type_match:
        text_to_type = type_match.group(1).strip()
        is_search = "search" in clean
        speak(f"Ji Shahid Sir, text type kar rahi hoon...")
        type_text(text_to_type, submit=is_search)
        if is_search:
            speak("Shahid Sir, search query submit kar di hai!")
        else:
            speak("Shahid Sir, text type kar diya hai!")
        jam.activate()
        return True

    # Press Keys (Enter, Save, Undo)
    if "enter" in clean or "submit" in clean:
        speak("Ji Shahid Sir, Enter press kar rahi hoon...")
        run_desktop_cmd(["press", "return"])
        jam.activate()
        return True
    if "save" in clean or "save karo" in clean:
        speak("Ji Shahid Sir, document save kar rahi hoon...")
        run_desktop_cmd(["press", "ctrl+s"])
        jam.activate()
        return True
    if "undo" in clean or "undo karo" in clean:
        speak("Ji Shahid Sir, undo action perform kar rahi hoon...")
        run_desktop_cmd(["press", "ctrl+z"])
        jam.activate()
        return True

    # List Running Apps & Windows
    if re.search(r'\b(list apps|active apps|kaunse apps|running apps|apps dikhao)\b', clean):
        speak("Ji Shahid Sir, active applications check kar rahi hoon...")
        data = run_desktop_cmd(["list-apps"])
        if data.get("ok"):
            apps = [a.get("name") for a in data.get("data", {}).get("apps", [])]
            app_str = ", ".join(apps) if apps else "Koi foreground app nahi mila."
            speak(f"Shahid Sir, active applications hain: {app_str}")
        jam.activate()
        return True

    if re.search(r'\b(list windows|windows dikhao|open windows|saare windows)\b', clean):
        speak("Ji Shahid Sir, open windows check kar rahi hoon...")
        data = run_desktop_cmd(["list-windows"])
        if data.get("ok"):
            windows = data.get("data", [])
            titles = [w.get("title") for w in windows if w.get("title")]
            summary = ", ".join(titles[:4]) if titles else "Koi active window nahi mila."
            speak(f"Shahid Sir, {len(windows)} windows open hain: {summary}")
        jam.activate()
        return True

    print(f"[*] (Jam active window) Ignored non-command talk: \"{command}\"")
    return True

def handle_incoming_speech(raw_text: str) -> bool:
    """
    Filters speech: Only activates on wake-word 'Hey Jam' / 'Jam' or during active follow-up window.
    Silently ignores background chatter.
    """
    text = raw_text.strip()
    if not text:
        return True

    clean = text.lower()
    wake_match = re.search(WAKE_PATTERN, clean)

    if wake_match:
        # User called 'Jam'! Play crisp pleasant chime instantly!
        play_wake_chime()
        jam.activate()

        # Extract command after removing wake word
        cmd_after_wake = re.sub(WAKE_PATTERN, '', text, flags=re.I).strip(" ,.!\t")
        print(f"\n⚡ [Jam Activated] Heard: \"{text}\"")

        # If user ONLY said "Jam" or "Hey Jam"
        if not cmd_after_wake or len(cmd_after_wake) <= 1:
            speak("Ji Shahid Sir, Jam sun rahi hai. Boliye kya kaam karna hai?", cache_key="wake_female")
            return True

        # User gave command along with wake word (e.g. "Hey Jam, Photoshop open karo")
        return execute_desktop_action(cmd_after_wake)

    elif jam.is_in_active_window():
        print(f"\n💬 [Jam Follow-up Window] Heard: \"{text}\"")
        return execute_desktop_action(text)

    else:
        # Silent Mode: No wake word and not active -> Silently ignore background chatter
        print(f"🔇 [Jam Standby - Ignored background speech]: \"{text}\"")
        return True

def start_voice_loop():
    """Start continuous microphone listening loop with calibrated noise sensitivity."""
    import speech_recognition as sr
    r = sr.Recognizer()

    # Noise-resilient settings:
    # 1. Fixed sensitive threshold so background noise doesn't make it deaf
    r.energy_threshold = 280
    r.dynamic_energy_threshold = False
    # 2. Faster responsiveness on pauses
    r.pause_threshold = 0.5
    r.non_speaking_duration = 0.3

    speak("Namaste Shahid Sir! Main Jam hoon. Main standby par hoon, jab bhi zaroorat ho bas kahiye 'Hey Jam'.", cache_key="greeting_female")
    print("\n[Jam is listening in STANDBY mode... Say 'Hey Jam' to wake]")

    try:
        with sr.Microphone() as source:
            # Calibrate briefly (0.4s) and cap threshold to avoid deafness
            r.adjust_for_ambient_noise(source, duration=0.4)
            if r.energy_threshold > 350:
                r.energy_threshold = 300
            print(f"[*] Calibrated mic energy threshold: {r.energy_threshold}")

            while True:
                try:
                    audio = r.listen(source, timeout=6, phrase_time_limit=8)
                    try:
                        text = r.recognize_google(audio, language="en-IN")
                        should_continue = handle_incoming_speech(text)
                        if not should_continue:
                            break
                    except sr.UnknownValueError:
                        pass
                    except sr.RequestError as e:
                        print(f"[Speech recognition network notice: {e}]")
                except sr.WaitTimeoutError:
                    continue
    except KeyboardInterrupt:
        speak("Jam shut down ho rahi hai Shahid Sir. Have a great day!")
    except Exception as e:
        print(f"\n[Microphone Error: {e}]")
        speak("Microphone me dikkat aayi Shahid Sir. Aap text mode use kar sakte hain.")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--text":
        speak("Jam Text Mode active Shahid Sir. Type commands starting with 'Hey Jam' or type 'exit' to quit.")
        while True:
            try:
                line = input("\n📝 Enter text: ").strip()
                if not line:
                    continue
                cont = handle_incoming_speech(line)
                if not cont:
                    break
            except (KeyboardInterrupt, EOFError):
                break
    elif len(sys.argv) > 2 and sys.argv[1] == "--run":
        cmd = " ".join(sys.argv[2:])
        handle_incoming_speech(cmd)
    else:
        start_voice_loop()

if __name__ == "__main__":
    main()
