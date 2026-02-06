# Video Skill Transcriber Capabilities

This is a local toolkit allowing the AI to download and transcribe videos from the web (Bilibili, YouTube, etc.) or local files.

## Available Tools (located in `tools/`)

### 1. Download Tool (`tools.download`)
- **Command**: `python -m tools.download "URL" [options]`
- **Function**: Downloads video/audio from the given URL.
- **Key Options**:
  - `--cookies-browser [chrome|edge]`: Use cookies from a local browser (crucial for premium/login-required content on YT/Bilibili).
  - `--video`: Download video file (defaults to audio-only for transcription efficiency).
- **Output**: Files are saved to the `output/` directory.

### 2. Transcribe Tool (`tools.transcribe`)
- **Command**: `python -m tools.transcribe "path/to/file.ext" [options]`
- **Function**: Transcribes audio/video files to text (.txt) and subtitles (.srt).
- **Models**:
  - Default: Local Whisper (balance of speed/accuracy).
  - `-m Qwen/Qwen3-ASR-0.6B`: Optimized for Chinese speech.
  - `-m openai`: Uses OpenAI API (requires `.env` config).

### 3. Bilibili Auth (`tools.auth`)
- **Command**: `python -m tools.auth`
- **Function**: Bilibili-specific QR Code login. (For YouTube, use `--cookies-browser`).

## Workflow Examples

**User**: "Summarize this YouTube video: https://youtu.be/..."

1. **Agent**: Download audio:
   ```bash
   python -m tools.download "https://youtu.be/..."
   ```
2. **Agent**: Transcribe the downloaded file:
   ```bash
   python -m tools.transcribe "output/video_title.m4a"
   ```
3. **Agent**: Read `output/video_title.txt` and summarize.

**User**: "Extract text from this Bilibili video using Qwen model."

1. **Agent**: Download:
   ```bash
   python -m tools.download "https://bilibili.com/..." --cookies-browser chrome
   ```
2. **Agent**: Transcribe:
   ```bash
   python -m tools.transcribe "output/video.m4a" -m Qwen/Qwen3-ASR-0.6B
   ```
