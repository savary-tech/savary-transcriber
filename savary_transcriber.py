#!/usr/bin/env python3
"""
Audio Transcriber — Interactive TUI
Just run:  python3 transcriber.py
"""

import sys
import os
import platform
import subprocess
import time
import glob
import tty
import termios

# ── Platform detection ────────────────────────────────────────────────────────

IS_MAC   = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"
PY_VER   = sys.version_info

# ── Terminal colors & styles ──────────────────────────────────────────────────

RESET    = "\033[0m"
BOLD     = "\033[1m"
DIM      = "\033[2m"
GREEN    = "\033[32m"
CYAN     = "\033[36m"
YELLOW   = "\033[33m"
RED      = "\033[31m"
WHITE    = "\033[97m"
BG_CYAN  = "\033[46m"
FG_BLACK = "\033[30m"

def clr(text, *codes):
    return "".join(codes) + text + RESET

def clear():
    os.system("clear")

# ── Python version guard ──────────────────────────────────────────────────────

def check_python_version():
    """Warn if Python >= 3.13 where torch support may be missing."""
    if PY_VER >= (3, 13):
        clear()
        banner()
        print(clr(f"\n  ⚠  Python {PY_VER.major}.{PY_VER.minor} detected\n", YELLOW + BOLD))
        print("  PyTorch (required by Whisper) does not yet support Python 3.13+.")
        print("  Please install Python 3.11 or 3.12 and re-run with that version.\n")
        if IS_MAC:
            print(clr("  On Mac:", BOLD + WHITE))
            print("    brew install python@3.11")
            print("    python3.11 transcriber.py\n")
        else:
            print(clr("  On Linux:", BOLD + WHITE))
            print("    sudo apt install python3.11")
            print("    python3.11 transcriber.py\n")
        sys.exit(1)

# ── Dependency installer ──────────────────────────────────────────────────────

def pip_install(package):
    """Install a pip package, using --break-system-packages only on Linux."""
    cmd = [sys.executable, "-m", "pip", "install", package, "-q"]
    if IS_LINUX:
        cmd.append("--break-system-packages")
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def check_and_install(package, import_name=None):
    import_name = import_name or package
    try:
        __import__(import_name)
    except ImportError:
        print(clr(f"  Installing {package}...", YELLOW))
        pip_install(package)

def ensure_dependencies():
    clear()
    banner()
    check_python_version()
    print(clr("\n  Checking dependencies...\n", DIM))
    check_and_install("openai-whisper", "whisper")
    check_and_install("torch")
    check_and_install("tqdm")

# ── Supported formats ─────────────────────────────────────────────────────────

SUPPORTED_EXT = {
    ".mp3", ".mp4", ".wav", ".m4a", ".ogg", ".flac",
    ".aac", ".wma", ".mkv", ".webm", ".mov", ".avi"
}

MODELS = ["tiny", "base", "small", "medium", "large"]
MODEL_DESC = {
    "tiny":   "Fastest · lowest accuracy",
    "base":   "Fast · decent accuracy",
    "small":  "Balanced · recommended ✓",
    "medium": "Slower · high accuracy",
    "large":  "Slowest · best accuracy",
}

FORMATS = ["txt", "srt", "vtt", "tsv"]
FORMAT_DESC = {
    "txt": "Plain text transcript",
    "srt": "Subtitles with timestamps (SRT)",
    "vtt": "Web subtitles (WebVTT)",
    "tsv": "Tab-separated with timecodes",
}

# ── Keyboard input ────────────────────────────────────────────────────────────

def getch():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            ch2 = sys.stdin.read(1)
            ch3 = sys.stdin.read(1)
            return ch + ch2 + ch3
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

KEY_UP    = "\x1b[A"
KEY_DOWN  = "\x1b[B"
KEY_ENTER = "\r"
KEY_CTRL_C = "\x03"

# ── UI components ─────────────────────────────────────────────────────────────

