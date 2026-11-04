---
name: project-jam
description: Standard operating guide, architecture, failure modes, and execution workflows for Project Jam (agent-desktop Windows automation + Jam Voice AI Agent with Delhi Indian Persona). Use when building, debugging, testing, or operating Project Jam voice agents, desktop automation bridges, or Windows UI automation.
metadata:
  version: "1.0"
  internal: true
---

# Project Jam: Standard Skill & Architecture Guide

Project Jam couples `agent-desktop` (a high-performance Rust CLI and C library for native OS accessibility tree manipulation) with `Jam` (a zero-cost, noise-resilient, Indian-accented Voice AI Agent). It enables conversational, voice-driven control of desktop applications (Photoshop, Chrome, Notepad, VS Code) on Windows.

---

## 1. Architecture & Component Map

The project separates the observe-act loop, voice orchestration, and native OS execution into four distinct layers:

```
                  ┌───────────────────────────────────────────────┐
                  │                 User Audio                    │
                  │   ("Hey Jam, File me jaake New click karo")   │
                  └───────────────────────┬───────────────────────┘
                                          │
                                          ▼
   ┌─────────────────────────────────────────────────────────────────────────────┐
   │                          Jam Voice Agent Layer                              │
   │  scripts/voice_assistant.py                                                 │
   │  - Wake-word pattern matching (Hey Jam, Jam, phonetic noise resilience)     │
   │  - Calibrated SpeechRecognition (fixed energy threshold, ambient cap)       │
   │  - Conversational state machine (JamAgent, 14s follow-up window)            │
   │  - Intent router (Menus, App Lifecycle, Web, Typing, Shortcuts)             │
   └──────────────────────┬───────────────────────────────┬──────────────────────┘
                          │                               │
                          ▼                               ▼
       ┌─────────────────────────────────────┐  ┌────────────────────────────────┐
       │      Audio Persona Engine           │  │    Windows Runner Bridge       │
       │  scripts/jam_tts.py                 │  │  scripts/agent-desktop-local.ps1│
       │  - Delhi Indian Accent (Sweet/Clear)│  │  - WinSta0\Default station     │
       │  - "Shahid Sir" honorific           │  │  - Subprocess execution        │
       │  - Pre-cached MP3s (.cache_audio/)  │  │  - Quoted argument pass-thru   │
       │  - Voice switcher (Female / Male)   │  │  - Exit code propagation       │
       │  - Offline pyttsx3 fallback         │  └───────────────┬────────────────┘
       └─────────────────────────────────────┘                  │
                                                                ▼
                                                ┌────────────────────────────────┐
                                                │    agent-desktop Core & Host   │
                                                │  npm/node_modules/.../bin/     │
                                                │  agent-desktop-win32-x64.exe   │
                                                │  - Windows UI Automation (UIA) │
                                                │  - Ref allocation & snapshot   │
                                                │  - Semantic & headed input     │
                                                └────────────────────────────────┘
```

### Component Directory

| Component | Path | Language / Runtime | Primary Responsibility |
| :--- | :--- | :--- | :--- |
| **Voice Controller** | `scripts/voice_assistant.py` | Python 3.11+ | Audio capture, wake-word filter, intent parsing, desktop execution. |
| **TTS Persona Engine**| `scripts/jam_tts.py` | Python 3.11+ | Delhi Indian female/male voice, 0ms cached responses, pyttsx3 fallback. |
| **Windows Desktop Bridge**| `scripts/agent-desktop-local.ps1`| PowerShell / C# P-Invoke | Bridges commands directly into interactive desktop (`WinSta0\Default`). |
| **Voice Config** | `config/voice_config.json` | JSON | Persistent user preferences (voice gender, name, honorific, threshold). |
| **Native Engine** | `crates/windows/`, `crates/core/` | Rust (MSRV) | OS accessibility tree traversal, snapshot generation, element refs. |
| **Launchers** | `run_voice_assistant.bat/.ps1`| Batch / PowerShell | 1-click execution for interactive user sessions. |

