# 🎙️ Audio Transcriber

Transcribe any audio or video file **locally** using [OpenAI Whisper](https://github.com/openai/whisper) — no API key, no internet connection needed after setup.

---

## Requirements

- Python 3.8+
- `ffmpeg` (install once)

```bash
sudo apt install ffmpeg
```

That's it. The script installs Python packages automatically on first run.

---

## Usage

```bash
python3 transcriber.py
```

### Basic examples

```bash
# Transcribe an MP3 (saves to meeting.txt)
python3 transcriber.py meeting.mp3

# Use a more accurate model
python3 transcriber.py interview.wav --model medium

# Force a language
python3 transcriber.py lecture.mp4 --language Spanish

# Save as SRT subtitles
python3 transcriber.py podcast.m4a --format srt

# Print transcript to terminal as well
python3 transcriber.py clip.ogg --print
```

---

## Options

| Flag | Short | Description |
|------|-------|-------------|
| `--model` | `-m` | Whisper model (default: `small`) |
| `--language` | `-l` | Force language (e.g. `English`, `French`) |
| `--output` | `-o` | Custom output file path |
| `--format` | `-f` | Output format: `txt`, `srt`, `vtt`, `tsv` |
| `--print` | `-p` | Also print transcript to terminal |
| `--list-models` | | Show model options and exit |

---

## Models

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| `tiny` | ~39M | ⚡⚡⚡⚡ | ★★☆☆☆ |
| `base` | ~74M | ⚡⚡⚡ | ★★★☆☆ |
| `small` | ~244M | ⚡⚡ | ★★★★☆ ← default |
| `medium` | ~769M | ⚡ | ★★★★★ |
| `large` | ~1.5B | 🐢 | ★★★★★+ |

Models are downloaded automatically the first time you use them and cached in `~/.cache/whisper/`.

---

## Supported Formats

Audio: `.mp3` `.wav` `.m4a` `.ogg` `.flac` `.aac` `.wma`  
Video: `.mp4` `.mkv` `.webm` `.mov` `.avi`

---

## Output Formats

- **txt** — Plain text transcript
- **srt** — Subtitle file with timestamps (for video players)
- **vtt** — WebVTT subtitles (for web/HTML5)
- **tsv** — Tab-separated with start/end times (for spreadsheets)

---

## First Run

On first run the script will:
1. Install `openai-whisper` and `torch` via pip (one-time, ~1-2 minutes)
2. Download the chosen Whisper model (one-time per model)
3. Transcribe your file

Subsequent runs are much faster.