def banner():
    print(clr("  ╔══════════════════════════════════════╗", CYAN))
    print(clr("  ║  ", CYAN) + clr("🎙  Audio Transcriber", BOLD + WHITE) + clr("             ║", CYAN))
    print(clr("  ║  ", CYAN) + clr("   Powered by OpenAI Whisper", DIM)   + clr("        ║", CYAN))
    print(clr("  ╚══════════════════════════════════════╝", CYAN))

def menu(title, options, descriptions=None, selected=0, subtitle=None):
    """Arrow-key menu. Returns chosen index."""
    while True:
        clear()
        banner()
        if subtitle:
            print(clr(f"\n  {subtitle}", DIM))
        print(clr(f"\n  {title}\n", BOLD + WHITE))
        for i, opt in enumerate(options):
            desc = descriptions[i] if descriptions else ""
            if i == selected:
                prefix = clr("  ▶ ", CYAN + BOLD)
                label  = clr(f"{opt:<14}", BG_CYAN + FG_BLACK + BOLD)
                hint   = clr(f"  {desc}", CYAN) if desc else ""
            else:
                prefix = "    "
                label  = clr(f"{opt:<14}", WHITE)
                hint   = clr(f"  {desc}", DIM) if desc else ""
            print(f"{prefix}{label}{hint}")

        print(clr("\n  ↑↓ navigate   Enter select   Ctrl+C quit\n", DIM))

        key = getch()
        if key == KEY_CTRL_C:
            quit_screen()
        elif key == KEY_UP:
            selected = (selected - 1) % len(options)
        elif key == KEY_DOWN:
            selected = (selected + 1) % len(options)
        elif key == KEY_ENTER:
            return selected

def quit_screen():
    clear()
    banner()
    print(clr("\n  Goodbye! 👋\n", CYAN))
    sys.exit(0)

def error_screen(msg):
    clear()
    banner()
    print(clr(f"\n  ✖  {msg}\n", RED + BOLD))
    print(clr("  Press any key to try again...", DIM))
    getch()

# ── File browser ──────────────────────────────────────────────────────────────

def file_picker():
    choice = menu(
        "How do you want to select the audio file?",
        ["Browse files", "Type path manually"],
        ["Navigate folders on this machine", "Enter the full path yourself"],
    )
    if choice == 1:
        return type_path()
    return browse_files(os.getcwd())


def browse_files(start_dir):
    current_dir = os.path.abspath(start_dir)
    while True:
        entries = []
        labels  = []
        descs   = []

        # Parent dir
        parent = os.path.dirname(current_dir)
        if parent != current_dir:
            entries.append(("dir", parent))
            labels.append(".. (go up)")
            descs.append(f"→ {parent}")

        # Subdirectories
        try:
            dirs = sorted([
                d for d in os.listdir(current_dir)
                if os.path.isdir(os.path.join(current_dir, d)) and not d.startswith(".")
            ])
        except PermissionError:
            dirs = []

        for d in dirs:
            entries.append(("dir", os.path.join(current_dir, d)))
            labels.append(f"📁 {d}")
            descs.append("folder")

        # Audio files
        try:
            files = sorted([
                f for f in os.listdir(current_dir)
                if os.path.isfile(os.path.join(current_dir, f))
                and os.path.splitext(f)[1].lower() in SUPPORTED_EXT
            ])
        except PermissionError:
            files = []

        for f in files:
            full = os.path.join(current_dir, f)
            size = os.path.getsize(full)
            size_str = f"{size/1024/1024:.1f} MB" if size > 1024*1024 else f"{size/1024:.0f} KB"
            entries.append(("file", full))
            labels.append(f"🎵 {f}")
            descs.append(size_str)

        if not entries:
            error_screen(f"No folders or audio files found in:\n  {current_dir}")
            current_dir = os.path.dirname(current_dir)
            continue

        choice = menu(
            f"Select a file",
            labels, descs,
            subtitle=f"📂 {current_dir}"
        )

        kind, path = entries[choice]
        if kind == "dir":
            current_dir = path
        else:
            return path


