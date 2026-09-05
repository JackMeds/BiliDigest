# BiliDigest 离线证据图

[返回 README](../README.md) · [查看原图](../assets/brand/product-proof.png)

这张图是实际命令输出的排版截图，不是 BiliDigest 应用界面，也不是已登录账号的字幕导出结果。输入为三条明确标记的虚构字幕；右侧是仓库中 `body_to_markdown()` 的原始返回文本。

## 来源与运行记录

- 源码提交：`3bfa0a9d16182cc32fb919d18f69d2bec1f36f5e`。
- 采集时间：2026-09-05 07:38（Asia/Shanghai）。
- Python：`3.14.6`；复用本机已有 BiliDigest 虚拟环境，仅作解释器与依赖来源。
- 工作目录与导入源码：本次品牌工作区中的全新 BiliDigest 检出副本；已检查 `tools.bili_subtitle.__file__` 指向该副本。
- `python -m tools.bilidigest --help` 和 `body_to_markdown()` 转换均退出为 `0`，没有标准错误输出。
- 捕获尺寸：`1600 × 1120`，使用独立的 Playwright `bilidigest-proof` 会话，从本机回环地址页面截图；截图后进行了图片目视检查。

本次没有实例化 `BiliClient`、读取账号 Session、登录、请求 B站 API、下载字幕或调用模型。占位 ID `EXAMPLE_OFFLINE` 是故意无效的示例值；生成的链接没有打开。图中关于 CLI 功能的文字来自帮助输出，不代表相关网络功能已在此次采集中测试。

## 实际帮助命令

```bash
python -m tools.bilidigest --help
```

```text
usage: bilidigest [-h] {auth,list,transcript,summary,batch} ...

BiliDigest 哔哩摘要笔记 CLI

positional arguments:
  {auth,list,transcript,summary,batch}
    auth                B站登录状态和扫码登录
    list                列出稍后再看或收藏夹
    transcript          导出 B站现成字幕
    summary             导出 B站 AI 小助手总结
    batch               批量处理稍后再看

options:
  -h, --help            show this help message and exit
```

## 示例字幕与真实转换

下面的函数调用由采集脚本通过 `python -c` 实际执行。`print(..., end="")` 保留函数返回内容，不额外增加换行。

```python
from tools.bili_subtitle import body_to_markdown

video = {"title": "示例字幕：把想法写成笔记", "bvid": "EXAMPLE_OFFLINE"}
subtitle = {"lan": "zh-CN", "lan_doc": "中文（示例字幕）"}
body = [
    {"from": 0, "to": 6, "content": "先记录一个值得保留的想法。"},
    {"from": 12, "to": 18, "content": "为它补上来源，方便回到原处。"},
    {"from": 28, "to": 35, "content": "用时间戳，把回看变成下一步。"},
]
print(body_to_markdown(video, subtitle, body), end="")
```

实际输出：

```markdown
# 示例字幕：把想法写成笔记

- BV: EXAMPLE_OFFLINE
- URL: https://www.bilibili.com/video/EXAMPLE_OFFLINE
- Subtitle: 中文（示例字幕）

## 字幕

- [00:00](https://www.bilibili.com/video/EXAMPLE_OFFLINE?t=0) 先记录一个值得保留的想法。
- [00:12](https://www.bilibili.com/video/EXAMPLE_OFFLINE?t=12) 为它补上来源，方便回到原处。
- [00:28](https://www.bilibili.com/video/EXAMPLE_OFFLINE?t=28) 用时间戳，把回看变成下一步。
```

## 复现素材

品牌工作区的 `github-brand/scripts/proof-bilidigest.mjs` 负责运行命令、核对源码导入路径，并将原始 stdout 直接转义到 HTML 中。它不改变 BiliDigest 运行时代码或依赖。

从同时包含品牌仓库与项目检出副本的工作区运行，将最后一个参数换成已有 Python 环境的真实路径：

```bash
node github-brand/scripts/proof-bilidigest.mjs \
  github-brand-workspace/BiliDigest \
  /path/to/venv/bin/python
```

记录保存在工作区 `output/playwright/bilidigest-proof/`：`capture.json` 包含命令、解释器、源码路径与退出码；`cli-help.txt`、`fixture.json` 和 `example.md` 保存原始数据；`index.html` 仅承担展示排版。页面不加载外部资源。用本地静态服务器打开该目录，再以相同尺寸截图，即可重新生成证据图。
