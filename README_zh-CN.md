# Video-Skill-Transcriber 🧠

> **不仅仅是下载器，更是 AI 的"眼睛"和"耳朵"。**
> 让 Claude/ChatGPT 具备视频理解能力，实现自动摘要、思维导图构建、知识库沉淀。

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Release](https://img.shields.io/github/v/release/JackMeds/Video-Skill-Transcriber)](https://github.com/JackMeds/Video-Skill-Transcriber/releases)

[English README](README.md)

---

## 📖 目录

- [为什么需要这个工具](#为什么需要这个工具)
- [核心能力](#核心能力)
- [AI 学习场景示例](#ai-学习场景示例)
- [安装与配置](#安装与配置)
- [使用指南](#使用指南)
- [B站深度学习流](#b站深度学习流)
- [给 Agent 集成 (Skills)](#给-agent-集成-skills)

---

## 为什么需要这个工具

在 AI 时代，视频是最大的知识黑洞。虽然 AI 文本能力很强，但它无法直接"看"懂 B 站的硬核教程或 YouTube 的深度讲座。

**Video-Skill-Transcriber** 的出现，就是为了打通 **视频 -> AI** 的最后一步。它不仅仅是一个下载转录工具，更是一套**专为 AI 学习流程设计的 Skills**。

通过本工具，你也让 Agent 拥有了：
1.  **全网视频获取能力** (Bilibili/YouTube/TikTok...)
2.  **高精度听觉能力** (Whisper/Qwen3/OpenAI) 
3.  **知识萃取的基础** (从视频到结构化文本)

## 核心能力

- **🎥 视频知识化**: 将长达数小时的视频课程，转换为 AI 可处理的精确文本。
- **🤖 Agent 技能化**: 提供标准的 `.agent/skills` 接口，让 Claude/GPT 自主调用下载和转录。
- **📚 批量学习流**: 支持一键处理 "稍后再看" 列表，通过 AI 自动生成每日学习摘要。
- **🧠 本地隐私**: 支持纯本地模型 (Whisper/Qwen)，由于学习资料可能涉及隐私，本地处理更安全。

## AI 学习场景示例

有了这个工具，你的 AI Agent 可以做到：

*   **🎓 自动课程笔记**: "帮我把这两个小时的李宏毅深度学习课程转成 Markdown 笔记，提取核心知识点。"
*   **📝 会议/访谈整理**: "把这段访谈录音转录，并分析受访者的核心观点和潜在情绪。"
*   **🗺️ 知识图谱构建**: "下载这 10 个关于 'RAG' 的 B 站视频，梳理出技术发展路线图。"
*   **🔍 跨语言学习**: "下载这个英文教程，转录并翻译成中文概览。"

## 效果展示

![Terminal Demo](assets/terminal_demo.png)

## 安装与配置

1.  **克隆仓库**:
    ```bash
    git clone https://github.com/JackMeds/Video-Skill-Transcriber.git
    cd Video-Skill-Transcriber
    ```

2.  **安装依赖**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    ```
    *(需安装 [FFmpeg](https://ffmpeg.org/))*

3.  **(可选) 配置在线模型**:
    如需使用 OpenAI/DeepSeek 能力，复制 `.env.example` 到 `.env` 并填入 Key。

## 使用指南

### 1. 通用视频获取
让 AI "看到" 视频内容：
```bash
python -m tools.download "https://www.bilibili.com/video/BVxxx" --cookies-browser chrome
```

### 2. 把视频"变成"知识 (转录)
```bash
# 本地模型 (推荐用于隐私内容)
python -m tools.transcribe "output/video.m4a" -m Qwen/Qwen3-ASR-0.6B

# 在线 API (速度快，适合总结)
python -m tools.transcribe "output/video.m4a" -m openai
```

---

## B站深度学习流

专为 Bilibili 重度学习者打造的自动化流：

1.  **扫码登录** (只需一次):
    ```bash
    python -m tools.auth
    ```
2.  **批量消化 "稍后再看"**:
    不再让"稍后再看"变成"稍后不看"。一键拉取前 10 个视频进行转录：
    ```bash
    python -m tools.list --watch-later --limit 10
    python -m tools.batch_run
    ```
    配合 AI Agent，你可以让它每天早上为你推送这 10 个视频的**一句话总结**。

---

## 给 Agent 集成 (Skills)

将 [`skills/VIDEO_SKILL.md`](skills/VIDEO_SKILL.md) 的内容提供给你的 AI Agent (如 Cursor, Claude Desktop, AutoGPT)。它将学会如何自主操作这些工具，成为你的**全能学习助手**。

## 许可证

MIT License
