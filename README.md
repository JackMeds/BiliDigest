# Video-Skill-Transcriber 🧠

> **The cure for your "Watch Later" backlog.**
> Let AI binge-watch those thousands of saved videos for you, turning them into summaries and knowledge.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Release](https://img.shields.io/github/v/release/JackMeds/Video-Skill-Transcriber)](https://github.com/JackMeds/Video-Skill-Transcriber/releases)

[中文说明 (Chinese README)](README_zh-CN.md)

---

## 📖 Table of Contents

- [The Problem: Information Overload](#the-problem-information-overload)
- [Capabilities](#capabilities)
- [Installation](#installation)
- [Usage](#usage)
- [Bilibili Workflow](#bilibili-workflow)
- [For AI Agents (Skills)](#for-ai-agents-skills)

---

## The Problem: Information Overload

Have you ever looked at your **YouTube "Watch Later"** or **Bilibili "Favorites"** list and felt anxiety?

You've saved thousands of high-quality tutorials, lectures, and talks, thinking "I'll learn this later." But "later" never comes because watching video is time-consuming.

**Video-Skill-Transcriber** is the solution. It autonomously batches download and transcribes your backlog, converting hours of video into structured text that AI can digest in seconds.

**Turn "Watch Later" into "Knowledge Acquired".**

## Capabilities

| Feature | Description | Note |
| :--- | :--- | :--- |
| **Universal Download** | Supports YouTube, Bilibili, TikTok, etc. | Powered by `yt-dlp` |
| **Multi-Engine ASR** | Whisper (Local), Qwen3 (Chinese Optimized), OpenAI API | Offline & Online support |
| **Batch Pipeline** | Auto-fetch "Watch Later" -> Download -> Transcribe | **Core Feature** |
| **Privacy First** | Credentials and Inference run 100% Locally | Safe for private lists |
| **Agent Ready** | Standardized Skill Definition for Claude/GPT | Automate the process |

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
    Copy `.env.example` to `.env` if you want to use Online Transcription.

## Usage

### 1. General Download
```bash
python -m tools.download "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### 2. Transcribe to Text
```bash
# Local Whisper (Default)
python -m tools.transcribe "output/video.m4a"

# Local Qwen3-ASR (Best for Chinese)
python -m tools.transcribe "output/video.m4a" -m Qwen/Qwen3-ASR-0.6B

# Online API (Fastest)
python -m tools.transcribe "output/video.m4a" -m openai
```

---

## Bilibili Workflow

We support both **Public** and **Authenticated** modes.

### Mode 1: Public Access (Default)
For standard public videos, **no login is required**. Just use the download tool directly.

```bash
python -m tools.download "https://www.bilibili.com/video/BVxxx"
```

### Mode 2: Authenticated (Advanced)
Login is required ONLY if you want to:
1. Access your private **"Watch Later"** or **"Favorites"** lists.
2. Download **1080P+ / Premium** quality videos.

**Steps:**

1.  **Login via QR Code**:
    ```bash
    python -m tools.auth
    ```
    *(Session is saved locally to `.user_session.json`)*

2.  **Process Backlog**:
    Once logged in, you can fetch your private lists:
    ```bash
    # 1. Fetch Top 10 from Watch Later
    python -m tools.list --watch-later --limit 10

    # 2. Run the pipeline
    python -m tools.batch_run
    ```

---

## For AI Agents (Skills)

Give [`skills/VIDEO_SKILL.md`](skills/VIDEO_SKILL.md) to your AI Agent (Claude/ChatGPT). It will learn to use these tools autonomously.

## License

MIT License
