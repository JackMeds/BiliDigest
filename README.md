<!-- jackmeds-brand:start -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/brand/hero-dark.svg">
  <img src="assets/brand/hero-light.svg" alt="BiliDigest / 哔哩摘要笔记 — A video queue, ready for your next idea." width="1200">
</picture>
<!-- jackmeds-brand:end -->

# BiliDigest / 哔哩摘要笔记

把“稍后再看”里的视频，整理成能检索、能回看来源的笔记。

面向个人 Agent 工作流的 B站字幕与摘要导出工具。读取本人已登录账号的稍后再看与收藏夹，优先使用现成字幕和 B站 AI 小助手总结，输出 Markdown、SRT 与 JSON。

[快速开始](#快速开始) · [批量处理与登录迁移](docs/usage.md) · [Agent Skill](skills/bili-digest/SKILL.md) · [English](README_en.md)

## 从视频到笔记

![BiliDigest 真实命令与字幕转换输出，使用明确标记的示例数据](assets/brand/product-proof.png)

字幕 Markdown 保留视频来源和时间戳链接，可以从一条笔记回到视频中的对应位置。输出目录为 `output/bilidigest/<日期>/`；字幕导出会同时保存 `.md`、`.srt` 与 `.subtitle.json`。

## 核心能力

- **先取现成内容。** 优先导出 B站字幕和可用的 AI 小助手总结，不默认启动 ASR。
- **整理自己的收藏。** 列出稍后再看、收藏夹目录与内容，结果包含远端总数。
- **保存批量进度。** 本地缓存、快照与状态文件支持续跑，默认跳过已完成及已失败项目。
- **接入 Agent。** CLI 提供 JSON 输出和非阻塞扫码登录流程，仓库附带 `bili-digest` Skill。

## 快速开始

需要 Python 3.10+。在终端中安装项目依赖：

```bash
git clone https://github.com/JackMeds/BiliDigest.git
cd BiliDigest
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell 的虚拟环境激活命令为 `.\.venv\Scripts\Activate.ps1`。依赖中仍包含可选转写工具使用的模型库，安装体积可能较大；基本字幕导出流程不需要另配大模型 API Key。

### 导出第一条字幕

```bash
# 用 Bilibili App 扫描终端中的二维码
python -m tools.bilidigest auth login

# 先查看一条稍后再看，取得其中的真实 BV 号
python -m tools.bilidigest list watch-later --limit 1

# 将下面的占位 BV 号替换为上一步返回的 bvid
python -m tools.bilidigest transcript BVxxxxxxxxxx --format md
```

终端会返回生成文件的路径。没有字幕时，可对该视频尝试 `python -m tools.bilidigest summary BVxxxxxxxxxx`，但 AI 小助手总结也不保证可用。

首次单条导出成功后，再处理最多 15 条：

```bash
python -m tools.bilidigest batch watch-later --limit 15 --fallback-summary
```

重复同一条批量命令即可续跑。收藏夹命令、浏览器登录态导入、缓存刷新、仅处理新增和失败状态说明见[完整使用参考](docs/usage.md)。

## 隐私与限制

- 只处理本人账号原本可访问的内容。现有字幕或 AI 总结不可用时，保留失败状态；Whisper、Qwen、OpenAI、Gemini 转写是需要显式选择的其他路径。
- Cookie 与登录 Session 保存在本机。缓存、字幕和摘要同样是本地文件；Git 忽略规则不等同于加密，分享输出前请自行检查内容。
- 请求默认限速，批量默认 15 条。遇到登录失效、HTTP `412` 或 B站 `-352` 等风控响应会保存状态并停止；不要并发启动多个批处理或在日常任务中循环重试失败项。
- 当前统一 `transcript` 入口处理视频的第一个分 P；字幕选择与结果取决于 B站接口和账号权限。

## Agent 与开发文档

安装 Skill 前先保留本仓库与 Python 环境，并将 `BILIDIGEST_HOME` 设置为 clone 的绝对路径。Skill 安装器只安装指令，不安装 Python 项目本体：

```bash
npx skills add https://github.com/JackMeds/BiliDigest --skill bili-digest -g -a codex -y
```

[中文使用参考](docs/usage.md) · [English reference](docs/usage.en.md) · [CLI 入口](tools/bilisub.py) · [现有测试](tests/)

贡献时可提交脱敏的错误信息、最小复现与预期输出。请不要附带 Cookie、Session、私人收藏列表或完整导出包。

## 许可与鸣谢

本项目采用 [GPL-3.0-or-later](LICENSE)。功能边界与安全策略参考了 [BiliTools](https://github.com/btjawa/BiliTools) 的开源实践，未迁入其 Tauri UI。归属与参考说明见 [NOTICE](NOTICE)。
