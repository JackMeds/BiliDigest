# Video-Skill-Transcriber 🧠

> **More than a downloader. This is the "Eyes" and "Ears" for your AI Agent.**
> Enable Claude/ChatGPT/AutoGPT to understand video content, generate summaries, build mind maps, and extract knowledge.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Release](https://img.shields.io/github/v/release/JackMeds/Video-Skill-Transcriber)](https://github.com/JackMeds/Video-Skill-Transcriber/releases)

[中文说明 (Chinese README)](README_zh-CN.md)

---

## Table of Contents

- [Introduction](#introduction)
- [Why Use This?](#why-use-this)
- [Core Capabilities](#core-capabilities)
- [AI Learning Scenarios](#ai-learning-scenarios)
- [Installation](#installation)
- [Usage (CLI)](#usage-cli)
- [Bilibili Special Workflow](#bilibili-special-workflow)
- [For AI Agents (Skills)](#for-ai-agents-skills)
- [License](#license)

---

## Introduction

In the age of AI, video remains a "black box" for text-based models. **Video-Skill-Transcriber** bridges this gap. It is a specialized toolkit designed to empower AI Agents to autonomously access, download, and transcribe video content from the web (Bilibili, YouTube, etc.) or local files.

## Why Use This?

The goal isn't just to get an `.mp4` or `.txt` file—it's to **unlock knowledge**.
By integrating this tool as a Skill, your AI Agent can:

1.  **"Watch" Deep Content**: Access hours of lectures, tutorials, and talks.
2.  **"Hear" Every Detail**: Use state-of-the-art ASR models (Whisper/Qwen/OpenAI) for high-fidelity transcripts.
3.  **"Synthesize" Knowledge**: Turn unstructured video into summaries, knowledge graphs, and study notes.

## Core Capabilities

- **🎥 Universal Ingestion**: Based on [yt-dlp](https://github.com/yt-dlp/yt-dlp), supporting thousands of sites (Bilibili, YouTube, TikTok...).
- **🤖 Agent-Ready Skills**: Provides a standardized `skills/` interface for immediate integration with agent frameworks.
- **📚 Batch Learning**: Automate the processing of playlists or "Watch Later" lists.
- **🔒 Privacy First**: run fully local inference (Whisper/Qwen3-ASR) to keep your learning data private.

## AI Learning Scenarios

Imagine telling your AI Agent:

*   **🎓 Auto-Summarization**: "Download this 2-hour lecture on Deep Learning and summarize the key concepts in bullet points."
*   **🗺️ Knowledge Graphing**: "Process this playlist about 'RAG Architecture' and build a technology roadmap."
*   **📝 Meeting Minutes**: "Transcribe this interview recording and extract action items."
*   **🔍 Cross-Lingual Study**: "Download this English tutorial, transcribe it, and translate the summary to Chinese."

## Demo

![Terminal Demo](assets/terminal_demo.png)

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/JackMeds/Video-Skill-Transcriber.git
    cd Video-Skill-Transcriber
    ```

2.  **Install dependencies**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    ```
    *(Requires [FFmpeg](https://ffmpeg.org/) installed)*

3.  **(Optional) Configure API**:
    Copy `.env.example` to `.env` if you want to use Online Transcription (OpenAI, DeepSeek, etc.).

## Usage (CLI)

All tools are located in the `tools/` package and can be run with `python -m tools.xxx`.

### 1. Ingest Video Content

```bash
# YouTube/General
python -m tools.download "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Use Browser Cookies (Recommended for age-gated/premium content)
python -m tools.download "URL" --cookies-browser chrome
```

### 2. Transcribe to Knowledge

```bash
# Local Whisper (Default - Balanced)
python -m tools.transcribe "output/video.m4a"

# Local Qwen3-ASR (Best for Multilingual/Chinese)
python -m tools.transcribe "output/video.m4a" -m Qwen/Qwen3-ASR-0.6B

# Online API (Fastest)
python -m tools.transcribe "output/video.m4a" -m openai
```

---

## Bilibili Special Workflow

Optimized for knowledge hunters on Bilibili:

1.  **Auth Once**:
    Safe QR login to save session locally.
    ```bash
    python -m tools.auth
    ```

2.  **Clear Your "Watch Later"**:
    Don't let videos pile up. Fetch the top 10 and process them automatically.
    ```bash
    python -m tools.list --watch-later --limit 10
    python -m tools.batch_run
    ```
    *Pro Tip: Connect this to an Agent to get a "Daily Knowledge Digest".*

---

## For AI Agents (Skills)

Give the content of [`skills/VIDEO_SKILL.md`](skills/VIDEO_SKILL.md) to your AI Agent (Claude/ChatGPT/Cursor). It serves as the instruction manual, enabling the AI to autonomously control these tools.

## License

MIT