def type_path():
    while True:
        clear()
        banner()
        print(clr("\n  Enter the full path to your audio file:\n", BOLD + WHITE))
        print(clr("  Tip: you can use wildcards like /home/user/*.mp3\n", DIM))
        try:
            path = input(clr("  Path: ", CYAN)).strip()
        except (KeyboardInterrupt, EOFError):
            quit_screen()

        if "*" in path or "?" in path:
            matches = [m for m in glob.glob(path)
                       if os.path.splitext(m)[1].lower() in SUPPORTED_EXT]
            if not matches:
                error_screen(f"No matching audio files for: {path}")
                continue
            if len(matches) == 1:
                return matches[0]
            idx = menu("Multiple files found — pick one:", matches)
            return matches[idx]

        path = os.path.expanduser(path)
        if not os.path.isfile(path):
            error_screen(f"File not found: {path}")
            continue
        if os.path.splitext(path)[1].lower() not in SUPPORTED_EXT:
            error_screen(f"Unsupported file type: {os.path.splitext(path)[1]}")
            continue
        return path

# ── Output dir picker ─────────────────────────────────────────────────────────

def pick_output_dir(audio_path):
    audio_dir = os.path.dirname(os.path.abspath(audio_path))
    home_dir  = os.path.expanduser("~")
    cwd       = os.getcwd()

    options = ["Same folder as audio file", "Home directory", "Current working directory", "Type a custom path"]
    descs   = [audio_dir, home_dir, cwd, "Enter manually"]
    dirs    = [audio_dir, home_dir, cwd, None]

    choice = menu("Where should the transcript be saved?", options, descs)
    if dirs[choice] is not None:
        return dirs[choice]

    clear()
    banner()
    print(clr("\n  Enter the output directory path:\n", BOLD + WHITE))
    try:
        path = input(clr("  Directory: ", CYAN)).strip()
    except (KeyboardInterrupt, EOFError):
        quit_screen()
    path = os.path.expanduser(path)
    os.makedirs(path, exist_ok=True)
    return path

# ── Transcription ─────────────────────────────────────────────────────────────

