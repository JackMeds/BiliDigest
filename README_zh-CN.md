# Video-Skill-Transcriber 🧠

> **拯救你的"稍后不看"列表。让 AI 替你把那几千个吃灰的视频"看"完。**
> 专为解决知识焦虑而生：一键批量转录 B 站/YouTube 收藏夹，生成摘要与笔记。

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

**这也是我做这个项目的初衷：**

你的 B 站"收藏夹"和"稍后再看"列表里是不是已经堆积了几千个视频？
每次看到干货都想"马了就是学会了"，但其实由于时间成本太高，绝大多数视频都在吃灰。

虽然现在的多模态大模型（如 Gemini 1.5, GPT-4o）可以直接看视频，但面对**成百上千**的待看列表，手动一个个投喂显然不现实，而且 Token 成本极高。

**Video-Skill-Transcriber** 就是为了解决这个问题。
它能作为 Agent 的"手"，全自动批量下载、转录你堆积的视频，把它们变成 AI 可以瞬间消化的文本知识。

**从此，"稍后再看" 真的变成了 "已阅"。**

## 核心能力

- **🎥 批量消灭库存**: 一键处理 B 站"稍后再看"或收藏夹，自动流水线作业。
- **🤖 Agent 技能化**: 提供标准的 `.agent/skills` 接口，让 Claude/GPT 自主调用。
- **📝 高精度转录**: 集成 Whisper/Qwen3/OpenAI，把 2 小时的视频压缩成 5 分钟的笔记。
- **🧠 本地隐私**: 支持纯本地模型运行，学习记录无需上传云端。

## AI 学习场景示例

*   **🎓 自动清仓**: "帮我把稍后再看里关于 '深度学习' 的前 10 个视频全部看完，并总结成一份学习路径图。"
*   **📝 课程笔记**: "下载这个李宏毅的合集，提取每一节课的核心知识点。"
*   **🔍 知识检索**: "我记得好像收藏过一个讲 RAG 的视频，帮我找出来它具体是在哪一分钟讲了 GraphRAG。"

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

专为 **消灭库存** 打造的自动化流：

1.  **扫码登录** (只需一次):
    ```bash
    python -m tools.auth
    ```
2.  **批量消化 "稍后再看"**:
    每天处理 10 个，配合 AI 自动生摘，从此不再焦虑。
    ```bash
    python -m tools.list --watch-later --limit 10
    python -m tools.batch_run
    ```

---

## 给 Agent 集成 (Skills)

将 [`skills/VIDEO_SKILL.md`](skills/VIDEO_SKILL.md) 的内容提供给你的 AI Agent (如 Cursor, Claude Desktop)。它将学会如何自主帮你"刷"视频。

## 许可证

MIT License
