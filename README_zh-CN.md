# Video-Skill-Transcriber 🎥

> 通用视频处理工具集：下载、转录，为 AI Agent 而生。
> 支持 Bilibili / YouTube / 本地文件

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Release](https://img.shields.io/github/v/release/JackMeds/Video-Skill-Transcriber)](https://github.com/JackMeds/Video-Skill-Transcriber/releases)

[English README](README.md)

---

## 目录 (Table of Contents)

- [简介](#简介)
- [核心功能](#核心功能)
- [效果展示](#效果展示)
- [安装指南](#安装指南)
- [快速开始](#快速开始)
- [B站专属教程 (Bilibili Tutorial)](#b站专属教程-bilibili-tutorial)
- [给 Agent 使用 (Skills)](#给-agent-使用-skills)
- [许可证](#许可证)

---

## 简介

Video-Skill-Transcriber 是一个功能强大的命令行工具集，旨在让 AI Agent (如 Claude, ChatGPT) 能够轻松地与视频内容交互。它集成了全平台的视频下载能力和高精度的本地/在线语音转录引擎。

## 核心功能

1.  **全平台下载**: 基于强大的 [yt-dlp](https://github.com/yt-dlp/yt-dlp)，支持 YouTube, Bilibili, TikTok 等数千个网站。
2.  **灵活鉴权**: 支持自动读取 Chrome/Edge/Firefox 浏览器 Cookie，轻松搞定会员/年龄限制视频。
3.  **多引擎转录**:
    *   **Whisper (Local)**: 速度快，通用性强。
    *   **Qwen3-ASR (Local)**: 阿里通义千问语音模型，效果卓越。
    *   **OpenAI API**: 支持调用 whisper-1 或 DeepSeek/Qwen 在线接口。

## 效果展示

![Terminal Demo](assets/terminal_demo.png)

## 安装指南

1.  **克隆仓库**:
    ```bash
    git clone https://github.com/JackMeds/Video-Skill-Transcriber.git
    cd Video-Skill-Transcriber
    ```

2.  **安装依赖**:
    ```bash
    # 推荐使用虚拟环境
    python3 -m venv .venv
    source .venv/bin/activate  # Windows 用户: .venv\Scripts\activate

    pip install -r requirements.txt
    ```
    *(注: 即使不使用虚拟环境，也能直接运行，但推荐隔离环境)*

    > **前置要求**: 请确保系统已安装 [FFmpeg](https://ffmpeg.org/) (用于音频格式转换)。

3.  **(可选) 配置 API**:
    如果你想使用在线转录功能，请复制 `.env.example` 为 `.env` 并填入你的 API Key。

## 快速开始

所有的工具都支持通过 `python -m tools.xxx` 方式调用。

### 1. 下载视频 (通用)

```bash
# 下载 YouTube 视频
python -m tools.download "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# 使用浏览器 Cookie 下载 (解决登录限制)
python -m tools.download "URL" --cookies-browser chrome
```

### 2. 音频转录

```bash
# 使用本地 Whisper 模型 (默认)
python -m tools.transcribe "output/video.m4a"

# 使用 Qwen3-ASR 模型
python -m tools.transcribe "output/video.m4a" -m Qwen/Qwen3-ASR-0.6B

# 使用 OpenAI API (需配置 .env)
python -m tools.transcribe "output/video.m4a" -m openai
```

---

## B站专属教程 (Bilibili Tutorial)

针对 Bilibili 用户，我们提供了一套深度的玩法，助你高效获取知识。

### 场景 1: 获取“稍后再看”并批量转录

这对于想把收藏的视频变成文字笔记非常有帮助。

1.  **登录 B 站**:
    由于 API 限制，这里推荐使用我们的扫码工具登录一次，Session 会自动保存。
    ```bash
    python -m tools.auth
    ```
    *(按照终端提示扫码即可)*

2.  **获取列表**:
    ```bash
    python -m tools.list --watch-later --limit 10
    ```
    这会将你稍后再看列表的前 10 个视频保存为 `batch_list.json`。

3.  **批量处理**:
    我们提供了一个批量脚本，自动读取 json 并执行下载+转录。
    ```bash
    python -m tools.batch_run
    ```
    *(你需要确保 `batch_run.py` 存在于 tools 目录，或者参考 `batch_run.py` 的用法)*

### 场景 2: 下载大会员高清/收藏夹视频

如果你有大会员权限，带上 Cookie 下载可以获得更高画质，或者下载仅限会员观看的内容。

```bash
# 自动读取你 Chrome 浏览器登录的 B 站 Cookie
python -m tools.download "https://www.bilibili.com/video/BVxxx" --cookies-browser chrome
```

---

## 给 Agent 使用 (Skills)

如果你在构建 AI Agent (如使用 Claude Desktop 或其他框架)，可以将 `skills/VIDEO_SKILL.md` 的内容复制给 Agent 作为 System Prompt 或 Skill Definition。这样 Agent 就能理解如何自主调用这些工具了。

## 许可证

MIT License