def format_timestamp(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"

def write_plain(result, out_path):
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(result["text"].strip() + "\n")

def write_srt(result, out_path):
    with open(out_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(result["segments"], 1):
            s = format_timestamp(seg["start"]).replace(".", ",")
            e = format_timestamp(seg["end"]).replace(".", ",")
            f.write(f"{i}\n{s} --> {e}\n{seg['text'].strip()}\n\n")

def write_vtt(result, out_path):
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for seg in result["segments"]:
            s = format_timestamp(seg["start"])
            e = format_timestamp(seg["end"])
            f.write(f"{s} --> {e}\n{seg['text'].strip()}\n\n")

def write_tsv(result, out_path):
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("start\tend\ttext\n")
        for seg in result["segments"]:
            f.write(f"{seg['start']:.3f}\t{seg['end']:.3f}\t{seg['text'].strip()}\n")

WRITERS = {"txt": write_plain, "srt": write_srt, "vtt": write_vtt, "tsv": write_tsv}

def run_transcription(audio_path, model_name, language, out_path, fmt):
    import whisper

    clear()
    banner()
    print(clr("\n  ┌─────────────────────────────────────┐", CYAN))
    print(clr("  │  ", CYAN) + clr("Transcribing...                    ", WHITE + BOLD) + clr(" │", CYAN))
    print(clr("  └─────────────────────────────────────┘\n", CYAN))
    print(clr("  File    : ", DIM) + clr(os.path.basename(audio_path), WHITE))
    print(clr("  Model   : ", DIM) + clr(model_name, WHITE))
    print(clr("  Format  : ", DIM) + clr(fmt.upper(), WHITE))
    if language:
        print(clr("  Language: ", DIM) + clr(language, WHITE))
    print()
    print(clr("  Loading model (downloads once on first use)...", YELLOW))

    model = whisper.load_model(model_name)
    print(clr("  Running transcription...", YELLOW))

    start = time.time()
    options = {}
    if language:
        options["language"] = language

    result = model.transcribe(audio_path, verbose=False, **options)
    elapsed = time.time() - start

    WRITERS[fmt](result, out_path)

    print(clr("\n  ✔  Transcription complete!", GREEN + BOLD))
    print()
    print(clr("  Time      : ", DIM) + clr(f"{elapsed:.1f}s", WHITE))
    print(clr("  Language  : ", DIM) + clr(result.get("language", "unknown"), WHITE))
    print(clr("  Saved to  : ", DIM) + clr(out_path, WHITE + BOLD))
    print()

    return result

# ── Post-transcription ────────────────────────────────────────────────────────

def post_menu(result, out_path):
    options = ["Print transcript to terminal", "Transcribe another file", "Exit"]
    choice  = menu("What would you like to do next?", options)

    if choice == 0:
        clear()
        banner()
        print(clr(f"\n  📄 {os.path.basename(out_path)}\n", BOLD + CYAN))
        print(clr("  " + "─" * 56, DIM))
        words = result["text"].strip().split()
        line = ""
        for word in words:
            if len(line) + len(word) + 1 > 68:
                print("  " + line)
                line = word
            else:
                line = (line + " " + word).strip()
        if line:
            print("  " + line)
        print(clr("  " + "─" * 56, DIM))
        print(clr("\n  Press any key to continue...", DIM))
        getch()
        post_menu(result, out_path)

    elif choice == 1:
        main()

    else:
        quit_screen()

# ── Main flow ─────────────────────────────────────────────────────────────────

def main():
    ensure_dependencies()

    # 1. Pick file
    audio_path = file_picker()

    # 2. Pick model
    model_idx = menu(
        "Choose a Whisper model",
        MODELS,
        [MODEL_DESC[m] for m in MODELS],
        selected=2,
        subtitle=f"File: {os.path.basename(audio_path)}"
    )
    model_name = MODELS[model_idx]

    # 3. Language
    lang_options = ["Auto-detect", "English", "Spanish", "French", "German",
                    "Portuguese", "Italian", "Japanese", "Chinese", "Other (type it)"]
    lang_values  = [None, "English", "Spanish", "French", "German",
                    "Portuguese", "Italian", "Japanese", "Chinese", None]
    lang_idx = menu(
        "Select the audio language",
        lang_options,
        subtitle=f"File: {os.path.basename(audio_path)}"
    )
    if lang_values[lang_idx] is not None or lang_idx != len(lang_options) - 1:
        language = lang_values[lang_idx]
    else:
        clear()
        banner()
        print(clr("\n  Type the language name (e.g. Korean, Arabic, Dutch):\n", BOLD + WHITE))
        try:
            language = input(clr("  Language: ", CYAN)).strip() or None
        except (KeyboardInterrupt, EOFError):
            quit_screen()

    # 4. Output format
    fmt_idx = menu(
        "Choose output format",
        FORMATS,
        [FORMAT_DESC[f] for f in FORMATS],
        subtitle=f"File: {os.path.basename(audio_path)}"
    )
    fmt = FORMATS[fmt_idx]

    # 5. Output location
    out_dir  = pick_output_dir(audio_path)
    base     = os.path.splitext(os.path.basename(audio_path))[0]
    out_path = os.path.join(out_dir, f"{base}.{fmt}")

    # 6. Confirm
    clear()
    banner()
    print(clr("\n  Confirm settings:\n", BOLD + WHITE))
    print(clr("  File    : ", DIM) + clr(audio_path, WHITE))
    print(clr("  Model   : ", DIM) + clr(f"{model_name}  ({MODEL_DESC[model_name]})", WHITE))
    print(clr("  Language: ", DIM) + clr(language or "Auto-detect", WHITE))
    print(clr("  Format  : ", DIM) + clr(f"{fmt.upper()}  ({FORMAT_DESC[fmt]})", WHITE))
    print(clr("  Save to : ", DIM) + clr(out_path, WHITE))
    confirm = menu("", ["▶  Start transcription", "✎  Change settings", "✖  Quit"])
    if confirm == 1:
        main()
        return
    if confirm == 2:
        quit_screen()

    result = run_transcription(audio_path, model_name, language, out_path, fmt)
    post_menu(result, out_path)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(clr("\n\n  Cancelled.\n", DIM))
        sys.exit(0)