---

## 2. Core Invariants & Operating Rules

Any agent modifying or extending Project Jam must strictly preserve these invariants:

### A. Desktop Station Routing (`WinSta0\Default`)
- Windows isolates headless processes and background sandboxes on secondary desktops (`exebox-*`).
- `EnumWindows` and UI Automation return `0` windows when called from sandboxed desktops.
- **Rule**: All desktop interactions must route through `scripts/agent-desktop-local.ps1` or pass `lpDesktop = @"WinSta0\Default"` via Win32 `STARTUPINFO`. Never execute `agent-desktop` directly in isolated background shells without this bridge.

### B. Ref-Based Identification & Snapshot Discipline
- Element references (`@s8f3k2p9:e1`) are snapshot-scoped and depth-first allocated.
- Refs expire when the underlying UI mutates (modal opened, menu dropped, window focused).
- **Rule**: Never cache refs across actions or turns. Always resolve dynamically via `find` or fresh `snapshot`. On `STALE_REF` or `AMBIGUOUS_TARGET`, take a new snapshot.

### C. Semantic-First with Headed Fallback
- `agent-desktop` executes headless semantic calls by default without taking cursor focus.
- If an element lacks a semantic pattern or requires physical dispatch, it returns `POLICY_DENIED`.
- **Rule**: Try semantic invoke first (`click @ref`). If `POLICY_DENIED` is returned, automatically retry with `--headed` (`click --headed @ref`).

### D. Native Keyboard Accelerator Fallback
- Complex desktop applications (Adobe Photoshop, Premiere, web video players) often expose unclickable top-level menu nodes to accessibility trees.
- **Rule**: For standard application actions, always pair semantic finding with native keyboard accelerators:
  - File menu: `Alt+F`
  - New document: `Ctrl+N`
  - Save: `Ctrl+S`
  - Open file: `Ctrl+O`
  - Undo: `Ctrl+Z`
  - Close window/app: `Alt+F4`

### E. Noise-Resilient Wake Engine
- In rooms with fans, typing, or background chatter, dynamic noise calibration causes threshold drift, making the microphone deaf to "Hey Jam".
- **Rule**:
  1. Keep `energy_threshold` calibrated between 250 and 320.
  2. Set `r.dynamic_energy_threshold = False`.
  3. Include phonetic acoustic variations (`jam`, `hey jam`, `gem`, `gym`, `jan`, `jaam`, `cham`).
  4. Play instant audio chime (`winsound.Beep`) immediately on wake detection.

### F. Silent Standby & False-Positive Rejection
- When the user is on the phone or speaking to others, Jam must remain completely silent.
- **Rule**: Unless the wake-word is detected or the 14-second active follow-up window is live, incoming audio must be silently dropped without TTS speech or execution.

### G. Audio Persona & Pronunciation Standard
- Default persona is a sweet, clear Delhi Indian female voice.
- Must pronounce **"Shahid Sir"** (शाहिद सर) with native phonetics, never Americanized.
- Pre-cache common static audio responses in `.cache_audio/` for 0ms instantaneous speech.

---

## 3. Standard Workflows

### Workflow 1: Application Lifecycle (`launch` & `close`)
```python
# Launch: Routes to WinSta0\Default with fallback aliases
launch_target("photoshop")  # Launches Photoshop.exe on interactive desktop
launch_target("chatgpt")    # Launches https://chatgpt.com in default browser

# Close: Multi-tier graceful shutdown
close_target("photoshop")
# Tier 1: agent-desktop close-app Photoshop.exe
# Tier 2: Windows taskkill /IM Photoshop.exe (graceful WM_CLOSE)
# Tier 3: taskkill /F /IM Photoshop.exe (force termination if hung)
```

