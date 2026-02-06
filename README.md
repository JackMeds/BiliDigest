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
- [The Solution](#the-solution)
- [How It Works](#how-it-works)
- [Installation](#installation)
- [Usage](#usage)
- [Bilibili Workflow](#bilibili-workflow)
- [For AI Agents (Skills)](#for-ai-agents-skills)

---

## The Problem: Information Overload

Have you ever looked at your **YouTube "Watch Later"** or **Bilibili "Favorites"** list and felt anxiety?

You've saved thousands of high-quality tutorials, lectures, and talks, thinking "I'll learn this later." But "later" never comes because watching video is time-consuming.

While Multimodal AI (like Gemini/GPT-4o) can watch *one* video, it cannot efficiently process your **entire backlog of 1,000 videos**. It's too slow and too expensive.

## The Solution

**Video-Skill-Transcriber** is built to solve exactly this.

It acts as a pipeline tool for your AI Agent. It autonomously batches download and transcribes your backlog, converting hours of video into structured text that AI can digest in seconds.

**Turn "Watch Later" into "Knowledge Acquired".**

## Core Capabilities

- **🎥 Batch Processing**: Automatically handle playlists or "Watch Later" lists from Bilibili/YouTube.
- **🤖 Agent Skills**: Standardized interface for AI Agents to autonomously fetch knowledge.
- **📝 High-Fidelity ASR**: Uses Whisper, Qwen3 (Chinese optimized), or OpenAI API for accurate transcripts.
- **🧠 Privacy First**: Run locally to keep your learning habits private.

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
    Copy `.env.example` to `.env` if you want to use Online Transcription.

## Usage

### 1. General Download
```bash
python -m tools.download "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --cookies-browser chrome
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

The ultimate "Clear Backlog" workflow:

1.  **Login Once**:
    ```bash
    python -m tools.auth
    ```
2.  **Batch Process Watch Later**:
    Fetch top 10 videos -> Download -> Transcribe.
    Let your AI summarize these daily.
    ```bash
    python -m tools.list --watch-later --limit 10
    python -m tools.batch_run
    ```

---

## For AI Agents (Skills)

Give [`skills/VIDEO_SKILL.md`](skills/VIDEO_SKILL.md) to your AI Agent (Claude/ChatGPT). It will learn to use these tools autonomously.

## License

MIT License
