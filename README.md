# Video-Skill-Transcriber 🎥

> A universal video processing toolkit for AI Agents. Download and transcribe content from anywhere.
> Bilibili / YouTube / Local Files / ...

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

This toolkit empowers your AI Agent to:
1. **Download** videos from ANY platform supported by [yt-dlp](https://github.com/yt-dlp/yt-dlp) (YouTube, Bilibili, TikTok, etc.).
2. **Authenticate** via browser cookies (Chrome/Edge/Firefox) or generic Netscape cookie files.
3. **Transcribe** audio to text using **Local AI** (Whisper/Qwen) or **Online API** (OpenAI/DeepSeek).

## 🚀 Capabilities

- **Universal Downloader**: Works with YouTube, Bilibili, and thousands of other sites.
- **Cross-Platform**: Windows, macOS, Linux.
- **Privacy First**: Local transcription keeps your data safe.
- **Flexible Models**: `faster-whisper`, `Qwen3-ASR` (Chinese optimized), or `OpenAI API`.

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/Video-Skill-Transcriber.git
   cd Video-Skill-Transcriber
   ```

2. **Install dependencies**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
   *(Requires [FFmpeg](https://ffmpeg.org/) installed)*

3. **(Optional) Configure API**:
   Copy `.env.example` to `.env` if you want to use Online Transcription.

## 📖 Usage for Humans

### 1. Download Video (Universal)
```bash
# YouTube
python -m tools.download "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Bilibili
python -m tools.download "https://www.bilibili.com/video/BVxxx"

# Use Browser Cookies (Recommended for age-gated/premium content)
python -m tools.download "URL" --cookies-browser chrome
```

### 2. Transcribe Audio
```bash
# Local Whisper (Default)
python -m tools.transcribe "output/video.m4a"

# Local Qwen (Best for Chinese)
python -m tools.transcribe "output/video.m4a" -m Qwen/Qwen3-ASR-0.6B

# Online API
python -m tools.transcribe "output/video.m4a" -m openai
```

### 3. Bilibili Specific Tools
We include specialized tools for Bilibili power users:
```bash
# QR Code Login
python -m tools.auth

# Fetch Watch Later List
python -m tools.list --watch-later
```

## 🤖 Usage for Agents (Skills)

Give the content of `skills/VIDEO_SKILL.md` to your AI Agent (Claude/ChatGPT). It serves as a manual enabling the AI to autonomously control these tools.

## 📄 License

MIT