### Workflow 2: Semantic Element Finding & Clicking
```python
# 1. Inspect active foreground window
active_win = get_active_window()
app_name = active_win.get("app_name")

# 2. Search element by name or text
find_args = ["find", "--name", "New", "--first", "--app", app_name]
res = run_desktop_cmd(find_args)
ref_id = res["data"]["match"]["ref_id"]

# 3. Click with automatic headed fallback
click_res = run_desktop_cmd(["click", ref_id])
if click_res.get("error", {}).get("code") == "POLICY_DENIED":
    run_desktop_cmd(["click", "--headed", ref_id])
```

### Workflow 3: Multi-Step Hierarchical Menu Traversal
```python
# Handles commands like: "File mein jaake New pe click karo"
def multi_step_menu(step1="File", step2="New"):
    # Step 1: Open primary menu (semantic click + Alt+F fallback)
    click_element_by_name(step1)
    # Step 2: Allow dropdown animation to settle
    time.sleep(0.4)
    # Step 3: Trigger sub-item (semantic click + Ctrl+N fallback)
    click_element_by_name(step2)
```

### Workflow 4: Clipboard-Safe Typing & Search Submission
```python
# Direct typing can drop characters in heavy apps; use clipboard injection
def type_text(text: str, submit: bool = False):
    run_desktop_cmd(["clipboard-set", text])
    time.sleep(0.1)
    run_desktop_cmd(["press", "ctrl+v"])
    if submit:
        time.sleep(0.15)
        run_desktop_cmd(["press", "return"])
```

### Workflow 5: Voice Persona Switching
```python
# Live switching via voice or programmatic call
set_voice_gender("male")    # Switches to Microsoft David Desktop + persists
set_voice_gender("female")  # Switches to Sweet Delhi Neural Female + persists
```

---

## 4. Failure Modes & Edge-Case Matrix

| Symptom / Error Code | Root Cause | Architectural Recovery |
| :--- | :--- | :--- |
| `EnumWindows failed` | Subshell spawned on sandbox desktop station (`exebox-*`). | Route call via `scripts/agent-desktop-local.ps1` to attach `WinSta0\Default`. |
| `POLICY_DENIED` | Headless semantic action unsupported for target element. | Append `--headed` to allow physical input dispatch. |
| `STALE_REF` | UI mutated after snapshot was taken (e.g. tab switch). | Discard ref, invoke `find` or fresh `snapshot`, and retry original action. |
| `AMBIGUOUS_TARGET` | Multiple elements match the search criteria. | Scope query using `--window-id <id>` or `--root <ref>`. |
| Mic fails to hear "Hey Jam" | Dynamic energy threshold drifted too high from background fan. | Set `dynamic_energy_threshold = False` and cap threshold at `300`. |
| Cloud TTS Network Timeout | Disconnected from Google TTS endpoints. | Automatically catch exception and fall back to local Windows SAPI (`pyttsx3`). |
| Audio Playback Lock Error | Audio file handle locked by media player on Windows. | Load audio into `pygame.mixer.Sound` memory object instead of streaming from disk. |
| App ignores menu click | Photoshop or legacy Win32 app ignores UIA invoke. | Fall back to standard keyboard accelerators (`Alt+F`, `Ctrl+N`). |

---

## 5. Development & Verification Protocols

When verifying changes to Project Jam, use these commands:

```bash
# 1. Run single-shot voice command test
.\.venv\Scripts\python.exe scripts/voice_assistant.py --run "Hey Jam, list windows"

# 2. Test interactive console mode (no mic needed)
.\.venv\Scripts\python.exe scripts/voice_assistant.py --text

# 3. Test TTS audio output and voice switcher
.\.venv\Scripts\python.exe -c "import sys; sys.path.append('scripts'); import jam_tts; jam_tts.speak('Ji Shahid Sir, test complete hai.')"

# 4. Scoped Rust build check (Windows host set)
cargo check -p agent-desktop-core -p agent-desktop-windows -p agent-desktop -p agent-desktop-ffi

# 5. Scoped Rust library tests
cargo test -p agent-desktop-core -p agent-desktop-windows -p agent-desktop -p agent-desktop-ffi --lib
```
